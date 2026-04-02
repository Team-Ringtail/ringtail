"""
DAG-based optimization orchestrator.

Traverses the call-graph DAG bottom-up, optimising hot functions in parallel
at each level.  Each function gets up to ``max_attempts`` tries, with full
context from prior attempts passed to the LLM so it can learn from failures
without being told what to avoid.
"""
from __future__ import annotations

import ast
import concurrent.futures
import os
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.arg_capture import IOPair
from src.core.cprofile_analyzer import (
    CallDAG,
    FunctionProfile,
    run_cprofile_analysis,
)
from src.core.snapshot_tester import (
    generate_snapshot_tests,
    merge_with_repo_tests,
    run_snapshot_tests,
)

_MIN_ACCEPTABLE_SPEEDUP = 1.0


@dataclass
class AttemptResult:
    attempt: int
    optimized_code: str
    test_passed: bool
    test_output: dict[str, Any] = field(default_factory=dict)
    profile_result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class FunctionResult:
    func_key: str
    function_name: str
    file_path: str
    original_source: str
    optimized_source: str | None
    success: bool
    attempts: list[AttemptResult]
    baseline_tottime: float
    optimized_tottime: float | None
    speedup: float | None
    error: str = ""
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class DAGResult:
    function_results: dict[str, FunctionResult]
    baseline_total_time: float | None
    optimized_total_time: float | None
    overall_speedup: float | None
    levels_processed: int
    total_functions: int
    successful_optimizations: int
    failed_optimizations: int
    skipped_functions: int
    skipped_by_reason: dict[str, int]


