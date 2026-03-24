"""
Ringtail SDK -- stable programmatic interface for code optimization.

Usage::

    from src.sdk import optimize_function, optimize_code, optimize_repo
    from src.sdk import discover_targets, rank_targets

    result = optimize_function("path/to/file.py", "slow_sum")
    result = optimize_code("def slow_add(n): ...", function_call="slow_add(5000)")
    result = optimize_repo("/path/to/repo", prompt="make this faster")
"""
from __future__ import annotations

from typing import Any, TypedDict

from src.core.optimization_request_contract import normalize_request_defaults
from src.core.worker_runner import run_local_worker_request


class OptimizationResult(TypedDict, total=False):
    """Structured result from an optimization run."""

    optimized_code: str
    iteration_number: int
    metrics: dict[str, Any]
    baseline_metrics: dict[str, Any]
    test_passed: bool
    improvement_ratio: float
    termination_reason: str
    converged: bool
    error: str
    is_significant: bool
    confidence: float
    run_id: str
    run_log_path: str
    summary_stats: dict[str, Any]
    artifacts: dict[str, str]


class RepoResult(TypedDict, total=False):
    """Structured result from a repo-agent optimization run."""

    success: bool
    repo_url: str
    selected_target: dict[str, str]
    candidate_count: int
    evaluated_candidate_count: int
    winner_result: dict[str, Any]
    validation_result: dict[str, Any]
    pull_request: dict[str, Any]
    summary_stats: dict[str, Any]
    artifacts: dict[str, Any]
    error: str


class RankedTarget(TypedDict, total=False):
    """A single ranked optimization candidate."""

    source_file: str
    function_name: str
    function_call: str
    median_ms: float
    peak_memory_kb: float
    cyclomatic_complexity: int
    discovered_test_count: int


def _run_worker(request: dict[str, Any]) -> Any:
    """Execute a normalized optimization request through the local Jac worker."""
    worker = run_local_worker_request(request)
    result = worker.get("result")
    if result is None:
        stderr = str(worker.get("stderr", ""))
        raise RuntimeError(f"Worker failed (exit {worker.get('returncode')}): {stderr}")
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(str(result["error"]))
    if worker.get("returncode", 1) != 0:
        stderr = str(worker.get("stderr", ""))
        raise RuntimeError(f"Worker failed (exit {worker.get('returncode')}): {stderr}")
    return result


def optimize_code(
    source_code: str,
    *,
    function_call: str,
    function_name: str = "",
    test_cases: list[dict[str, Any]] | None = None,
    config_name: str = "",
    analysis_mode: str = "",
    llm_model: str = "",
) -> OptimizationResult:
    """
    Optimize a code snippet directly. No server required.

    Args:
        source_code: Python source containing the target function.
        function_call: How to invoke the function (e.g. ``"slow_add(5000)"``).
        function_name: Name of the function to optimize (auto-detected if omitted).
        test_cases: Optional list of ``{"call": ..., "expected": ...}`` dicts.
        config_name: Named agent config profile (default: ``"live-fast"``).
        analysis_mode: ``"llm"`` or ``"heuristic"``.
        llm_model: Override the LLM model for this run.

    Returns:
        Optimization result with ``optimized_code``, ``metrics``, etc.
    """
    payload: dict[str, Any] = {
        "operation": "optimize_input",
        "input": {
            "source_code": source_code,
            "function_call": function_call,
            "function_name": function_name,
            "test_cases": test_cases or [],
        },
    }
    if config_name:
        payload["config_name"] = config_name
    if analysis_mode:
        payload["analysis_mode"] = analysis_mode
    if llm_model:
        payload["input"]["llm_model"] = llm_model
    return _run_worker(normalize_request_defaults(payload))  # type: ignore[return-value]


