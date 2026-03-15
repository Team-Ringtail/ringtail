"""Lightweight replay tracing for Python workflows."""

from __future__ import annotations

import hashlib
import json
import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


TRACE_WRAPPER_TEMPLATE = """import importlib.util
import json
import os
import runpy
import sys

SOURCE_BASENAME = {source_basename!r}
SCRIPT_BASENAME = {script_basename!r}
MODULE_NAME = {module_name!r}
FUNCTION_NAMES = {function_names!r}
TRACE_PATH = {trace_path!r}

sys.path.insert(0, os.getcwd())

spec = importlib.util.spec_from_file_location(MODULE_NAME, SOURCE_BASENAME)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.modules[MODULE_NAME] = module

records = []

def _make_wrapper(function_name):
    orig = getattr(module, function_name)

    def wrapped(*args, **kwargs):
        record = {{
            "function_name": function_name,
            "args": [repr(a) for a in args],
            "kwargs": {{k: repr(v) for (k, v) in kwargs.items()}},
        }}
        try:
            result = orig(*args, **kwargs)
            record["expected"] = repr(result)
            records.append(record)
            return result
        except Exception as exc:  # pragma: no cover - exercised through subprocess
            record["raises"] = type(exc).__name__
            records.append(record)
            raise

    return wrapped

for function_name in FUNCTION_NAMES:
    if hasattr(module, function_name):
        setattr(module, function_name, _make_wrapper(function_name))

run_error = ""
try:
    runpy.run_path(SCRIPT_BASENAME, run_name="__main__")
except Exception as exc:
    run_error = "%s: %s" % (type(exc).__name__, exc)

with open(TRACE_PATH, "w") as f:
    json.dump({{"records": records, "run_error": run_error}}, f)

if run_error:
    raise RuntimeError(run_error)
"""


REPO_TRACE_WRAPPER_TEMPLATE = """import importlib
import json
import os
import runpy
import sys

SOURCE_SPECS = {source_specs!r}
SCRIPT_REL_PATH = {script_rel_path!r}
TRACE_PATH = {trace_path!r}

sys.path.insert(0, os.getcwd())

records = []
loaded_modules = {{}}

def _make_wrapper(module_name, source_rel_path, module, function_name):
    orig = getattr(module, function_name)

    def wrapped(*args, **kwargs):
        record = {{
            "module_name": module_name,
            "source_rel_path": source_rel_path,
            "function_name": function_name,
            "args": [repr(a) for a in args],
            "kwargs": {{k: repr(v) for (k, v) in kwargs.items()}},
        }}
        try:
            result = orig(*args, **kwargs)
            record["expected"] = repr(result)
            records.append(record)
            return result
        except Exception as exc:  # pragma: no cover - exercised through subprocess
            record["raises"] = type(exc).__name__
            records.append(record)
            raise

    return wrapped

for spec in SOURCE_SPECS:
    module_name = spec["module_name"]
    try:
        loaded_modules[module_name] = importlib.import_module(module_name)
    except Exception:
        pass

for spec in SOURCE_SPECS:
    module_name = spec["module_name"]
    source_rel_path = spec["source_rel_path"]
    function_names = spec["function_names"]
    module = loaded_modules.get(module_name)
    if module is None:
        continue
    for function_name in function_names:
        if hasattr(module, function_name):
            setattr(module, function_name, _make_wrapper(module_name, source_rel_path, module, function_name))

run_error = ""
try:
    runpy.run_path(SCRIPT_REL_PATH, run_name="__main__")
except Exception as exc:
    run_error = "%s: %s" % (type(exc).__name__, exc)

with open(TRACE_PATH, "w") as f:
    json.dump({{"records": records, "run_error": run_error}}, f)

if run_error:
    raise RuntimeError(run_error)
"""

REPLAY_CACHE_VERSION = "v1"


def _render_call(function_name: str, args: list[str], kwargs: dict[str, str]) -> str:
    parts = list(args)
    parts.extend(f"{key}={value}" for key, value in kwargs.items())
    return f"{function_name}({', '.join(parts)})"


def _records_to_test_cases(function_name: str, records: list[dict]) -> list[dict]:
    cases: list[dict] = []
    for idx, record in enumerate(records):
        test_case = {
            "name": f"replay_case_{idx}",
            "call": _render_call(function_name, record.get("args", []), record.get("kwargs", {})),
        }
        if "raises" in record:
            test_case["raises"] = record["raises"]
        else:
            test_case["expected"] = record.get("expected", "None")
        cases.append(test_case)
    return cases