def optimize_dag(
    repo_path: str,
    dag: CallDAG,
    io_data: dict[str, list[IOPair]],
    config: dict[str, Any],
    entry_point: str,
    repo_tests: dict[str, str] | None = None,
    run_log: Any = None,
) -> DAGResult:
    """Optimise all functions in *dag* bottom-up, level by level.

    Parameters
    ----------
    repo_path:
        Root of the cloned repo.
    dag:
        The call-graph DAG from ``build_call_dag``.
    io_data:
        Captured IO pairs per function key from ``capture_function_io``.
    config:
        Agent config dict (``llm_model``, ``analysis_mode``, ``max_attempts``, etc.).
    entry_point:
        The profiling entry point command.
    repo_tests:
        Optional mapping of function key → existing pytest code from the repo.
    run_log:
        Optional RunLog for tracking LLM calls.
    """
    max_workers = config.get("max_parallel_candidates", 3)
    max_attempts = config.get("max_attempts", 3)
    llm_model = config.get("llm_model", None)
    analysis_mode = config.get("analysis_mode", "llm")

    results: dict[str, FunctionResult] = {}
    successful = 0
    failed = 0
    skipped = 0
    skipped_by_reason: dict[str, int] = {}

    for level_idx, level_keys in enumerate(dag.levels):
        futures: dict[str, concurrent.futures.Future] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for func_key in level_keys:
                fp = dag.nodes.get(func_key)
                if fp is None:
                    skipped += 1
                    _count_skip(skipped_by_reason, "missing profiler node")
                    continue

                non_function_reason = _skip_symbol_reason(fp.name)
                if non_function_reason is not None:
                    skipped += 1
                    _count_skip(skipped_by_reason, non_function_reason)
                    results[func_key] = FunctionResult(
                        func_key=func_key,
                        function_name=fp.name,
                        file_path=fp.file_path,
                        original_source="",
                        optimized_source=None,
                        success=False,
                        attempts=[],
                        baseline_tottime=fp.tottime,
                        optimized_tottime=None,
                        speedup=None,
                        error=non_function_reason,
                        skipped=True,
                        skip_reason=non_function_reason,
                    )
                    continue

                source = _extract_function_source(fp.file_path, fp.name)
                if source is None:
                    skipped += 1
                    _count_skip(skipped_by_reason, "no extractable function definition")
                    results[func_key] = FunctionResult(
                        func_key=func_key,
                        function_name=fp.name,
                        file_path=fp.file_path,
                        original_source="",
                        optimized_source=None,
                        success=False,
                        attempts=[],
                        baseline_tottime=fp.tottime,
                        optimized_tottime=None,
                        speedup=None,
                        error="no extractable function definition",
                        skipped=True,
                        skip_reason="no extractable function definition",
                    )
                    continue

                io_pairs = io_data.get(func_key, [])
                test_code = _build_test_code(fp.name, io_pairs, source, repo_tests, func_key)

                future = executor.submit(
                    optimize_single_function,
                    func_key=func_key,
                    func_profile=fp,
                    source=source,
                    test_code=test_code,
                    dag=dag,
                    max_attempts=max_attempts,
                    llm_model=llm_model,
                    analysis_mode=analysis_mode,
                    run_log=run_log,
                )
                futures[func_key] = future

            for func_key, future in futures.items():
                try:
                    result = future.result(timeout=600)
                    results[func_key] = result
                    if result.success:
                        successful += 1
                        _write_optimized_function(result)
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    fp = dag.nodes[func_key]
                    results[func_key] = FunctionResult(
                        func_key=func_key,
                        function_name=fp.name,
                        file_path=fp.file_path,
                        original_source="",
                        optimized_source=None,
                        success=False,
                        attempts=[],
                        baseline_tottime=fp.tottime,
                        optimized_tottime=None,
                        speedup=None,
                        error=str(exc),
                    )

    # Full re-profile after all optimisations
    baseline_total = None
    optimized_total = None
    overall_speedup = None
    try:
        post_analysis = run_cprofile_analysis(repo_path, entry_point, timeout=300)
        _apply_post_profile_timings(results, post_analysis)
        rejected_regressions = _reject_slower_results(results)
        if rejected_regressions > 0:
            post_analysis = run_cprofile_analysis(repo_path, entry_point, timeout=300)
            _apply_post_profile_timings(results, post_analysis)
            successful = sum(1 for result in results.values() if result.success)
            failed = sum(
                1 for result in results.values()
                if (not result.success) and (not result.skipped)
            )
        baseline_total, optimized_total, overall_speedup = _comparable_speedup_totals(results)
    except Exception as exc:
        raise RuntimeError(f"Post-optimization profiling failed: {exc}") from exc

    return DAGResult(
        function_results=results,
        baseline_total_time=baseline_total,
        optimized_total_time=optimized_total,
        overall_speedup=overall_speedup,
        levels_processed=len(dag.levels),
        total_functions=len(dag.nodes),
        successful_optimizations=successful,
        failed_optimizations=failed,
        skipped_functions=skipped,
        skipped_by_reason=skipped_by_reason,
    )