def optimize_function(
    file_path: str,
    function_name: str,
    *,
    function_call: str = "",
    tests_root: str = "tests",
    config_name: str = "",
    analysis_mode: str = "",
    llm_model: str = "",
) -> OptimizationResult:
    """
    Optimize a function from a file on disk. No server required.

    Args:
        file_path: Absolute or relative path to the Python source file.
        function_name: Name of the function to optimize.
        function_call: How to invoke it (auto-inferred if omitted).
        tests_root: Directory to search for existing tests.
        config_name: Named agent config profile.
        analysis_mode: ``"llm"`` or ``"heuristic"``.
        llm_model: Override the LLM model for this run.

    Returns:
        Optimization result with ``optimized_code``, ``metrics``, etc.
    """
    from pathlib import Path

    resolved = str(Path(file_path).expanduser().resolve())
    payload: dict[str, Any] = {
        "operation": "optimize_file_function",
        "file_path": resolved,
        "function_name": function_name,
        "tests_root": tests_root,
    }
    if function_call:
        payload["function_call"] = function_call
    if config_name:
        payload["config_name"] = config_name
    if analysis_mode:
        payload["analysis_mode"] = analysis_mode
    if llm_model:
        payload["llm_model"] = llm_model
    return _run_worker(normalize_request_defaults(payload))  # type: ignore[return-value]


def optimize_repo(
    repo_url: str,
    *,
    prompt: str = "make this faster",
    base_branch: str = "main",
    max_targets: int = 3,
    tests_root: str = "tests",
    config_name: str = "",
    publish_pr: bool = False,
    test_command: str = "",
    setup_commands: list[str] | None = None,
    backend: str = "local",
) -> RepoResult:
    """
    Optimize the hottest functions in a repository. No server required.

    Args:
        repo_url: GitHub HTTPS URL or local filesystem path.
        prompt: Natural-language optimization directive.
        base_branch: Branch to clone and compare against.
        max_targets: Maximum number of functions to optimize.
        tests_root: Path to tests within the repo.
        config_name: Named agent config profile.
        publish_pr: Whether to push a branch and open a pull request.
        test_command: Custom test command (e.g. ``"python -m pytest tests"``).
        setup_commands: Commands to run before testing (e.g. ``["pip install -e ."]``).
        backend: ``"local"`` or ``"blaxel"``.

    Returns:
        Repo result with ``selected_target``, ``winner_result``, ``artifacts``, etc.
    """
    from src.core.repo_agent import run_repo_agent_job

    payload: dict[str, Any] = {
        "operation": "run_repo_agent_job",
        "repo_url": repo_url,
        "prompt": prompt,
        "base_branch": base_branch,
        "max_targets": max_targets,
        "tests_root": tests_root,
        "publish_pr": publish_pr,
        "backend_config": {"backend": backend},
    }
    if config_name:
        payload["config_name"] = config_name
    if test_command:
        payload["test_command"] = test_command
    if setup_commands:
        payload["setup_commands"] = setup_commands
    return run_repo_agent_job(normalize_request_defaults(payload))  # type: ignore[return-value]


def discover_targets(
    source_root: str,
    *,
    tests_root: str = "tests",
    limit: int = 10,
) -> list[RankedTarget]:
    """
    Discover and rank optimization targets in a directory. No server required.

    Args:
        source_root: Path to a Python source directory.
        tests_root: Path to tests relative to source_root.
        limit: Maximum number of ranked targets to return.

    Returns:
        Ranked list of optimization candidates.
    """
    payload: dict[str, Any] = {
        "operation": "discover_and_rank_directory",
        "source_root": source_root,
        "tests_root": tests_root,
        "limit": limit,
    }
    result = _run_worker(payload)
    if isinstance(result, list):
        return result  # type: ignore[return-value]
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(str(result["error"]))
    return result.get("ranked", [])  # type: ignore[return-value]


def rank_targets(
    file_path: str,
    *,
    tests_root: str = "tests",
    limit: int = 10,
) -> list[RankedTarget]:
    """
    Rank optimization targets within a single file. No server required.

    Args:
        file_path: Path to a Python source file.
        tests_root: Path to tests.
        limit: Maximum number of ranked targets to return.

    Returns:
        Ranked list of optimization candidates.
    """
    from pathlib import Path

    resolved = str(Path(file_path).expanduser().resolve())
    payload: dict[str, Any] = {
        "operation": "discover_and_rank_file",
        "file_path": resolved,
        "tests_root": tests_root,
        "limit": limit,
    }
    result = _run_worker(payload)
    if isinstance(result, list):
        return result  # type: ignore[return-value]
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(str(result["error"]))
    return result.get("ranked", [])  # type: ignore[return-value]
