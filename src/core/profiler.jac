"""
Code profiling utilities.

Runs submitted Python code in an isolated subprocess, measures execution time
(via time.perf_counter_ns) and peak memory (via tracemalloc), and returns
structured metrics as a dict.
"""

import subprocess;
import tempfile;
import os;
import json;
import sys;


glob HARNESS_TEMPLATE: str = """import time, tracemalloc, json, statistics, sys
sys.path.insert(0, ".")
from solution import *

tracemalloc.start()
times = []
for _i in range({num_iterations}):
    _start = time.perf_counter_ns()
    {function_call}
    _end = time.perf_counter_ns()
    elapsed = (_end - _start) / 1e6
    times.append(elapsed)
    if _i == 0 and elapsed > 5000:
        break

_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(json.dumps({{
    "median_ms": statistics.median(times),
    "min_ms": min(times),
    "max_ms": max(times),
    "peak_memory_kb": peak / 1024,
    "iterations": len(times),
    "success": True,
    "error": ""
}}))
""";


glob _ERROR_RESULT: dict = {
    "median_ms": 0.0,
    "min_ms": 0.0,
    "max_ms": 0.0,
    "peak_memory_kb": 0.0,
    "iterations": 0,
    "success": False,
    "error": ""
};


def _make_error(msg: str) -> dict {
    result = dict(_ERROR_RESULT);
    result["error"] = msg;
    return result;
}


"""Profile a Python function's execution time and memory usage.

    :param code: Python source code containing the function to profile.
    :param function_call: The function invocation, e.g. "two_sum([2,7,11,15], 9)".
    :param num_iterations: Number of times to call the function (takes median).
    :param timeout_seconds: Max wall-clock seconds before the subprocess is killed.
    :returns: dict with keys: median_ms, min_ms, max_ms, peak_memory_kb,
              iterations, success (bool), error (str).
"""
def profile_code(
    code: str,
    function_call: str,
    num_iterations: int = 5,
    timeout_seconds: int = 30
) -> dict {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_profile_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    harness_path = os.path.join(tmp_dir, "_harness.py");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }

        harness_src = HARNESS_TEMPLATE.format(
            num_iterations=num_iterations,
            function_call=function_call
        );
        with open(harness_path, "w") as f {
            f.write(harness_src);
        }

        result = subprocess.run(
            [sys.executable, "_harness.py"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        if result.returncode != 0 {
            return _make_error(
                result.stderr.strip() or result.stdout.strip()
            );
        }

        return json.loads(result.stdout.strip());
    } except subprocess.TimeoutExpired {
        return _make_error(f"Timed out after {timeout_seconds}s");
    } except Exception as e {
        return _make_error(str(e));
    } finally {
        for fname in ["solution.py", "_harness.py"] {
            p = os.path.join(tmp_dir, fname);
            if os.path.exists(p) {
                os.remove(p);
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}