def optimize_single_function(
    func_key: str,
    func_profile: FunctionProfile,
    source: str,
    test_code: str,
    dag: CallDAG,
    max_attempts: int = 3,
    llm_model: str | None = None,
    analysis_mode: str = "llm",
    run_log: Any = None,
) -> FunctionResult:
    """Optimise a single function with up to *max_attempts* tries.

    Each failed attempt is recorded and its full context (code, errors,
    performance data) is provided to subsequent attempts as informational
    history — the LLM decides how to use it.
    """
    from src.utils.llm_client_py import analyze_and_plan, generate_optimized_code

    attempts: list[AttemptResult] = []
    profiling_context = _build_profiling_context(func_profile, dag)

    for attempt_num in range(1, max_attempts + 1):
        try:
            feedback = _build_attempt_feedback(attempts) if attempts else None

            criteria = {
                "profiling_context": profiling_context,
                "focus": "performance",
                "attempt_number": attempt_num,
                "max_attempts": max_attempts,
            }

            if analysis_mode == "mock":
                plan = {"steps": ["mock optimization"], "analysis": "mock", "estimated_time_sec": 0}
                optimized_code = source
            else:
                plan = analyze_and_plan(
                    source_code=source,
                    criteria=criteria,
                    function_call=f"{func_profile.name}()",
                    test_cases=[],
                    model=llm_model,
                    feedback=feedback,
                    run_log=run_log,
                )

                optimized_code = generate_optimized_code(
                    source_code=source,
                    plan=plan,
                    model=llm_model,
                    run_log=run_log,
                )

            # Run tests
            test_result = {"passed": True, "total": 0, "failures": []}
            if test_code:
                test_result = run_snapshot_tests(optimized_code, test_code)

            attempt = AttemptResult(
                attempt=attempt_num,
                optimized_code=optimized_code,
                test_passed=test_result.get("passed", False),
                test_output=test_result,
            )
            attempts.append(attempt)

            if attempt.test_passed:
                return FunctionResult(
                    func_key=func_key,
                    function_name=func_profile.name,
                    file_path=func_profile.file_path,
                    original_source=source,
                    optimized_source=optimized_code,
                    success=True,
                    attempts=attempts,
                    baseline_tottime=func_profile.tottime,
                    optimized_tottime=None,
                    speedup=None,
                )

        except Exception as exc:
            attempts.append(AttemptResult(
                attempt=attempt_num,
                optimized_code="",
                test_passed=False,
                error=str(exc),
            ))

    return FunctionResult(
        func_key=func_key,
        function_name=func_profile.name,
        file_path=func_profile.file_path,
        original_source=source,
        optimized_source=None,
        success=False,
        attempts=attempts,
        baseline_tottime=func_profile.tottime,
        optimized_tottime=None,
        speedup=None,
        error=f"Failed after {max_attempts} attempts",
    )


def _skip_symbol_reason(function_name: str) -> str | None:
    if function_name.startswith("<") and function_name.endswith(">"):
        return "non-function profiler symbol"
    if not function_name.isidentifier():
        return "non-function profiler symbol"
    return None


def _count_skip(skipped_by_reason: dict[str, int], reason: str) -> None:
    skipped_by_reason[reason] = skipped_by_reason.get(reason, 0) + 1


def _apply_post_profile_timings(results: dict[str, FunctionResult], post_analysis: Any) -> None:
    post_totals: dict[tuple[str, str], float] = {}
    for fp in post_analysis.functions.values():
        key = (os.path.realpath(fp.file_path), fp.name)
        post_totals[key] = post_totals.get(key, 0.0) + float(fp.tottime)

    for result in results.values():
        if not result.success:
            continue
        key = (os.path.realpath(result.file_path), result.function_name)
        optimized_tottime = post_totals.get(key, None)
        if optimized_tottime is None:
            continue
        result.optimized_tottime = optimized_tottime
        if optimized_tottime > 0.0 and result.baseline_tottime > 0.0:
            result.speedup = result.baseline_tottime / optimized_tottime


def _comparable_speedup_totals(results: dict[str, FunctionResult]) -> tuple[float | None, float | None, float | None]:
    baseline_total = 0.0
    optimized_total = 0.0
    measured = 0
    for result in results.values():
        if not result.success or result.optimized_tottime is None:
            continue
        if result.baseline_tottime <= 0.0 or result.optimized_tottime <= 0.0:
            continue
        baseline_total += result.baseline_tottime
        optimized_total += result.optimized_tottime
        measured += 1
    if measured == 0 or optimized_total <= 0.0:
        return None, None, None
    return baseline_total, optimized_total, baseline_total / optimized_total


def _reject_slower_results(results: dict[str, FunctionResult]) -> int:
    rejected = 0
    for result in results.values():
        if not result.success or result.speedup is None:
            continue
        if result.speedup >= _MIN_ACCEPTABLE_SPEEDUP:
            continue
        _restore_original_function(result)
        result.success = False
        result.error = f"Rejected: slower after profiling ({result.speedup:.2f}x)"
        result.optimized_source = None
        result.optimized_tottime = None
        result.speedup = None
        rejected += 1
    return rejected


