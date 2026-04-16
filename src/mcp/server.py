"""
Ringtail MCP tool server.

Exposes Ringtail's optimisation engine as MCP tools that coding agents
(Cursor, Claude Code, VS Code Copilot, etc.) can call.

Tools
-----
- ``profile_repo``      – Fast structured hotspot analysis for coding agents.
- ``optimize_hotspot``  – Strictly validated patch generation for one hotspot.
- ``submit_optimize_repo_job`` – Async repo optimisation escalation path.
- ``get_optimize_repo_job`` – Poll the async repo optimisation job.
- ``optimize_repo``     – Full profile-driven DAG repo optimisation.
- ``optimize_function`` – Single-function optimisation.

Run with::

    python -m src.mcp.server          # stdio transport (IDE integration)
    python -m src.mcp.server --sse    # SSE transport (remote/web)
"""
from __future__ import annotations

import difflib
import json
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.mcp.acceptance import evaluate_hotspot_acceptance
from src.mcp.contracts import (
    HotspotOptimizationReport,
    HotspotSummary,
    McpError,
    OptimizationAttemptSummary,
    OptimizationMetrics,
    OptimizationTarget,
    PatchArtifact,
    ProfileReport,
    RecommendedTarget,
    ValidationSummary,
)

mcp = FastMCP("Ringtail")

_DEFAULT_PROFILE_LIMIT = 8
_DEFAULT_MIN_SPEEDUP = 1.10


@mcp.tool()
def optimize_repo(
    repo_path: str,
    entry_point: str,
    prompt: str = "optimize for performance",
    publish_pr: bool = False,
    analysis_mode: str = "llm",
    llm_model: str | None = None,
) -> str:
    """Optimise a Python repository using profile-driven DAG analysis.

    Profiles the repo via the entry point, identifies hot functions,
    and optimises them bottom-up through the call graph. Returns a
    JSON summary with per-function diffs and before/after metrics.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository root.
    entry_point:
        Command to exercise the code (e.g. "pytest tests/" or "python main.py").
    prompt:
        Natural language description of what to optimise.
    publish_pr:
        If True and repo is a git checkout, create a branch with optimisations.
    analysis_mode:
        "llm" for real optimisation, "mock" for testing.
    llm_model:
        Override LLM model (default: use RINGTAIL_DEFAULT_LLM_MODEL or claude-opus-4-6).
    """
    try:
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
            return json.dumps({
                "success": True,
                "message": "No significant bottlenecks detected",
                "total_time": analysis.total_time,
                "functions_analyzed": len(analysis.functions),
            })

        dag = build_call_dag(analysis, hot)

        targets = {
            k: {"module": v.module, "name": v.name, "file_path": v.file_path}
            for k, v in dag.nodes.items()
        }
        io_data = capture_function_io(repo_path, entry_point, targets)

        config: dict[str, Any] = {
            "analysis_mode": analysis_mode,
            "max_attempts": 3,
            "max_parallel_candidates": min(len(dag.nodes), 4),
        }
        if llm_model:
            config["llm_model"] = llm_model

        result = optimize_dag(
            repo_path=repo_path,
            dag=dag,
            io_data=io_data,
            config=config,
            entry_point=entry_point,
            baseline_program_time=analysis.total_time,
        )

        summaries = []
        for key, fr in result.function_results.items():
            entry: dict[str, Any] = {
                "function": fr.function_name,
                "file": fr.file_path,
                "success": fr.success,
                "baseline_time": fr.baseline_tottime,
                "attempts": len(fr.attempts),
            }
            if fr.success and fr.optimized_source:
                entry["diff_summary"] = _diff_summary(fr.original_source, fr.optimized_source)
            if fr.error:
                entry["error"] = fr.error
            summaries.append(entry)

        return json.dumps({
            "success": True,
            "total_functions": result.total_functions,
            "optimized": result.successful_optimizations,
            "failed": result.failed_optimizations,
            "baseline_time": result.baseline_total_time,
            "optimized_time": result.optimized_total_time,
            "speedup": result.overall_speedup,
            "baseline_program_time": result.baseline_program_time,
            "optimized_program_time": result.optimized_program_time,
            "program_speedup": result.program_speedup,
            "functions": summaries,
        }, indent=2)

    except Exception as exc:
        return _json_dumps_error("optimize_repo_failed", str(exc))


