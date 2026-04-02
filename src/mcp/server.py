"""
Ringtail MCP tool server.

Exposes Ringtail's optimisation engine as MCP tools that coding agents
(Cursor, Claude Code, VS Code Copilot, etc.) can call.

Tools
-----
- ``optimize_repo``   – Full profile-driven DAG repo optimisation.
- ``optimize_function`` – Single-function optimisation.
- ``profile_repo``    – Profile only (no optimisation), returns hot-function list.

Run with::

    python -m src.mcp.server          # stdio transport (IDE integration)
    python -m src.mcp.server --sse    # SSE transport (remote/web)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Ringtail",
    description="AI-powered Python code optimisation service",
)


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
        return json.dumps({"error": str(exc), "traceback": traceback.format_exc()})


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
            return json.dumps({"error": f"Function '{function_name}' not found in {file_path}"})

        test_code = None
        if test_file and os.path.isfile(test_file):
            with open(test_file) as f:
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
        return json.dumps({"error": str(exc), "traceback": traceback.format_exc()})


@mcp.tool()
def profile_repo(
    repo_path: str,
    entry_point: str,
    pct_threshold: float = 5.0,
) -> str:
    """Profile a Python repository and return hot-function analysis.

    Runs the entry point under cProfile and identifies bottleneck functions.
    Does not modify any code — useful for agents to decide whether to
    invoke ``optimize_repo``.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository root.
    entry_point:
        Command to exercise the code.
    pct_threshold:
        Minimum percentage of total runtime for a function to be "hot".
    """
    try:
        from src.core.cprofile_analyzer import (
            build_call_dag,
            compute_hotness_threshold,
            run_cprofile_analysis,
        )

        analysis = run_cprofile_analysis(repo_path, entry_point)
        hot = compute_hotness_threshold(analysis, pct_threshold=pct_threshold)
        dag = build_call_dag(analysis, hot)

        functions = []
        for key in hot:
            fp = analysis.functions.get(key)
            if fp is None:
                continue
            functions.append({
                "name": fp.name,
                "module": fp.module,
                "file": fp.file_path,
                "line": fp.lineno,
                "tottime": fp.tottime,
                "cumtime": fp.cumtime,
                "ncalls": fp.ncalls,
                "hotness_pct": fp.hotness_pct,
            })

        functions.sort(key=lambda f: f["hotness_pct"], reverse=True)

        return json.dumps({
            "total_time": analysis.total_time,
            "functions_analyzed": len(analysis.functions),
            "hot_functions": len(hot),
            "dag_levels": len(dag.levels),
            "functions": functions,
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc), "traceback": traceback.format_exc()})


@mcp.resource("ringtail://info")
def get_server_info() -> str:
    """Basic info about the Ringtail MCP server."""
    return json.dumps({
        "name": "Ringtail",
        "description": "AI-powered Python code optimisation service",
        "tools": ["optimize_repo", "optimize_function", "profile_repo"],
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


def main() -> None:
    transport = "stdio"
    if "--sse" in sys.argv:
        transport = "sse"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
