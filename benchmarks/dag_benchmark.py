"""
DAG pipeline benchmark harness.

Clones each repo in dag_repos.json, runs the full profile-driven DAG
optimisation pipeline, and records per-function and overall metrics.

Usage::

    python benchmarks/dag_benchmark.py                    # all repos
    python benchmarks/dag_benchmark.py --repo marshmallow  # single repo
    python benchmarks/dag_benchmark.py --dry-run           # profile only, no optimisation
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPOS_FILE = SCRIPT_DIR / "dag_repos.json"
RESULTS_DIR = SCRIPT_DIR / "dag_results"


def load_repos(filter_name: str | None = None) -> list[dict[str, Any]]:
    with open(REPOS_FILE) as f:
        data = json.load(f)
    repos = data.get("repos", [])
    if filter_name:
        repos = [r for r in repos if r["name"] == filter_name]
    return repos


def clone_repo(repo_url: str, dest: str, timeout: int = 120) -> bool:
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, dest],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode == 0


def install_deps(repo_path: str, timeout: int = 120) -> bool:
    reqs = os.path.join(repo_path, "requirements.txt")
    if os.path.isfile(reqs):
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", reqs, "-q"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0

    setup_py = os.path.join(repo_path, "setup.py")
    pyproject = os.path.join(repo_path, "pyproject.toml")
    if os.path.isfile(setup_py) or os.path.isfile(pyproject):
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0

    return True


def run_profile_only(repo_path: str, entry_point: str) -> dict[str, Any]:
    """Profile-only mode: identify hot functions without optimising."""
    from src.core.cprofile_analyzer import (
        build_call_dag,
        compute_hotness_threshold,
        run_cprofile_analysis,
    )

    analysis = run_cprofile_analysis(repo_path, entry_point)
    hot = compute_hotness_threshold(analysis)
    dag = build_call_dag(analysis, hot)

    functions = []
    for key in hot:
        fp = analysis.functions.get(key)
        if fp:
            functions.append({
                "name": fp.name,
                "module": fp.module,
                "tottime": fp.tottime,
                "hotness_pct": fp.hotness_pct,
                "ncalls": fp.ncalls,
            })
    functions.sort(key=lambda f: f["hotness_pct"], reverse=True)

    return {
        "total_time": analysis.total_time,
        "functions_analyzed": len(analysis.functions),
        "hot_functions": len(hot),
        "dag_levels": len(dag.levels),
        "functions": functions,
    }


def run_full_pipeline(repo_path: str, entry_point: str, analysis_mode: str = "llm") -> dict[str, Any]:
    """Full DAG optimisation pipeline."""
    from src.core.arg_capture import capture_function_io
    from src.core.cprofile_analyzer import (
        build_call_dag,
        compute_hotness_threshold,
        run_cprofile_analysis,
    )
    from src.core.optimization_dag import optimize_dag

    analysis = run_cprofile_analysis(repo_path, entry_point)
    hot = compute_hotness_threshold(analysis)

    if not hot:
        return {
            "total_time": analysis.total_time,
            "hot_functions": 0,
            "message": "No significant bottlenecks detected",
        }

    dag = build_call_dag(analysis, hot)

    targets = {
        k: {"module": v.module, "name": v.name, "file_path": v.file_path}
        for k, v in dag.nodes.items()
    }
    io_data = capture_function_io(repo_path, entry_point, targets)

    config = {
        "analysis_mode": analysis_mode,
        "max_attempts": 3,
        "max_parallel_candidates": min(len(dag.nodes), 4),
    }

    result = optimize_dag(
        repo_path=repo_path,
        dag=dag,
        io_data=io_data,
        config=config,
        entry_point=entry_point,
    )

    function_results = []
    for key, fr in result.function_results.items():
        function_results.append({
            "function": fr.function_name,
            "file": fr.file_path,
            "success": fr.success,
            "baseline_tottime": fr.baseline_tottime,
            "attempts": len(fr.attempts),
            "error": fr.error or None,
        })

    return {
        "total_functions": result.total_functions,
        "successful": result.successful_optimizations,
        "failed": result.failed_optimizations,
        "skipped": result.skipped_functions,
        "baseline_total_time": result.baseline_total_time,
        "optimized_total_time": result.optimized_total_time,
        "overall_speedup": result.overall_speedup,
        "functions": function_results,
    }


def benchmark_repo(repo_config: dict[str, Any], dry_run: bool = False, analysis_mode: str = "llm") -> dict[str, Any]:
    name = repo_config["name"]
    repo_url = repo_config["repo_url"]
    entry_point = repo_config["entry_point"]

    temp_dir = tempfile.mkdtemp(prefix=f"ringtail_bench_{name}_")
    repo_path = os.path.join(temp_dir, "repo")

    result: dict[str, Any] = {
        "name": name,
        "repo_url": repo_url,
        "category": repo_config.get("category", ""),
        "entry_point": entry_point,
    }

    try:
        print(f"\n{'='*60}")
        print(f"Benchmarking: {name}")
        print(f"{'='*60}")

        print(f"  Cloning {repo_url}...")
        t0 = time.time()
        if not clone_repo(repo_url, repo_path):
            result["error"] = "Clone failed"
            return result
        result["clone_time_s"] = time.time() - t0

        print("  Installing dependencies...")
        t0 = time.time()
        install_deps(repo_path)
        result["install_time_s"] = time.time() - t0

        t0 = time.time()
        if dry_run:
            print(f"  Profiling with entry point: {entry_point}")
            profile = run_profile_only(repo_path, entry_point)
            result["profile"] = profile
            print(f"  Found {profile['hot_functions']} hot functions in {profile['total_time']:.3f}s total time")
        else:
            print(f"  Running full pipeline with entry point: {entry_point}")
            pipeline = run_full_pipeline(repo_path, entry_point, analysis_mode)
            result["pipeline"] = pipeline
            if "overall_speedup" in pipeline and pipeline["overall_speedup"]:
                print(f"  Speedup: {pipeline['overall_speedup']:.2f}x")

        result["wall_time_s"] = time.time() - t0

    except Exception as exc:
        result["error"] = str(exc)
        print(f"  ERROR: {exc}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="DAG pipeline benchmark harness")
    parser.add_argument("--repo", help="Run only this repo (by name)")
    parser.add_argument("--dry-run", action="store_true", help="Profile only, no optimisation")
    parser.add_argument("--mock", action="store_true", help="Use mock analysis mode (no LLM calls)")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    repos = load_repos(args.repo)
    if not repos:
        print(f"No repos found" + (f" matching '{args.repo}'" if args.repo else ""))
        sys.exit(1)

    analysis_mode = "mock" if args.mock else "llm"
    results = []
    for repo in repos:
        result = benchmark_repo(repo, dry_run=args.dry_run, analysis_mode=analysis_mode)
        results.append(result)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output or str(RESULTS_DIR / f"dag_bench_{int(time.time())}.json")
    with open(output_path, "w") as f:
        json.dump({"results": results}, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    for r in results:
        name = r["name"]
        if "error" in r:
            print(f"  {name}: ERROR - {r['error']}")
        elif "pipeline" in r:
            p = r["pipeline"]
            print(f"  {name}: {p.get('successful', 0)}/{p.get('total_functions', 0)} optimised, "
                  f"speedup={p.get('overall_speedup', 'N/A')}, "
                  f"wall={r.get('wall_time_s', 0):.1f}s")
        elif "profile" in r:
            p = r["profile"]
            print(f"  {name}: {p['hot_functions']} hot functions, "
                  f"total_time={p['total_time']:.3f}s (profile only)")

    print(f"\nResults written to: {output_path}")


if __name__ == "__main__":
    main()