@mcp.tool()
def optimize_function(
    file_path: str,
    function_name: str,
    test_file: str | None = None,
    analysis_mode: str = "llm",
    llm_model: str | None = None,
) -> str:
    """Optimise a single Python function.

    Reads the function from file_path, runs it through the optimisation
    loop, and returns the optimised code as a diff.

    Parameters
    ----------
    file_path:
        Path to the Python file containing the function.
    function_name:
        Name of the function to optimise.
    test_file:
        Optional path to a pytest file that tests this function.
    analysis_mode:
        "llm" for real optimisation, "mock" for testing.
    llm_model:
        Override LLM model.
    """
    try:
        from src.core.optimization_dag import _extract_function_source
        from src.utils.llm_client_py import analyze_and_plan, generate_optimized_code

        source = _extract_function_source(file_path, function_name)
        if source is None:
            return _json_dumps_error(
                "function_not_found",
                f"Function '{function_name}' not found in {file_path}",
            )

        test_code = None
        if test_file and os.path.isfile(test_file):
            with open(test_file, encoding="utf-8") as f:
                test_code = f.read()

        if analysis_mode == "mock":
            return json.dumps({
                "success": True,
                "function": function_name,
                "optimized_code": source,
                "message": "Mock mode — no changes made",
            })

        plan = analyze_and_plan(
            source_code=source,
            criteria={"focus": "performance"},
            function_call=f"{function_name}()",
            test_cases=[],
            model=llm_model,
        )

        optimized = generate_optimized_code(
            source_code=source,
            plan=plan,
            model=llm_model,
        )

        return json.dumps({
            "success": True,
            "function": function_name,
            "original_code": source,
            "optimized_code": optimized,
            "plan": plan.get("analysis", ""),
            "steps": plan.get("steps", []),
        }, indent=2)

    except Exception as exc:
        return _json_dumps_error("optimize_function_failed", str(exc))


@mcp.tool()
def profile_repo(
    repo_path: str,
    entry_point: str,
    pct_threshold: float = 5.0,
    max_results: int = _DEFAULT_PROFILE_LIMIT,
    timeout_s: int = 300,
) -> str:
    """Profile a Python repository and return hot-function analysis.

    Runs the entry point under cProfile and identifies bottleneck functions.
    Does not modify any code — useful for agents to decide whether to
    invoke ``optimize_hotspot``.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository root.
    entry_point:
        Command to exercise the code.
    pct_threshold:
        Minimum percentage of total runtime for a function to be "hot".
    max_results:
        Maximum number of hotspots to include in the structured response.
    timeout_s:
        Maximum cProfile runtime budget in seconds.
    """
    try:
        from src.core.cprofile_analyzer import (
            build_call_dag,
            compute_hotness_threshold,
            run_cprofile_analysis,
        )

        analysis = run_cprofile_analysis(repo_path, entry_point, timeout=timeout_s)
        hot = compute_hotness_threshold(analysis, pct_threshold=pct_threshold)
        dag = build_call_dag(analysis, hot)
        ranked_hotspots = _rank_hotspots(analysis, hot)
        hotspot_summaries = [
            _build_hotspot_summary(
                key=key,
                function_profile=function_profile,
                dag=dag,
                rank=index,
            )
            for index, (key, function_profile) in enumerate(
                ranked_hotspots[: max(1, max_results)],
                start=1,
            )
        ]
        report = ProfileReport(
            repo_path=repo_path,
            entry_point=entry_point,
            threshold_pct=pct_threshold,
            total_time=analysis.total_time,
            functions_analyzed=len(analysis.functions),
            hot_function_count=len(hot),
            dag_levels=len(dag.levels),
            editable_hotspot_count=sum(1 for item in hotspot_summaries if item.editable),
            recommended_targets=_recommended_targets(hotspot_summaries),
            hotspots=hotspot_summaries,
            message=_profile_message(hotspot_summaries),
            next_action=_profile_next_action(hotspot_summaries),
        )
        return json.dumps(report.to_dict(), indent=2)

    except Exception as exc:
        return _json_dumps_error("profile_repo_failed", str(exc))


