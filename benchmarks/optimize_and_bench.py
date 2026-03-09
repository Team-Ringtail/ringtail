#!/usr/bin/env python3
"""
End-to-end optimization + benchmark pipeline.

Takes a benchmark slug, uses the Anthropic API (Claude) to generate an
optimized solution, tests it in a Blaxel sandbox (or locally), validates
with the existing benchmark tests, and logs everything to a single run log.

Usage:
    python benchmarks/optimize_and_bench.py two_sum
    python benchmarks/optimize_and_bench.py --all
    python benchmarks/optimize_and_bench.py two_sum --backend blaxel
    python benchmarks/optimize_and_bench.py two_sum --model claude-sonnet-4-20250514

All output is captured in  logs/<run_id>.jsonl  — one file per run.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.utils.run_log import RunLog
from src.utils.llm_client import analyze_and_plan, generate_optimized_code

BENCHMARKS_ROOT = os.path.join(REPO_ROOT, "benchmarks")
LEETCODE_DIR = os.path.join(BENCHMARKS_ROOT, "leetcode")

# ---------------------------------------------------------------------------
# Timing: measure execution speed of a solution
# ---------------------------------------------------------------------------

def time_solution(code: str, entry_function: str, spec: dict) -> dict:
    """Run timeit on a solution to measure execution time.

    Returns dict with median_ms, mean_ms, min_ms, runs, or error.
    """
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_time_")
    solution_path = os.path.join(tmp_dir, "solution.py")
    harness_path = os.path.join(tmp_dir, "harness.py")

    try:
        with open(solution_path, "w") as f:
            f.write(code)

        # Build a small call expression from the spec for timing
        call_expr = _build_call_expr(entry_function, spec)
        if not call_expr:
            return {"error": "could not build call expression for timing"}

        harness_code = (
            "import timeit, json, statistics, sys, time\n"
            "sys.path.insert(0, '.')\n"
            f"from solution import {entry_function}\n"
            "# Adaptive: run once to calibrate, then choose iteration count\n"
            f"t0 = time.perf_counter(); {call_expr}; single = time.perf_counter() - t0\n"
            "num = max(1, min(500, int(0.05 / max(single, 1e-9))))\n"
            f"times = timeit.repeat(lambda: {call_expr}, number=num, repeat=5)\n"
            "per_call = [t / num * 1000 for t in times]\n"
            "print(json.dumps({\n"
            '    "median_ms": round(statistics.median(per_call), 4),\n'
            '    "mean_ms": round(statistics.mean(per_call), 4),\n'
            '    "min_ms": round(min(per_call), 4),\n'
            '    "runs": len(per_call),\n'
            '    "iters_per_run": num\n'
            "}))\n"
        )
        with open(harness_path, "w") as f:
            f.write(harness_code)

        result = subprocess.run(
            [sys.executable, "harness.py"],
            capture_output=True, text=True, timeout=30, cwd=tmp_dir,
        )
        if result.returncode != 0:
            return {"error": (result.stderr or result.stdout or "timing failed")[:300]}

        return json.loads(result.stdout.strip())

    except subprocess.TimeoutExpired:
        return {"error": "timing timed out"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _build_call_expr(entry_function: str, spec: dict) -> str:
    """Build a representative function call for timing from the spec.

    Uses known test inputs for common problems, or falls back to a generic
    call.
    """
    slug = spec.get("slug", "")
    difficulty = spec.get("difficulty", "")

    KNOWN_CALLS = {
        "two_sum": "two_sum(list(range(500)) + [9998, 9999], 19997)",
        "three_sum": "threeSum(list(range(-50, 50)))",
        "three_sum_closest": "threeSumClosest(list(range(-50, 50)), 1)",
        "container_with_most_water": "maxArea(list(range(1, 500)))",
        "valid_parentheses": "isValid('([{}])' * 100)",
        "merge_intervals": "merge([[i, i+2] for i in range(0, 1000, 1)])",
        "search_rotated_sorted_array": "search([4,5,6,7,0,1,2], 0)",
        "search_insert_position": "searchInsert(list(range(0, 10000, 2)), 5001)",
        "subsets": "subsets([1,2,3,4,5,6,7,8,9,10])",
        "sort_list": "sortList(None)",
        "add_digits": "addDigits(38)",
        "sqrt_x": "mySqrt(2147395599)",
        "zigzag_conversion": "convert('PAYPALISHIRING' * 50, 7)",
        "string_to_integer_atoi": "myAtoi('   -42')",
        "longest_palindromic_substring": "longestPalindrome('a' * 200)",
        "median_of_two_sorted_arrays": "findMedianSortedArrays(list(range(0,1000,2)), list(range(1,1001,2)))",
    }

    if slug in KNOWN_CALLS:
        return KNOWN_CALLS[slug]

    return f"{entry_function}()"


def discover_problems():
    if not os.path.isdir(LEETCODE_DIR):
        return []
    slugs = []
    for name in sorted(os.listdir(LEETCODE_DIR)):
        path = os.path.join(LEETCODE_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "spec.json")):
            slugs.append(name)
    return slugs


def load_problem(slug: str) -> dict:
    """Load spec + solution + test code for a benchmark problem."""
    problem_dir = os.path.join(LEETCODE_DIR, slug)
    spec_path = os.path.join(problem_dir, "spec.json")
    solution_path = os.path.join(problem_dir, "solution.py")

    with open(spec_path) as f:
        spec = json.load(f)
    with open(solution_path) as f:
        source_code = f.read()

    test_files = [fn for fn in os.listdir(problem_dir) if fn.startswith("test_") and fn.endswith(".py")]
    test_code = ""
    if test_files:
        with open(os.path.join(problem_dir, test_files[0])) as f:
            test_code = f.read()

    return {
        "slug": slug,
        "spec": spec,
        "source_code": source_code,
        "test_code": test_code,
        "problem_dir": problem_dir,
        "solution_path": solution_path,
    }


# ---------------------------------------------------------------------------
# Execution backends
# ---------------------------------------------------------------------------

def run_tests_local(optimized_code: str, problem: dict, log: RunLog) -> dict:
    """Write optimized code to a temp file and run the benchmark tests locally."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix=f"ringtail_{problem['slug']}_", delete=False
    )
    tmp.write(optimized_code)
    tmp.close()

    slug = problem["slug"]
    test_file = None
    for fn in os.listdir(problem["problem_dir"]):
        if fn.startswith("test_") and fn.endswith(".py"):
            test_file = os.path.join(problem["problem_dir"], fn)
            break

    if not test_file:
        log.error(f"No test file found for {slug}")
        os.unlink(tmp.name)
        return {"passed": 0, "failed": 1, "error": "no test file"}

    env = os.environ.copy()
    env["BENCHMARK_SOLUTION"] = tmp.name

    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd=problem["problem_dir"], env=env,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        log.sandbox_exec(backend="local", command="pytest", returncode=-1, error="timeout")
        os.unlink(tmp.name)
        return {"passed": 0, "failed": 1, "time_s": round(elapsed, 3), "error": "timeout"}

    elapsed = time.perf_counter() - t0
    log.sandbox_exec(
        backend="local", command="pytest", returncode=result.returncode,
        stdout_tail=result.stdout[-500:] if result.stdout else "",
    )
    os.unlink(tmp.name)

    if result.returncode != 0:
        return {
            "passed": 0, "failed": 1, "time_s": round(elapsed, 3),
            "error": (result.stderr or result.stdout or "pytest failed")[:500],
        }
    return {"passed": 1, "failed": 0, "time_s": round(elapsed, 3), "stdout": result.stdout}


