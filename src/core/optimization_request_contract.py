"""
Canonical request/response contract helpers for optimization operations.

This module is intentionally pure-Python so both CLI and worker orchestration
paths can share one operation map and defaults.
"""
from __future__ import annotations

from typing import Any

DEFAULT_OPERATION = "optimize_input"
DEFAULT_CONFIG_NAME = "live-fast"
DEFAULT_ANALYSIS_MODE = "llm"
DEFAULT_ENABLE_RUN_LOG = True

# Ordered operation names (single source of truth for payload/docs).
OPTIMIZATION_OPERATION_SEQUENCE: tuple[str, ...] = (
    "optimize_input",
    "optimize_file_function",
    "optimize_replay_function",
    "optimize_best_replay_function",
    "optimize_best_replay_in_repo",
    "run_repo_agent_job",
)
DISCOVERY_OPERATION_SEQUENCE: tuple[str, ...] = (
    "discover_and_rank_directory",
    "discover_and_rank_replay_repo",
    "get_ranked_demo_suite_catalog",
    "get_ranked_demo_benchmarks",
    "get_latest_ranked_demo_suite",
    "get_ranked_demo_job_progress",
    "run_ranked_demo_suite",
)

# Set views for membership checks.
OPTIMIZATION_OPERATIONS: set[str] = set(OPTIMIZATION_OPERATION_SEQUENCE)
DISCOVERY_OPERATIONS: set[str] = set(DISCOVERY_OPERATION_SEQUENCE)

ALL_OPERATIONS: set[str] = OPTIMIZATION_OPERATIONS | DISCOVERY_OPERATIONS


def normalize_operation_name(raw_operation: Any) -> str:
    operation = str(raw_operation or "").strip()
    if operation == "":
        return DEFAULT_OPERATION
    return operation


def is_optimization_operation(operation: str) -> bool:
    return operation in OPTIMIZATION_OPERATIONS


def normalize_request_defaults(request: dict[str, Any]) -> dict[str, Any]:
    """
    Return a normalized copy of the request with canonical defaults applied.

    Defaults are only applied for optimization operations to avoid mutating
    read-only discovery endpoints with unrelated fields.
    """
    normalized = dict[str, Any](request)
    operation = normalize_operation_name(normalized.get("operation"))
    normalized["operation"] = operation
    if is_optimization_operation(operation):
        normalized.setdefault("config_name", DEFAULT_CONFIG_NAME)
        normalized.setdefault("analysis_mode", DEFAULT_ANALYSIS_MODE)
        normalized.setdefault("enable_run_log", DEFAULT_ENABLE_RUN_LOG)
    return normalized


def get_contract_payload() -> dict[str, Any]:
    """Return a stable, JSON-friendly view of the optimization contract."""
    return {
        "defaults": {
            "operation": DEFAULT_OPERATION,
            "config_name": DEFAULT_CONFIG_NAME,
            "analysis_mode": DEFAULT_ANALYSIS_MODE,
            "enable_run_log": DEFAULT_ENABLE_RUN_LOG,
        },
        # Keep explicit order for display/docs consistency.
        "optimization_operations": list(OPTIMIZATION_OPERATION_SEQUENCE),
        "discovery_operations": list(DISCOVERY_OPERATION_SEQUENCE),
    }