def _empty_trace_result(error: str, *, stdout: str = "", stderr: str = "") -> dict:
    return {
        "success": False,
        "test_cases": [],
        "trace_count": 0,
        "captured_records": [],
        "captured_function": "",
        "run_error": error,
        "partial_success": False,
        "returncode": -1,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
    }


def _empty_session_result(error: str, *, stdout: str = "", stderr: str = "") -> dict:
    return {
        "success": False,
        "functions": {},
        "traced_function_names": [],
        "observed_function_names": [],
        "total_trace_count": 0,
        "captured_records": [],
        "run_error": error,
        "partial_success": False,
        "returncode": -1,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
    }


def _empty_repo_session_result(error: str, *, stdout: str = "", stderr: str = "") -> dict:
    return {
        "success": False,
        "sources": {},
        "traced_source_files": [],
        "observed_source_files": [],
        "total_trace_count": 0,
        "captured_records": [],
        "run_error": error,
        "partial_success": False,
        "returncode": -1,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
    }


def _cache_dir() -> str:
    return os.path.join(str(Path.home()), ".ringtail_cache", "replay")


def _hash_file(abs_path: str) -> str:
    return hashlib.sha256(Path(abs_path).read_bytes()).hexdigest()


def _session_cache_key(abs_source: str, abs_script: str, function_names: list[str]) -> str:
    payload = {
        "version": REPLAY_CACHE_VERSION,
        "mode": "single_file_session",
        "source_file": abs_source,
        "script_path": abs_script,
        "source_hash": _hash_file(abs_source),
        "script_hash": _hash_file(abs_script),
        "function_names": list(function_names),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _repo_session_cache_key(
    abs_sources: list[str],
    abs_script: str,
    function_names_by_source: dict[str, list[str]],
) -> str:
    payload = {
        "version": REPLAY_CACHE_VERSION,
        "mode": "repo_session",
        "script_path": abs_script,
        "script_hash": _hash_file(abs_script),
        "sources": [
            {
                "source_file": abs_source,
                "source_hash": _hash_file(abs_source),
                "function_names": list(function_names_by_source.get(abs_source, [])),
            }
            for abs_source in abs_sources
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _load_cache(cache_key: str) -> dict | None:
    cache_path = os.path.join(_cache_dir(), cache_key + ".json")
    if not os.path.exists(cache_path):
        return None
    try:
        return json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _store_cache(cache_key: str, result: dict) -> None:
    cache_dir = _cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, cache_key + ".json")
    Path(cache_path).write_text(json.dumps(result), encoding="utf-8")


def _with_cache_metadata(result: dict, cache_key: str, cache_hit: bool) -> dict:
    with_meta = dict(result)
    with_meta["cache_key"] = cache_key
    with_meta["cache_hit"] = cache_hit
    return with_meta


def _group_records_by_function(records: list[dict], function_names: list[str]) -> dict[str, list[dict]]:
    grouped = {name: [] for name in function_names}
    for record in records:
        function_name = str(record.get("function_name", ""))
        if function_name in grouped:
            grouped[function_name].append(record)
    return grouped


def _module_name_from_rel_path(rel_path: str) -> str:
    path = Path(rel_path)
    parts = list(path.with_suffix("").parts)
    if len(parts) > 0 and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _copy_tree_file(abs_path: str, common_root: str, tmp_dir: str) -> str:
    rel_path = os.path.relpath(abs_path, common_root)
    target_path = os.path.join(tmp_dir, rel_path)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    Path(target_path).write_text(Path(abs_path).read_text(encoding="utf-8"), encoding="utf-8")
    return rel_path


def _group_records_by_source_and_function(
    records: list[dict],
    source_rel_paths: list[str],
    function_names_by_source: dict[str, list[str]],
) -> dict[str, dict[str, list[dict]]]:
    grouped = {
        source_rel_path: {
            function_name: []
            for function_name in function_names_by_source.get(source_rel_path, [])
        }
        for source_rel_path in source_rel_paths
    }
    for record in records:
        source_rel_path = str(record.get("source_rel_path", ""))
        function_name = str(record.get("function_name", ""))
        if (
            source_rel_path in grouped
            and function_name in grouped[source_rel_path]
        ):
            grouped[source_rel_path][function_name].append(record)
    return grouped


def _function_trace_result(
    function_name: str,
    records: list[dict],
    *,
    run_error: str,
    returncode: int,
    stdout: str,
    stderr: str,
) -> dict:
    cases = _records_to_test_cases(function_name, records)
    partial_success = len(cases) > 0 and run_error != ""
    error = ""
    if len(cases) == 0:
        error = run_error or "No calls captured"
    return {
        "success": len(cases) > 0,
        "test_cases": cases,
        "trace_count": len(cases),
        "captured_records": records,
        "captured_function": function_name,
        "run_error": run_error,
        "partial_success": partial_success,
        "returncode": returncode,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
    }


def trace_replay_session_from_script(
    source_file_path: str,
    function_names: list[str],
    script_path: str,
    timeout_seconds: int = 30,
) -> dict:
    if len(function_names) == 0:
        return _empty_session_result("No functions requested for replay tracing")

    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_")
    abs_source = os.path.abspath(source_file_path)
    abs_script = os.path.abspath(script_path)
    common_root = os.path.commonpath([abs_source, abs_script])
    cache_key = _session_cache_key(abs_source, abs_script, function_names)
    cached = _load_cache(cache_key)
    if cached is not None:
        return _with_cache_metadata(cached, cache_key, True)
    source_basename = os.path.basename(abs_source)
    script_basename = os.path.basename(abs_script)
    trace_json_path = os.path.join(tmp_dir, "_trace.json")
    wrapper_path = os.path.join(tmp_dir, "_trace_wrapper.py")

    try:
        with open(os.path.join(tmp_dir, source_basename), "w", encoding="utf-8") as f:
            f.write(Path(abs_source).read_text(encoding="utf-8"))
        with open(os.path.join(tmp_dir, script_basename), "w", encoding="utf-8") as f:
            f.write(Path(abs_script).read_text(encoding="utf-8"))

        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(
                TRACE_WRAPPER_TEMPLATE.format(
                    source_basename=source_basename,
                    script_basename=script_basename,
                    module_name=os.path.splitext(source_basename)[0],
                    function_names=function_names,
                    trace_path="_trace.json",
                )
            )

        result = subprocess.run(
            [sys.executable, "_trace_wrapper.py"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir,
        )

        if not os.path.exists(trace_json_path):
            return _empty_session_result(
                result.stderr.strip() or result.stdout.strip() or "Trace produced no output",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        with open(trace_json_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)

        records = trace_data.get("records", [])
        run_error = trace_data.get("run_error", "")
        grouped = _group_records_by_function(records, function_names)
        functions = {
            function_name: _function_trace_result(
                function_name,
                grouped.get(function_name, []),
                run_error=run_error,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            for function_name in function_names
        }
        observed_function_names = [
            function_name
            for function_name, fn_result in functions.items()
            if fn_result.get("trace_count", 0) > 0
        ]
        success = len(observed_function_names) > 0
        result_payload = {
            "success": success,
            "functions": functions,
            "traced_function_names": list(function_names),
            "observed_function_names": observed_function_names,
            "total_trace_count": len(records),
            "captured_records": records,
            "run_error": run_error,
            "partial_success": success and run_error != "",
            "returncode": result.returncode,
            "error": "" if success else (run_error or "No calls captured"),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    except subprocess.TimeoutExpired:
        result_payload = _empty_session_result(f"Replay trace timed out after {timeout_seconds}s")
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    except Exception as exc:  # pragma: no cover - defensive
        result_payload = _empty_session_result(str(exc))
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    finally:
        for dirpath, dirs, files in os.walk(tmp_dir, topdown=False):
            for fname in files:
                os.remove(os.path.join(dirpath, fname))
            for dname in dirs:
                os.rmdir(os.path.join(dirpath, dname))
        os.rmdir(tmp_dir)


def trace_replay_cases_from_script(
    source_file_path: str,
    function_name: str,
    script_path: str,
    timeout_seconds: int = 30,
) -> dict:
    session = trace_replay_session_from_script(
        source_file_path,
        [function_name],
        script_path,
        timeout_seconds,
    )
    functions = session.get("functions", {})
    if function_name in functions:
        result = dict(functions[function_name])
        result["session_total_trace_count"] = session.get("total_trace_count", 0)
        result["observed_function_names"] = session.get("observed_function_names", [])
        result["cache_key"] = session.get("cache_key", "")
        result["cache_hit"] = bool(session.get("cache_hit", False))
        return result
    return _empty_trace_result(
        str(session.get("error", "No calls captured")),
        stdout=str(session.get("stdout", "")),
        stderr=str(session.get("stderr", "")),
    )


def trace_replay_repo_session_from_script(
    source_file_paths: list[str],
    script_path: str,
    function_names_by_source: dict[str, list[str]] | None = None,
    timeout_seconds: int = 30,
) -> dict:
    if len(source_file_paths) == 0:
        return _empty_repo_session_result("No source files requested for replay tracing")

    abs_sources = [os.path.abspath(path) for path in source_file_paths]
    abs_script = os.path.abspath(script_path)
    common_root = os.path.commonpath(abs_sources + [abs_script])
    raw_function_names_by_source = function_names_by_source or {}
    normalized_function_names_by_source = {
        abs_source: list(raw_function_names_by_source.get(abs_source, []))
        for abs_source in abs_sources
    }
    cache_key = _repo_session_cache_key(abs_sources, abs_script, normalized_function_names_by_source)
    cached = _load_cache(cache_key)
    if cached is not None:
        return _with_cache_metadata(cached, cache_key, True)
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_")
    trace_json_path = os.path.join(tmp_dir, "_trace.json")
    wrapper_path = os.path.join(tmp_dir, "_trace_repo_wrapper.py")

    try:
        source_specs: list[dict] = []
        source_rel_paths: list[str] = []
        for abs_source in abs_sources:
            source_rel_path = _copy_tree_file(abs_source, common_root, tmp_dir)
            source_rel_paths.append(source_rel_path)
            selected_functions = list(normalized_function_names_by_source.get(abs_source, []))
            normalized_function_names_by_source[source_rel_path] = selected_functions
            source_specs.append(
                {
                    "source_rel_path": source_rel_path,
                    "module_name": _module_name_from_rel_path(source_rel_path),
                    "function_names": selected_functions,
                }
            )

        script_rel_path = _copy_tree_file(abs_script, common_root, tmp_dir)

        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(
                REPO_TRACE_WRAPPER_TEMPLATE.format(
                    source_specs=source_specs,
                    script_rel_path=script_rel_path,
                    trace_path="_trace.json",
                )
            )

        result = subprocess.run(
            [sys.executable, "_trace_repo_wrapper.py"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir,
        )

        if not os.path.exists(trace_json_path):
            return _empty_repo_session_result(
                result.stderr.strip() or result.stdout.strip() or "Trace produced no output",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        with open(trace_json_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)

        records = trace_data.get("records", [])
        run_error = trace_data.get("run_error", "")
        grouped = _group_records_by_source_and_function(
            records,
            source_rel_paths,
            normalized_function_names_by_source,
        )

        sources: dict[str, dict] = {}
        observed_source_files: list[str] = []
        for abs_source in abs_sources:
            source_rel_path = os.path.relpath(abs_source, common_root)
            function_results = {}
            observed_function_names = []
            source_records: list[dict] = []
            for function_name in normalized_function_names_by_source.get(source_rel_path, []):
                fn_records = grouped.get(source_rel_path, {}).get(function_name, [])
                fn_result = _function_trace_result(
                    function_name,
                    fn_records,
                    run_error=run_error,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                function_results[function_name] = fn_result
                if fn_result.get("trace_count", 0) > 0:
                    observed_function_names.append(function_name)
                    source_records.extend(fn_records)

            source_success = len(observed_function_names) > 0
            if source_success:
                observed_source_files.append(abs_source)
            sources[abs_source] = {
                "success": source_success,
                "source_file": abs_source,
                "source_rel_path": source_rel_path,
                "module_name": _module_name_from_rel_path(source_rel_path),
                "functions": function_results,
                "observed_function_names": observed_function_names,
                "trace_count": len(source_records),
                "captured_records": source_records,
                "run_error": run_error,
                "partial_success": source_success and run_error != "",
                "returncode": result.returncode,
                "error": "" if source_success else (run_error or "No calls captured"),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        success = len(observed_source_files) > 0
        result_payload = {
            "success": success,
            "sources": sources,
            "traced_source_files": abs_sources,
            "observed_source_files": observed_source_files,
            "total_trace_count": len(records),
            "captured_records": records,
            "run_error": run_error,
            "partial_success": success and run_error != "",
            "returncode": result.returncode,
            "error": "" if success else (run_error or "No calls captured"),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    except subprocess.TimeoutExpired:
        result_payload = _empty_repo_session_result(f"Replay trace timed out after {timeout_seconds}s")
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    except Exception as exc:  # pragma: no cover - defensive
        result_payload = _empty_repo_session_result(str(exc))
        _store_cache(cache_key, result_payload)
        return _with_cache_metadata(result_payload, cache_key, False)
    finally:
        for dirpath, dirs, files in os.walk(tmp_dir, topdown=False):
            for fname in files:
                os.remove(os.path.join(dirpath, fname))
            for dname in dirs:
                os.rmdir(os.path.join(dirpath, dname))
        os.rmdir(tmp_dir)