async def run_tests_blaxel(optimized_code: str, problem: dict, log: RunLog) -> dict:
    """Upload code + tests to a Blaxel sandbox and run pytest inside it."""
    try:
        from blaxel.core import SandboxInstance
    except ImportError:
        log.error("blaxel SDK not installed — pip install blaxel")
        return {"passed": 0, "failed": 1, "error": "blaxel SDK not installed"}

    slug = problem["slug"].replace("_", "-")
    sandbox_name = f"ringtail-{slug}-{os.urandom(4).hex()}"

    sandbox = None
    try:
        create_opts = {
            "name": sandbox_name,
            "image": os.environ.get("BL_IMAGE", "sandbox/ringtail-python:yjetxvb6idjq"),
            "memory": int(os.environ.get("BL_MEMORY_MB", "2048")),
        }
        region = os.environ.get("BL_REGION", "us-pdx-1")
        if region:
            create_opts["region"] = region

        sandbox = await SandboxInstance.create(create_opts)

        await sandbox.fs.write("/workspace/solution.py", optimized_code)
        await sandbox.fs.write("/workspace/test_solution.py", problem["test_code"])

        pip_proc = await sandbox.process.exec({
            "command": "pip install --quiet pytest",
            "working_dir": "/workspace",
            "wait_for_completion": True,
            "timeout": 30000,
        })

        proc = await sandbox.process.exec({
            "name": "run-tests",
            "command": f"cd /workspace && BENCHMARK_SOLUTION=/workspace/solution.py python -m pytest test_solution.py -v --tb=short -q",
            "working_dir": "/workspace",
            "wait_for_completion": True,
            "timeout": 60000,
        })

        stdout = getattr(proc, "stdout", "") or ""
        stderr = getattr(proc, "stderr", "") or ""
        logs_obj = getattr(proc, "logs", None)
        if logs_obj:
            stdout = getattr(logs_obj, "stdout", stdout) or stdout
            stderr = getattr(logs_obj, "stderr", stderr) or stderr
        exit_code = getattr(proc, "exit_code", None)
        if exit_code is None:
            exit_code = getattr(proc, "exitCode", -1)

        log.sandbox_exec(
            backend="blaxel", command="pytest", returncode=exit_code,
            sandbox_name=sandbox_name,
        )

        if exit_code != 0:
            return {
                "passed": 0, "failed": 1, "time_s": 0,
                "error": (stderr or stdout or "pytest failed")[:500],
            }
        return {"passed": 1, "failed": 0, "time_s": 0, "stdout": stdout}

    except Exception as e:
        log.error(f"Blaxel sandbox error: {e}", sandbox_name=sandbox_name)
        return {"passed": 0, "failed": 1, "error": str(e)}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def optimize_one(slug: str, *, backend: str, model: str, log: RunLog) -> dict:
    """Full pipeline for one problem: analyze -> generate -> test -> report."""
    log.event("problem_start", slug=slug, backend=backend, model=model)

    try:
        problem = load_problem(slug)
    except FileNotFoundError as e:
        log.error(f"Problem not found: {slug} ({e})")
        return {"slug": slug, "status": "error", "error": str(e)}

    spec = problem["spec"]
    source_code = problem["source_code"]
    entry_fn = spec.get("entry_function", "")
    function_call = f"{entry_fn}()" if entry_fn else ""

    log.event("loaded_problem", slug=slug, difficulty=spec.get("difficulty"), entry_function=entry_fn)

    # 0. Baseline timing on the original solution
    baseline_timing = time_solution(source_code, entry_fn, spec)
    if "error" in baseline_timing:
        log.event("baseline_timing_error", error=baseline_timing["error"])
    else:
        log.event("baseline_timing", **baseline_timing)

    # 1. Analyze & plan via Anthropic
    try:
        plan = analyze_and_plan(
            source_code,
            criteria={"performance_weight": 0.6, "code_quality_weight": 0.2, "functionality_weight": 0.2},
            function_call=function_call,
            test_cases=[],
            model=model,
            run_log=log,
        )
        log.event("plan_ready", steps=plan.get("steps", []))
    except Exception as e:
        log.error(f"LLM analyze_and_plan failed: {e}")
        return {"slug": slug, "status": "error", "error": f"analyze_and_plan: {e}"}

    # 2. Generate optimized code via Anthropic
    try:
        optimized_code = generate_optimized_code(
            source_code, plan, model=model, run_log=log,
        )
        log.event("code_generated", code_length=len(optimized_code))
    except Exception as e:
        log.error(f"LLM generate_optimized_code failed: {e}")
        return {"slug": slug, "status": "error", "error": f"generate_optimized_code: {e}"}

    # 3. Test in sandbox
    if backend == "blaxel":
        test_result = asyncio.run(run_tests_blaxel(optimized_code, problem, log))
    else:
        test_result = run_tests_local(optimized_code, problem, log)

    passed = test_result.get("passed", 0)
    failed = test_result.get("failed", 0)
    log.benchmark(
        slug=slug, passed=passed, failed=failed,
        time_s=test_result.get("time_s", 0),
    )

    status = "pass" if failed == 0 and "error" not in test_result else "fail"

    # 4. If tests passed, time the optimized code and compare
    timing_comparison = {}
    if status == "pass":
        optimized_timing = time_solution(optimized_code, entry_fn, spec)
        if "error" in optimized_timing:
            log.event("optimized_timing_error", error=optimized_timing["error"])
        else:
            log.event("optimized_timing", **optimized_timing)

            old_ms = baseline_timing.get("median_ms", 0)
            new_ms = optimized_timing.get("median_ms", 0)
            if old_ms > 0:
                speedup = old_ms / new_ms if new_ms > 0 else float("inf")
                pct_change = round((old_ms - new_ms) / old_ms * 100, 1)
            else:
                speedup = 0
                pct_change = 0

            timing_comparison = {
                "baseline_median_ms": old_ms,
                "optimized_median_ms": new_ms,
                "speedup": round(speedup, 2),
                "improvement_pct": pct_change,
            }
            log.event("timing_comparison", slug=slug, **timing_comparison)

    result = {
        "slug": slug,
        "status": status,
        "plan_steps": plan.get("steps", []),
        "optimized_code_length": len(optimized_code),
        "test_result": test_result,
        "timing": timing_comparison,
    }

    log.event("problem_done", slug=slug, status=status)
    return result


