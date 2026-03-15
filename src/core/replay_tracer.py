"""Lightweight replay tracing for Python workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


TRACE_WRAPPER_TEMPLATE = """import importlib.util
import json
import os
import runpy
import sys

SOURCE_BASENAME = {source_basename!r}
SCRIPT_BASENAME = {script_basename!r}
MODULE_NAME = {module_name!r}
FUNCTION_NAME = {function_name!r}
TRACE_PATH = {trace_path!r}

sys.path.insert(0, os.getcwd())

spec = importlib.util.spec_from_file_location(MODULE_NAME, SOURCE_BASENAME)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
sys.modules[MODULE_NAME] = module

records = []
orig = getattr(module, FUNCTION_NAME)

def wrapped(*args, **kwargs):
    record = {{
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

setattr(module, FUNCTION_NAME, wrapped)

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


def trace_replay_cases_from_script(
    source_file_path: str,
    function_name: str,
    script_path: str,
    timeout_seconds: int = 30,
) -> dict:
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_")
    abs_source = os.path.abspath(source_file_path)
    abs_script = os.path.abspath(script_path)
    source_basename = os.path.basename(abs_source)
    script_basename = os.path.basename(abs_script)
    trace_json_path = os.path.join(tmp_dir, "_trace.json")
    wrapper_path = os.path.join(tmp_dir, "_trace_wrapper.py")

    try:
        with open(os.path.join(tmp_dir, source_basename), "w") as f:
            f.write(open(abs_source, "r").read())
        with open(os.path.join(tmp_dir, script_basename), "w") as f:
            f.write(open(abs_script, "r").read())

        with open(wrapper_path, "w") as f:
            f.write(
                TRACE_WRAPPER_TEMPLATE.format(
                    source_basename=source_basename,
                    script_basename=script_basename,
                    module_name=os.path.splitext(source_basename)[0],
                    function_name=function_name,
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
            return {
                "success": False,
                "test_cases": [],
                "trace_count": 0,
                "error": result.stderr.strip() or result.stdout.strip() or "Trace produced no output",
            }

        with open(trace_json_path, "r") as f:
            trace_data = json.load(f)

        cases = _records_to_test_cases(function_name, trace_data.get("records", []))
        run_error = trace_data.get("run_error", "")
        return {
            "success": len(cases) > 0,
            "test_cases": cases,
            "trace_count": len(cases),
            "run_error": run_error,
            "error": "" if len(cases) > 0 else (run_error or "No calls captured"),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "test_cases": [],
            "trace_count": 0,
            "error": f"Replay trace timed out after {timeout_seconds}s",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "success": False,
            "test_cases": [],
            "trace_count": 0,
            "error": str(exc),
        }
    finally:
        for dirpath, dirs, files in os.walk(tmp_dir, topdown=False):
            for fname in files:
                os.remove(os.path.join(dirpath, fname))
            for dname in dirs:
                os.rmdir(os.path.join(dirpath, dname))
        os.rmdir(tmp_dir)