@mcp.tool()
def optimize_hotspot(
    repo_path: str,
    entry_point: str,
    hotspot_id: str = "",
    file_path: str = "",
    function_name: str = "",
    analysis_mode: str = "llm",
    llm_model: str | None = None,
    min_speedup: float = _DEFAULT_MIN_SPEEDUP,
    timeout_s: int = 300,
) -> str:
    """Optimise a single profiled hotspot and return a strict validation report."""
    try:
        from src.core.arg_capture import capture_function_io
        from src.core.cprofile_analyzer import CallDAG, compute_hotness_threshold, run_cprofile_analysis
        from src.core.optimization_dag import optimize_dag

        analysis = run_cprofile_analysis(repo_path, entry_point, timeout=timeout_s)
        hot = compute_hotness_threshold(analysis)
        target_key = _resolve_hotspot_target(
            analysis=analysis,
            hot_functions=hot,
            hotspot_id=hotspot_id,
            file_path=file_path,
            function_name=function_name,
        )
        if target_key is None:
            return _json_dumps_error(
                "hotspot_not_found",
                "No matching hot hotspot was found. Pass a hotspot id from profile_repo or a matching file_path/function_name pair.",
                hotspot_id=hotspot_id,
                file_path=file_path,
                function_name=function_name,
            )

        function_profile = analysis.functions[target_key]
        hotspot_summary = _build_hotspot_summary(
            key=target_key,
            function_profile=function_profile,
            dag=CallDAG(levels=[[target_key]], nodes={target_key: function_profile}, edges={}),
            rank=1,
        )
        if not hotspot_summary.editable:
            return _json_dumps_error(
                "hotspot_not_editable",
                hotspot_summary.skip_reason or "Hotspot is not editable.",
                hotspot_id=target_key,
            )

        dag = CallDAG(levels=[[target_key]], nodes={target_key: function_profile}, edges={})
        io_data = capture_function_io(
            repo_path,
            entry_point,
            {
                target_key: {
                    "module": function_profile.module,
                    "name": function_profile.name,
                    "file_path": function_profile.file_path,
                }
            },
        )
        config: dict[str, Any] = {
            "analysis_mode": analysis_mode,
            "max_attempts": 3,
            "max_parallel_candidates": 1,
        }
        if llm_model:
            config["llm_model"] = llm_model

        result = optimize_dag(
            repo_path=repo_path,
            dag=dag,
            io_data=io_data,
            config=config,
            entry_point=entry_point,
            baseline_program_time=analysis.total_time,
        )
        function_result = result.function_results.get(target_key)
        if function_result is None:
            return _json_dumps_error(
                "optimization_result_missing",
                "Optimization finished without a result for the requested hotspot.",
                hotspot_id=target_key,
            )

        tests_passed = any(attempt.test_passed for attempt in function_result.attempts)
        decision = evaluate_hotspot_acceptance(
            tests_passed=tests_passed,
            speedup=function_result.speedup,
            post_profile_completed=result.optimized_program_time is not None,
            min_speedup=min_speedup,
        )
        if not decision.accepted:
            function_result.success = False
            function_result.error = "; ".join(decision.reasons)
            function_result.optimized_source = None
            function_result.optimized_tottime = None
            function_result.speedup = None

        report = _build_hotspot_optimization_report(
            repo_path=repo_path,
            entry_point=entry_point,
            hotspot_id=target_key,
            function_profile=function_profile,
            function_result=function_result,
            baseline_program_time=result.baseline_program_time,
            optimized_program_time=result.optimized_program_time,
            program_speedup=result.program_speedup,
            min_speedup=min_speedup,
            decision=decision,
        )
        return json.dumps(report.to_dict(), indent=2)
    except Exception as exc:
        return _json_dumps_error("optimize_hotspot_failed", str(exc))


@mcp.tool()
def submit_optimize_repo_job(
    repo_url: str,
    entry_point: str,
    prompt: str = "optimize for performance",
    base_branch: str = "main",
    max_targets: int = 3,
    tests_root: str = "tests",
    publish_pr: bool = False,
    analysis_mode: str = "llm",
    llm_model: str | None = None,
) -> str:
    """Submit a long-running repo optimization job as an explicit async escalation path."""
    try:
        from src.core.async_jobs import submit_job

        request: dict[str, Any] = {
            "operation": "run_repo_agent_job",
            "repo_url": repo_url,
            "entry_point": entry_point,
            "prompt": prompt,
            "base_branch": base_branch,
            "max_targets": max_targets,
            "tests_root": tests_root,
            "publish_pr": publish_pr,
            "analysis_mode": analysis_mode,
            "backend_config": {"backend": "local"},
        }
        if llm_model:
            request["llm_model"] = llm_model
        submitted = submit_job(request)
        return json.dumps(
            {
                "success": True,
                "kind": "async_repo_optimization_submission",
                "job_id": submitted.get("job_id", ""),
                "status": submitted.get("status", ""),
                "run_id": submitted.get("run_id", ""),
                "run_log_path": submitted.get("run_log_path", ""),
                "message": "Repo optimization job queued. Poll get_optimize_repo_job for status.",
            },
            indent=2,
        )
    except Exception as exc:
        return _json_dumps_error("submit_optimize_repo_job_failed", str(exc))


