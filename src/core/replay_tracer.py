"""Lightweight replay tracing for Python workflows."""

from __future__ import annotations

import json
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


def _group_records_by_function(records: list[dict], function_names: list[str]) -> dict[str, list[dict]]:
    grouped = {name: [] for name in function_names}
    for record in records:
        function_name = str(record.get("function_name", ""))
        if function_name in grouped:
            grouped[function_name].append(record)
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
        return {
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
    except subprocess.TimeoutExpired:
        return _empty_session_result(f"Replay trace timed out after {timeout_seconds}s")
    except Exception as exc:  # pragma: no cover - defensive
        return _empty_session_result(str(exc))
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
        return result
    return _empty_trace_result(
        str(session.get("error", "No calls captured")),
        stdout=str(session.get("stdout", "")),
        stderr=str(session.get("stderr", "")),
    )
