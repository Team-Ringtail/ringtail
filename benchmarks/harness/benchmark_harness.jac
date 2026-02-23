"""
Benchmark harness for LeetCode problems.

This is the Jac-side adapter between the optimization loop and the
Python benchmark runner in `benchmarks/run_benchmark.py`.

Usage (from Jac / optimization loop):
- Call `run_benchmark(slug, solution_path)` to execute one benchmark.
- Optionally call the `run_benchmark` walker for ad‑hoc testing.
"""

import json, os, subprocess, sys


def:pub run_benchmark(slug: str, solution_path: str = "") -> dict {
    """
    Run a single LeetCode benchmark via the Python runner.

    - slug: e.g. "two_sum", "three_sum", ...
    - solution_path: optional path to a Python file containing the
      candidate implementation. If empty, the reference solution in
      `benchmarks/leetcode/<slug>/solution.py` is used.

    Returns a dict with at least:
    - benchmark: slug
    - solution_path: the path actually used (may be "")
    - passed: number of tests passed
    - failed: number of tests failed
    - time_seconds: wall-clock time for the run
    - error: optional error string if something went wrong
    """

    # Resolve repo root from this file location
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runner = os.path.join(root, "benchmarks", "run_benchmark.py")

    cmd = [sys.executable, runner, slug]
    if solution_path:
        cmd += ["--solution", solution_path]

    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as e:
        return {
            "benchmark": slug,
            "solution_path": solution_path,
            "passed": 0,
            "failed": 1,
            "time_seconds": 0.0,
            "error": str(e),
        }

    stdout = (result.stdout or "").strip()

    # Try to parse JSON from stdout (the runner's default output format)
    data = {}
    if stdout:
        try:
            data = json.loads(stdout)
        except Exception:
            data = {}

    # If the runner failed and we couldn't parse JSON, surface stderr/stdout
    if result.returncode != 0 and not data:
        return {
            "benchmark": slug,
            "solution_path": solution_path,
            "passed": 0,
            "failed": 1,
            "time_seconds": 0.0,
            "error": (result.stderr or result.stdout or f"exit_code={result.returncode}"),
        }

    # Normalize both single-benchmark and --all outputs from the runner
    passed = data.get("passed")
    failed = data.get("failed")
    time_seconds = data.get("time_seconds", 0.0)

    # Fallbacks if someone accidentally calls the runner with --all
    if passed is None and "total_passed" in data:
        passed = data.get("total_passed", 0)
    if failed is None and "total_failed" in data:
        failed = data.get("total_failed", 0)

    out = {
        "benchmark": slug,
        "solution_path": solution_path,
        "passed": passed if passed is not None else 0,
        "failed": failed if failed is not None else 0,
        "time_seconds": time_seconds,
    }

    if "error" in data:
        out["error"] = data["error"]

    return out
}


walker run_benchmark {
    has slug: str = "";
    has solution_path: str = "";

    can with entry {
        report run_benchmark(slug=slug, solution_path=solution_path);
    }
}