@mcp.tool()
def get_optimize_repo_job(job_id: str) -> str:
    """Poll an async repo optimization job submitted through the MCP server."""
    try:
        from src.core.async_jobs import get_job

        job = get_job(job_id)
        return json.dumps(
            {
                "success": job.get("status") != "not_found",
                "kind": "async_repo_optimization_status",
                "job": job,
            },
            indent=2,
        )
    except Exception as exc:
        return _json_dumps_error("get_optimize_repo_job_failed", str(exc), job_id=job_id)


@mcp.resource("ringtail://info")
def get_server_info() -> str:
    """Basic info about the Ringtail MCP server."""
    return json.dumps({
        "name": "Ringtail",
        "description": "AI-powered Python code optimisation service",
        "tools": [
            "profile_repo",
            "optimize_hotspot",
            "submit_optimize_repo_job",
            "get_optimize_repo_job",
            "optimize_repo",
            "optimize_function",
        ],
        "recommended_flow": [
            "profile_repo",
            "optimize_hotspot",
            "submit_optimize_repo_job",
        ],
        "version": "0.1.0",
    })


def _diff_summary(original: str, optimized: str) -> str:
    """Produce a short summary of changes between original and optimised code."""
    orig_lines = original.splitlines()
    opt_lines = optimized.splitlines()
    added = len(opt_lines) - len(orig_lines)
    if added > 0:
        return f"+{added} lines"
    elif added < 0:
        return f"{added} lines"
    return "same line count, logic changed"


def _json_dumps_error(code: str, message: str, **details: str) -> str:
    return json.dumps(McpError(code=code, message=message, details=details or None).to_dict(), indent=2)


def _rank_hotspots(analysis: Any, hot_functions: set[str]) -> list[tuple[str, Any]]:
    ranked = [(key, analysis.functions[key]) for key in hot_functions if key in analysis.functions]
    ranked.sort(key=lambda item: (item[1].hotness_pct, item[1].tottime, item[1].cumtime), reverse=True)
    return ranked


def _resolve_hotspot_target(
    *,
    analysis: Any,
    hot_functions: set[str],
    hotspot_id: str,
    file_path: str,
    function_name: str,
) -> str | None:
    if hotspot_id:
        return hotspot_id if hotspot_id in hot_functions else None
    if not file_path or not function_name:
        return None
    normalized_path = os.path.realpath(file_path)
    for key in hot_functions:
        function_profile = analysis.functions.get(key)
        if function_profile is None:
            continue
        if os.path.realpath(function_profile.file_path) == normalized_path and function_profile.name == function_name:
            return key
    return None


def _build_hotspot_summary(*, key: str, function_profile: Any, dag: Any, rank: int) -> HotspotSummary:
    from src.core.optimization_dag import _extract_function_source, _skip_symbol_reason

    skip_reason = _skip_symbol_reason(function_profile.name)
    if skip_reason is None and _extract_function_source(function_profile.file_path, function_profile.name) is None:
        skip_reason = "no extractable function definition"
    ownership = _classify_ownership(function_profile, dag)
    worth_optimizing = skip_reason is None and ownership != "library_bound"
    recommendation = _hotspot_recommendation(
        function_profile=function_profile,
        ownership=ownership,
        editable=skip_reason is None,
        callers=_node_names(dag, function_profile.callers),
        callees=_node_names(dag, function_profile.callees),
    )
    return HotspotSummary(
        id=key,
        rank=rank,
        module=function_profile.module,
        function=function_profile.name,
        file=function_profile.file_path,
        line=function_profile.lineno,
        tottime=function_profile.tottime,
        cumtime=function_profile.cumtime,
        ncalls=function_profile.ncalls,
        hotness_pct=function_profile.hotness_pct,
        ownership=ownership,
        editable=skip_reason is None,
        worth_optimizing=worth_optimizing,
        skip_reason="" if worth_optimizing else (skip_reason or _ownership_skip_reason(ownership)),
        callers=_node_names(dag, function_profile.callers),
        callees=_node_names(dag, function_profile.callees),
        recommendation=recommendation,
    )


def _classify_ownership(function_profile: Any, dag: Any) -> str:
    hot_callees = [key for key in function_profile.callees if key in dag.nodes]
    if function_profile.cumtime > max(function_profile.tottime * 5.0, function_profile.tottime + 0.05) and not hot_callees:
        return "library_bound"
    if hot_callees:
        return "mixed"
    return "user_code"


def _ownership_skip_reason(ownership: str) -> str:
    if ownership == "library_bound":
        return "time is dominated by downstream library or native work outside editable repo code"
    return ""


def _node_names(dag: Any, keys: list[str]) -> list[str]:
    names: list[str] = []
    for key in keys:
        node = dag.nodes.get(key)
        if node is None or node.name in names:
            continue
        names.append(node.name)
    return names


