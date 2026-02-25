"""
Code profiling utilities.

Generates a pytest-benchmark test file, runs it in an isolated subprocess
with ``--benchmark-json``, and parses the rich statistical output.
Memory is measured via tracemalloc in a separate test within the same run.

All timing statistics (warmup, calibration, outlier detection, rounds,
percentiles, IQR) are handled by pytest-benchmark — not reimplemented here.
"""

import subprocess;
import tempfile;
import os;
import json;
import sys;


glob _BENCH_TEMPLATE: str = """import json, tracemalloc, sys
sys.path.insert(0, ".")
from solution import *

def test_timing(benchmark):
    benchmark(lambda: {function_call})

def test_memory():
    tracemalloc.start()
    {function_call}
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    with open("_memory.json", "w") as f:
        json.dump({{"peak_memory_kb": peak / 1024}}, f)
""";


glob _ERROR_RESULT: dict = {
    "median_ms": 0.0,
    "mean_ms": 0.0,
    "min_ms": 0.0,
    "max_ms": 0.0,
    "stdev_ms": 0.0,
    "iqr_ms": 0.0,
    "q1_ms": 0.0,
    "q3_ms": 0.0,
    "peak_memory_kb": 0.0,
    "iterations": 0,
    "rounds": 0,
    "outliers": "",
    "success": False,
    "error": ""
};


def _make_error(msg: str) -> dict {
    result = dict(_ERROR_RESULT);
    result["error"] = msg;
    return result;
}


def _parse_benchmark_json(bench_path: str, memory_path: str) -> dict {
    """Parse pytest-benchmark JSON output + memory JSON into our result dict."""
    try {
        with open(bench_path, "r") as f {
            data = json.load(f);
        }
    } except (FileNotFoundError, json.JSONDecodeError) as e {
        return _make_error(f"Failed to parse benchmark JSON: {e}");
    }

    benchmarks = data.get("benchmarks", []);
    if len(benchmarks) == 0 {
        return _make_error("No benchmark results found in JSON output");
    }

    stats = benchmarks[0].get("stats", {});

    # pytest-benchmark reports in seconds; convert to ms
    to_ms = 1000.0;
    median_ms = stats.get("median", 0.0) * to_ms;
    mean_ms = stats.get("mean", 0.0) * to_ms;
    min_ms = stats.get("min", 0.0) * to_ms;
    max_ms = stats.get("max", 0.0) * to_ms;
    stdev_ms = stats.get("stddev", 0.0) * to_ms;
    iqr_ms = stats.get("iqr", 0.0) * to_ms;
    q1_ms = stats.get("q1", 0.0) * to_ms;
    q3_ms = stats.get("q3", 0.0) * to_ms;
    rounds = stats.get("rounds", 0);
    iterations = stats.get("iterations", 0);
    outliers = stats.get("outliers", "");

    # Memory from separate file
    peak_memory_kb = 0.0;
    try {
        with open(memory_path, "r") as f {
            mem_data = json.load(f);
        }
        peak_memory_kb = mem_data.get("peak_memory_kb", 0.0);
    } except (FileNotFoundError, json.JSONDecodeError) {
        ;  # memory measurement is best-effort
    }

    return {
        "median_ms": median_ms,
        "mean_ms": mean_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "stdev_ms": stdev_ms,
        "iqr_ms": iqr_ms,
        "q1_ms": q1_ms,
        "q3_ms": q3_ms,
        "peak_memory_kb": peak_memory_kb,
        "iterations": iterations,
        "rounds": rounds,
        "outliers": outliers,
        "success": True,
        "error": ""
    };
}


"""Profile a Python function's execution time and memory usage.

    Uses pytest-benchmark for timing (warmup, calibration, outlier detection,
    rich statistics) and tracemalloc for peak memory.

    :param code: Python source code containing the function to profile.
    :param function_call: The function invocation, e.g. "two_sum([2,7,11,15], 9)".
    :param min_rounds: Minimum benchmark rounds (pytest-benchmark default: 5).
    :param timeout_seconds: Max wall-clock seconds before the subprocess is killed.
    :returns: dict with timing stats from pytest-benchmark, peak memory, and metadata.
"""
def profile_code(
    code: str,
    function_call: str,
    min_rounds: int = 10,
    timeout_seconds: int = 30
) -> dict {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_profile_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    bench_path = os.path.join(tmp_dir, "_bench.py");
    json_path = os.path.join(tmp_dir, "_results.json");
    memory_path = os.path.join(tmp_dir, "_memory.json");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }

        bench_src = _BENCH_TEMPLATE.format(function_call=function_call);
        with open(bench_path, "w") as f {
            f.write(bench_src);
        }

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "_bench.py",
             "--benchmark-json=" + json_path,
             "--benchmark-min-rounds=" + str(min_rounds),
             "--benchmark-warmup=on",
             "--benchmark-disable-gc",
             "-q", "--no-header", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        if not os.path.exists(json_path) {
            return _make_error(
                result.stderr.strip() or result.stdout.strip() or "pytest-benchmark produced no output"
            );
        }

        if result.returncode != 0 {
            parsed = _parse_benchmark_json(json_path, memory_path);
            stderr_hint = result.stderr.strip() or result.stdout.strip();
            parsed["error"] = f"pytest exited with code {result.returncode}: {stderr_hint}";
            parsed["success"] = False;
            return parsed;
        }

        return _parse_benchmark_json(json_path, memory_path);
    } except subprocess.TimeoutExpired {
        return _make_error(f"Timed out after {timeout_seconds}s");
    } except Exception as e {
        return _make_error(str(e));
    } finally {
        for fname in os.listdir(tmp_dir) {
            p = os.path.join(tmp_dir, fname);
            if os.path.isfile(p) {
                os.remove(p);
            }
        }
        # Clean subdirectories left by pytest
        for (dirpath, dirs, files) in os.walk(tmp_dir, topdown=False) {
            for f in files {
                os.remove(os.path.join(dirpath, f));
            }
            for d in dirs {
                try { os.rmdir(os.path.join(dirpath, d)); } except OSError { ; }
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}
