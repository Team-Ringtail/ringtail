#!/usr/bin/env python3
"""
Run one or all LeetCode benchmarks. Reports pass/fail and timing.
Usage:
  python benchmarks/run_benchmark.py <slug>           # run one problem
  python benchmarks/run_benchmark.py --all            # run all under benchmarks/leetcode/
  BENCHMARK_SOLUTION=/path/to/optimized.py python benchmarks/run_benchmark.py <slug>  # run against optimized code

Exit code: 0 if all run and passed, 1 otherwise.
Output: JSON to stdout with passed, failed, time_seconds, errors (if any).
"""
import argparse
import json
import os
import subprocess
import sys
import time


BENCHMARKS_ROOT = os.path.dirname(os.path.abspath(__file__))
LEETCODE_DIR = os.path.join(BENCHMARKS_ROOT, "leetcode")


def discover_problems():
    """Return list of problem slugs (directory names under benchmarks/leetcode/)."""
    if not os.path.isdir(LEETCODE_DIR):
        return []
    slugs = []
    for name in os.listdir(LEETCODE_DIR):
        path = os.path.join(LEETCODE_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "spec.json")):
            slugs.append(name)
    return sorted(slugs)


def run_one(slug: str, solution_path: str | None = None) -> dict:
    """Run tests for one problem. Return dict with passed, failed, time_seconds, error."""
    problem_dir = os.path.join(LEETCODE_DIR, slug)
    if not os.path.isdir(problem_dir):
        return {"passed": 0, "failed": 0, "time_seconds": 0, "error": f"unknown slug: {slug}"}

    # Find test file
    test_files = [f for f in os.listdir(problem_dir) if f.startswith("test_") and f.endswith(".py")]
    if not test_files:
        return {"passed": 0, "failed": 0, "time_seconds": 0, "error": f"no test_*.py in {slug}"}

    env = os.environ.copy()
    if solution_path and os.path.isfile(solution_path):
        env["BENCHMARK_SOLUTION"] = os.path.abspath(solution_path)

    test_path = os.path.join(problem_dir, test_files[0])
    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "-q"]
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(test_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return {"passed": 0, "failed": 1, "time_seconds": round(elapsed, 3), "error": "timeout"}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {"passed": 0, "failed": 1, "time_seconds": round(elapsed, 3), "error": str(e)}

    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        return {
            "passed": 0,
            "failed": 1,
            "time_seconds": round(elapsed, 3),
            "error": result.stderr or result.stdout or "pytest failed",
        }

    # Parse pytest -q output for counts if needed; for simplicity we just report pass
    return {
        "passed": 1,
        "failed": 0,
        "time_seconds": round(elapsed, 3),
        "stdout": result.stdout,
    }


def main():
    parser = argparse.ArgumentParser(description="Run LeetCode benchmarks")
    parser.add_argument("slug", nargs="?", help="Problem slug (e.g. two_sum)")
    parser.add_argument("--all", action="store_true", help="Run all discovered problems")
    parser.add_argument("--solution", "-s", help="Path to solution file (e.g. optimized code)")
    parser.add_argument("--json", action="store_true", default=True, help="Output JSON (default)")
    parser.add_argument("--no-json", action="store_false", dest="json", help="Human-readable output")
    args = parser.parse_args()

    if args.all:
        slugs = discover_problems()
        if not slugs:
            out = {"results": [], "total_passed": 0, "total_failed": 0, "error": "no problems found"}
            print(json.dumps(out, indent=2))
            sys.exit(1)
        results = {}
        total_passed, total_failed = 0, 0
        for slug in slugs:
            r = run_one(slug, args.solution)
            results[slug] = r
            total_passed += r.get("passed", 0)
            total_failed += r.get("failed", 0)
        out = {
            "results": results,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "time_seconds": round(sum(r.get("time_seconds", 0) for r in results.values()), 3),
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            for slug, r in results.items():
                status = "PASS" if r.get("failed", 0) == 0 else "FAIL"
                print(f"{slug}: {status} ({r.get('time_seconds', 0):.3f}s)")
            print(f"Total: {total_passed} passed, {total_failed} failed")
        sys.exit(0 if total_failed == 0 else 1)
    else:
        if not args.slug:
            parser.error("slug required unless --all")
        r = run_one(args.slug, args.solution)
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            if r.get("error"):
                print("FAIL:", r["error"])
            else:
                print(f"PASS ({r.get('time_seconds', 0):.3f}s)")
        sys.exit(0 if r.get("failed", 0) == 0 and "error" not in r else 1)


if __name__ == "__main__":
    main()
