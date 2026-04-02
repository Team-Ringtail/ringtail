"""
Capture real function arguments and return values during execution.

Generates a wrapper script that monkey-patches target functions, runs the
entry point, and serialises the captured IO pairs for use as snapshot
regression tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IOPair:
    args: tuple
    kwargs: dict[str, Any]
    return_value: Any
    serializable: bool = True


def capture_function_io(
    repo_path: str,
    entry_point: str,
    target_functions: dict[str, dict[str, Any]],
    max_samples: int = 100,
    timeout: int = 300,
    venv_python: str = "",
) -> dict[str, list[IOPair]]:
    """Capture real args/returns for *target_functions* by running *entry_point*.

    Parameters
    ----------
    repo_path:
        Root of the checked-out repository.
    entry_point:
        Shell command to exercise the code (e.g. ``pytest tests/``).
    target_functions:
        Mapping of function key -> dict with ``file_path``, ``name``, ``module``.
    max_samples:
        Maximum unique IO pairs to keep per function.
    timeout:
        Seconds before the instrumented run is killed.

    Returns a mapping of function key -> list of IOPair.
    """
    if not target_functions:
        return {}

    with tempfile.TemporaryDirectory(prefix="ringtail_capture_") as tmp_dir:
        capture_file = os.path.join(tmp_dir, "captured_io.pkl")
        wrapper_script = os.path.join(tmp_dir, "_ringtail_capture_wrapper.py")

        _write_wrapper_script(
            wrapper_script,
            target_functions,
            capture_file,
            max_samples,
            entry_point,
        )

        python_bin = _resolve_python_bin(repo_path, venv_python)
        subprocess.run(
            f"{python_bin} {wrapper_script}",
            shell=True,
            cwd=repo_path,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )

        if not os.path.exists(capture_file):
            return {}

        return _load_captured(capture_file, target_functions)


def _resolve_python_bin(repo_path: str, venv_python: str = "") -> str:
    if venv_python and os.path.isfile(venv_python):
        return venv_python
    for venv_dir in (".venv", "venv"):
        candidate = os.path.join(repo_path, venv_dir, "bin", "python")
        if os.path.isfile(candidate):
            return candidate
    return "python"


def _write_wrapper_script(
    script_path: str,
    target_functions: dict[str, dict[str, Any]],
    capture_file: str,
    max_samples: int,
    entry_point: str,
) -> None:
    """Generate a Python script that patches targets and records IO."""

    patches = []
    for func_key, info in target_functions.items():
        module = info["module"]
        name = info["name"]
        patches.append(
            f"    _patch_function({module!r}, {name!r}, {func_key!r})"
        )

    patch_block = "\n".join(patches)

    # The generated script does the following:
    #   1. Imports the target modules
    #   2. Monkey-patches each target function with a recording wrapper
    #   3. Runs the entry point (by exec-ing pytest or the script)
    #   4. Serialises captured data to a pickle file
    script = textwrap.dedent(f"""\
        import sys
        import os
        import importlib
        import pickle
        import hashlib

        _captured = {{}}
        _max_samples = {max_samples}
        _capture_file = {capture_file!r}

        def _arg_hash(args, kwargs):
            try:
                return hashlib.md5(
                    pickle.dumps((args, kwargs), protocol=pickle.HIGHEST_PROTOCOL)
                ).hexdigest()
            except Exception:
                return None

        def _patch_function(module_name, func_name, func_key):
            try:
                mod = importlib.import_module(module_name)
            except ImportError:
                return
            original = getattr(mod, func_name, None)
            if original is None or not callable(original):
                return

            if func_key not in _captured:
                _captured[func_key] = {{}}

            def wrapper(*args, **kwargs):
                result = original(*args, **kwargs)
                store = _captured[func_key]
                if len(store) >= _max_samples:
                    return result
                h = _arg_hash(args, kwargs)
                if h is not None and h not in store:
                    try:
                        pickle.dumps((args, kwargs, result), protocol=pickle.HIGHEST_PROTOCOL)
                        store[h] = (args, kwargs, result, True)
                    except Exception:
                        store[h] = (args, kwargs, result, False)
                return result

            setattr(mod, func_name, wrapper)

        def _save():
            try:
                with open(_capture_file, "wb") as f:
                    pickle.dump(_captured, f, protocol=pickle.HIGHEST_PROTOCOL)
            except Exception:
                pass

        import atexit
        atexit.register(_save)

        # Apply patches
    {patch_block}

        # Run the entry point
        entry = {entry_point!r}
        if entry.startswith("pytest"):
            parts = entry.split()
            import pytest as _pytest
            _pytest.main(parts[1:] + ["-x", "-q", "--tb=no", "--no-header"])
        else:
            parts = entry.split()
            script_path = parts[0] if not parts[0].startswith("-") else parts[-1]
            if parts[0] == "python":
                script_path = parts[1] if len(parts) > 1 else ""
            if script_path and os.path.isfile(script_path):
                sys.argv = parts[1:] if parts[0] == "python" else parts
                exec(compile(open(script_path).read(), script_path, "exec"), {{"__name__": "__main__"}})
    """)

    with open(script_path, "w") as f:
        f.write(script)


def _load_captured(
    capture_file: str,
    target_functions: dict[str, dict[str, Any]],
) -> dict[str, list[IOPair]]:
    """Load and convert pickle data to IOPair instances."""
    try:
        with open(capture_file, "rb") as f:
            raw: dict[str, dict[str, tuple]] = pickle.load(f)
    except Exception:
        return {}

    result: dict[str, list[IOPair]] = {}
    for func_key, samples in raw.items():
        if func_key not in target_functions:
            continue
        pairs = []
        for _hash, (args, kwargs, ret, serializable) in samples.items():
            pairs.append(IOPair(
                args=args,
                kwargs=kwargs,
                return_value=ret,
                serializable=serializable,
            ))
        if pairs:
            result[func_key] = pairs
    return result
