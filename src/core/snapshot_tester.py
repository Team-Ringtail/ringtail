"""
Snapshot regression testing from captured IO pairs.

Generates pytest code that replays captured arguments against an optimised
function and asserts the return values match.  Integrates with existing
repo tests when available.
"""
from __future__ import annotations

import math
import os
import pickle
import subprocess
import tempfile
import textwrap
from typing import Any

from src.core.arg_capture import IOPair


def generate_snapshot_tests(
    function_name: str,
    io_pairs: list[IOPair],
    original_source: str,
    module_name: str | None = None,
) -> str:
    """Generate a pytest file that exercises *function_name* with captured IO.

    Only serialisable pairs are included.  Floats use ``pytest.approx``.
    """
    cases: list[str] = []

    for idx, pair in enumerate(io_pairs):
        if not pair.serializable:
            continue

        args_repr = _safe_repr(pair.args)
        kwargs_repr = _safe_repr(pair.kwargs)
        expected_repr = _safe_repr(pair.return_value)

        if args_repr is None or kwargs_repr is None or expected_repr is None:
            continue

        assertion = _build_assertion(pair.return_value, expected_repr)

        cases.append(textwrap.dedent(f"""\
            def test_snapshot_{idx}():
                args = {args_repr}
                kwargs = {kwargs_repr}
                result = solution.{function_name}(*args, **kwargs)
                {assertion}
        """))

    if not cases:
        return ""

    header = textwrap.dedent("""\
        import math
        import pytest
        import solution

    """)

    return header + "\n".join(cases)


def generate_snapshot_tests_pickled(
    function_name: str,
    io_pairs: list[IOPair],
    pickle_dir: str,
) -> tuple[str, str]:
    """Generate pytest that loads args from pickle files.

    Returns (test_code, pickle_data_path). This handles complex objects that
    can't be represented as literals but can be pickled.
    """
    data_file = os.path.join(pickle_dir, "snapshot_data.pkl")
    serialisable_pairs = [p for p in io_pairs if p.serializable]
    if not serialisable_pairs:
        return "", ""

    data = [
        {"args": p.args, "kwargs": p.kwargs, "expected": p.return_value}
        for p in serialisable_pairs
    ]
    with open(data_file, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    test_code = textwrap.dedent(f"""\
        import math
        import os
        import pickle
        import pytest
        import solution

        _DATA_FILE = os.path.join(os.path.dirname(__file__), "snapshot_data.pkl")
        with open(_DATA_FILE, "rb") as _f:
            _SNAPSHOT_DATA = pickle.load(_f)

        @pytest.mark.parametrize("case_idx", range(len(_SNAPSHOT_DATA)))
        def test_snapshot(case_idx):
            case = _SNAPSHOT_DATA[case_idx]
            result = solution.{function_name}(*case["args"], **case["kwargs"])
            expected = case["expected"]
            if isinstance(expected, float):
                assert result == pytest.approx(expected, rel=1e-6, abs=1e-9)
            else:
                assert result == expected
    """)

    return test_code, data_file


def run_snapshot_tests(
    optimized_code: str,
    test_code: str,
    extra_files: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Run snapshot tests against optimised code in an isolated temp dir.

    Returns a dict with ``passed``, ``total``, ``passed_count``, ``failed_count``,
    ``failures``, ``error``.
    """
    with tempfile.TemporaryDirectory(prefix="ringtail_snap_") as tmp_dir:
        solution_path = os.path.join(tmp_dir, "solution.py")
        test_path = os.path.join(tmp_dir, "test_snapshot.py")

        with open(solution_path, "w") as f:
            f.write(optimized_code)
        with open(test_path, "w") as f:
            f.write(test_code)

        if extra_files:
            for name, content in extra_files.items():
                path = os.path.join(tmp_dir, name)
                if isinstance(content, bytes):
                    with open(path, "wb") as f:
                        f.write(content)
                else:
                    with open(path, "w") as f:
                        f.write(content)

        proc = subprocess.run(
            ["python", "-m", "pytest", "test_snapshot.py", "-q", "--tb=line", "--no-header"],
            cwd=tmp_dir,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )

        return _parse_pytest_output(proc.stdout, proc.stderr, proc.returncode)


def merge_with_repo_tests(
    snapshot_test_code: str,
    repo_test_code: str | None,
) -> str:
    """Combine snapshot tests with existing repository tests.

    Snapshot tests are always additive — they never replace repo tests.
    """
    if not repo_test_code:
        return snapshot_test_code
    if not snapshot_test_code:
        return repo_test_code

    return repo_test_code + "\n\n# --- Ringtail snapshot regression tests ---\n\n" + snapshot_test_code


def _build_assertion(value: Any, value_repr: str) -> str:
    """Build an appropriate assertion for the given return value type."""
    if isinstance(value, float) and not (math.isnan(value) or math.isinf(value)):
        return f"assert result == pytest.approx({value_repr}, rel=1e-6, abs=1e-9)"
    if isinstance(value, (list, tuple)):
        if any(isinstance(x, float) for x in _flatten(value)):
            return f"assert result == pytest.approx({value_repr}, rel=1e-6, abs=1e-9)"
    return f"assert result == {value_repr}"


def _flatten(obj: Any) -> list:
    """Flatten nested lists/tuples for type checking."""
    if isinstance(obj, (list, tuple)):
        result = []
        for item in obj:
            result.extend(_flatten(item))
        return result
    return [obj]


def _safe_repr(obj: Any) -> str | None:
    """Return a repr string that can be safely eval'd, or None if not possible."""
    try:
        r = repr(obj)
        compile(r, "<test>", "eval")
        return r
    except Exception:
        return None


def _parse_pytest_output(
    stdout: str,
    stderr: str,
    returncode: int,
) -> dict[str, Any]:
    """Parse pytest -q --tb=line output into structured results."""
    failures: list[dict[str, str]] = []
    for line in stdout.splitlines():
        if line.startswith("FAILED"):
            parts = line.split(" - ", 1)
            failures.append({
                "test": parts[0].replace("FAILED ", "").strip(),
                "message": parts[1].strip() if len(parts) > 1 else "",
            })

    passed_count = 0
    failed_count = 0
    for line in stdout.splitlines():
        line = line.strip()
        if "passed" in line:
            for word in line.split():
                if word.isdigit():
                    passed_count = int(word)
                    break
        if "failed" in line:
            for word in line.split():
                if word.isdigit():
                    failed_count = int(word)
                    break

    total = passed_count + failed_count
    error = ""
    if returncode != 0 and not failures:
        error = stderr[:500] if stderr else stdout[:500]

    return {
        "passed": returncode == 0,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failures": failures,
        "error": error,
    }