def _hotspot_recommendation(
    *,
    function_profile: Any,
    ownership: str,
    editable: bool,
    callers: list[str],
    callees: list[str],
) -> str:
    if not editable:
        return "Skip this hotspot because it does not map cleanly to an editable Python function."
    if ownership == "library_bound":
        return "Skip this hotspot for now because most of the time appears to be spent outside editable repo code."
    if function_profile.ncalls >= 1000:
        return "High call count makes this a strong first target for algorithmic or allocation reductions."
    if callers and not callees:
        return "Leaf hotspot with upstream callers; a focused local rewrite is likely to have isolated impact."
    if callees:
        return "This hotspot fans into other work. Inspect repeated inner-loop work and expensive allocations first."
    return "Hot editable function in repo code. This is a reasonable first optimization target."


def _recommended_targets(hotspots: list[HotspotSummary]) -> list[RecommendedTarget]:
    recommendations: list[RecommendedTarget] = []
    for hotspot in hotspots:
        if not hotspot.worth_optimizing:
            continue
        recommendations.append(
            RecommendedTarget(
                id=hotspot.id,
                function=hotspot.function,
                file=hotspot.file,
                reason=hotspot.recommendation,
            )
        )
        if len(recommendations) == 3:
            break
    return recommendations


def _profile_message(hotspots: list[HotspotSummary]) -> str:
    if any(hotspot.worth_optimizing for hotspot in hotspots):
        return "Profile completed. Review recommended_targets and pass one hotspot id to optimize_hotspot."
    return "Profile completed but no editable hotspots cleared the current recommendation gate."


def _profile_next_action(hotspots: list[HotspotSummary]) -> str:
    if any(hotspot.worth_optimizing for hotspot in hotspots):
        return "Call optimize_hotspot with one hotspot id from recommended_targets."
    return "Lower pct_threshold, change the workload, or use submit_optimize_repo_job for a broader async pass."


def _build_hotspot_optimization_report(
    *,
    repo_path: str,
    entry_point: str,
    hotspot_id: str,
    function_profile: Any,
    function_result: Any,
    baseline_program_time: float | None,
    optimized_program_time: float | None,
    program_speedup: float | None,
    min_speedup: float,
    decision: Any,
) -> HotspotOptimizationReport:
    patch = PatchArtifact(
        original_code=function_result.original_source,
        optimized_code=function_result.optimized_source or "",
        diff=_unified_diff(
            function_result.original_source,
            function_result.optimized_source or function_result.original_source,
            function_result.file_path,
        ),
    )
    validation = ValidationSummary(
        accepted=decision.accepted,
        tests_passed=any(attempt.test_passed for attempt in function_result.attempts),
        post_profile_completed=optimized_program_time is not None,
        attempt_count=len(function_result.attempts),
        min_speedup_required=min_speedup,
        acceptance_reasons=decision.reasons,
    )
    metrics = OptimizationMetrics(
        baseline_function_time=function_result.baseline_tottime,
        optimized_function_time=function_result.optimized_tottime,
        function_speedup=function_result.speedup,
        baseline_program_time=baseline_program_time,
        optimized_program_time=optimized_program_time,
        program_speedup=program_speedup,
    )
    attempts = [
        OptimizationAttemptSummary(
            attempt=attempt.attempt,
            test_passed=attempt.test_passed,
            error=attempt.error,
            failure_count=len(attempt.test_output.get("failures", [])),
        )
        for attempt in function_result.attempts
    ]
    return HotspotOptimizationReport(
        repo_path=repo_path,
        entry_point=entry_point,
        hotspot_id=hotspot_id,
        target=OptimizationTarget(
            id=hotspot_id,
            module=function_profile.module,
            function=function_profile.name,
            file=function_profile.file_path,
            line=function_profile.lineno,
            tottime=function_profile.tottime,
            hotness_pct=function_profile.hotness_pct,
        ),
        validation=validation,
        metrics=metrics,
        attempts=attempts,
        patch=patch,
        message=(
            "Hotspot optimization accepted."
            if decision.accepted
            else "No patch was accepted for this hotspot."
        ),
        error=(
            None
            if decision.accepted
            else {
                "code": "optimization_rejected",
                "message": function_result.error or "Optimization did not meet the strict acceptance gate.",
            }
        ),
        success=decision.accepted,
    )


def _unified_diff(original: str, optimized: str, file_path: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            optimized.splitlines(),
            fromfile=file_path,
            tofile=file_path,
            lineterm="",
        )
    )


def main() -> None:
    transport = "stdio"
    if "--sse" in sys.argv:
        transport = "sse"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