def main():
    parser = argparse.ArgumentParser(description="Optimize & benchmark LeetCode problems with Claude + Blaxel")
    parser.add_argument("slug", nargs="?", help="Problem slug (e.g. two_sum)")
    parser.add_argument("--all", action="store_true", help="Run all problems")
    parser.add_argument("--backend", choices=["local", "blaxel"], default="local",
                        help="Execution backend (default: local)")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Anthropic model to use (default: claude-sonnet-4-20250514)")
    args = parser.parse_args()

    if not args.all and not args.slug:
        parser.error("Provide a slug or --all")

    slugs = discover_problems() if args.all else [args.slug]
    run_name = f"optimize-{'all' if args.all else args.slug}"
    log = RunLog(run_name)

    results = {}
    total_pass, total_fail = 0, 0

    for slug in slugs:
        r = optimize_one(slug, backend=args.backend, model=args.model, log=log)
        results[slug] = r
        if r.get("status") == "pass":
            total_pass += 1
        else:
            total_fail += 1

    summary = {
        "total_problems": len(slugs),
        "total_pass": total_pass,
        "total_fail": total_fail,
        "backend": args.backend,
        "model": args.model,
        "results": results,
    }
    log.event("run_summary", **{k: v for k, v in summary.items() if k != "results"})
    log.close()

    print(json.dumps(summary, indent=2, default=str))
    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