def _build_profiling_context(fp: FunctionProfile, dag: CallDAG) -> str:
    """Build a human-readable profiling context string for the LLM."""
    lines = [
        f"Function: {fp.name} ({fp.module})",
        f"Runtime: {fp.tottime:.4f}s own time, {fp.cumtime:.4f}s cumulative",
        f"Hotness: {fp.hotness_pct:.1f}% of total program runtime",
        f"Called {fp.ncalls} times",
    ]

    callers = [dag.nodes[c].name for c in fp.callers if c in dag.nodes]
    callees = [dag.nodes[c].name for c in fp.callees if c in dag.nodes]
    if callers:
        lines.append(f"Called by: {', '.join(callers)}")
    if callees:
        lines.append(f"Calls: {', '.join(callees)}")

    return "\n".join(lines)


def _build_attempt_feedback(attempts: list[AttemptResult]) -> dict[str, Any]:
    """Build informational feedback from all prior attempts.

    Presents facts only — no prescriptive instructions.
    """
    history = []
    for a in attempts:
        entry: dict[str, Any] = {
            "attempt": a.attempt,
            "test_passed": a.test_passed,
        }
        if a.error:
            entry["error"] = a.error
        if a.test_output.get("failures"):
            entry["failures"] = a.test_output["failures"][:5]
        if a.optimized_code:
            entry["previous_code"] = a.optimized_code[:2000]
        history.append(entry)

    return {
        "type": "retry_with_history",
        "attempt_history": history,
    }


def _build_test_code(
    function_name: str,
    io_pairs: list[IOPair],
    source: str,
    repo_tests: dict[str, str] | None,
    func_key: str,
) -> str:
    """Combine snapshot tests and repo tests into a single test file."""
    snapshot_code = generate_snapshot_tests(function_name, io_pairs, source)
    repo_test_code = (repo_tests or {}).get(func_key)
    return merge_with_repo_tests(snapshot_code, repo_test_code)


def _extract_function_source(file_path: str, function_name: str) -> str | None:
    """Extract a function's source code from a Python file using AST."""
    if not os.path.isfile(file_path):
        return None
    try:
        source = open(file_path).read()
        tree = ast.parse(source)
    except Exception:
        return None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                lines = source.splitlines()
                start = node.lineno - 1
                end = node.end_lineno if node.end_lineno else start + 1
                return "\n".join(lines[start:end])
    return None


def _write_optimized_function(result: FunctionResult) -> None:
    """Replace the original function in its source file with the optimised version."""
    if not result.success or not result.optimized_source:
        return
    _replace_function_source(result.file_path, result.function_name, result.optimized_source)


def _restore_original_function(result: FunctionResult) -> None:
    if not result.original_source:
        return
    _replace_function_source(result.file_path, result.function_name, result.original_source)


def _replace_function_source(file_path: str, function_name: str, replacement_source: str) -> None:
    if not os.path.isfile(file_path):
        return

    try:
        source = open(file_path).read()
        tree = ast.parse(source)
    except Exception:
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                lines = source.splitlines()
                start = node.lineno - 1
                end = node.end_lineno if node.end_lineno else start + 1

                indent = ""
                original_line = lines[start] if start < len(lines) else ""
                indent = original_line[: len(original_line) - len(original_line.lstrip())]

                optimized_lines = replacement_source.splitlines()
                indented = []
                for i, line in enumerate(optimized_lines):
                    if i == 0:
                        indented.append(indent + line.lstrip())
                    elif line.strip():
                        indented.append(indent + line)
                    else:
                        indented.append("")

                new_lines = lines[:start] + indented + lines[end:]
                with open(file_path, "w") as f:
                    updated_source = "\n".join(new_lines)
                    if source.endswith("\n"):
                        updated_source += "\n"
                    f.write(updated_source)
                return
