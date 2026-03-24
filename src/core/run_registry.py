"""
Run registry helpers for querying latest runs across workflows.
"""
from __future__ import annotations

import datetime as dt
import json
import base64
from pathlib import Path
from typing import Any

from src.core import async_jobs
from src.utils.run_log import LOGS_DIR

_RUN_INDEX = Path(LOGS_DIR) / "runs.jsonl"
_ARTIFACTS_DIR = Path(LOGS_DIR) / "artifacts"


def get_latest_run(kind: str = "any") -> dict[str, Any]:
    normalized_kind = _normalize_kind(kind)
    entries = list_recent_runs(limit=200, kind=normalized_kind)
    if not entries:
        return {
            "success": False,
            "kind": normalized_kind,
            "error": f"No runs found for kind '{normalized_kind}'",
        }
    return {
        "success": True,
        "kind": normalized_kind,
        "latest": entries[0],
    }


def list_recent_runs(limit: int = 20, kind: str = "any") -> list[dict[str, Any]]:
    normalized_kind = _normalize_kind(kind)
    merged: list[dict[str, Any]] = []
    merged.extend(_load_index_runs())
    merged.extend(_load_async_jobs_runs())
    if normalized_kind != "any":
        merged = [entry for entry in merged if str(entry.get("kind", "any")) == normalized_kind]
    merged.sort(key=lambda entry: float(entry.get("_sort_ts", 0.0)), reverse=True)
    trimmed = merged[: max(0, int(limit))]
    for entry in trimmed:
        entry.pop("_sort_ts", None)
    return trimmed


def _load_index_runs() -> list[dict[str, Any]]:
    if not _RUN_INDEX.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in _RUN_INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        run_id = str(row.get("run_id", "")).strip()
        finished = str(row.get("finished", "")).strip()
        kind = _kind_from_run_id(run_id)
        entry: dict[str, Any] = {
            "source": "run_log_index",
            "kind": kind,
            "run_id": run_id,
            "run_log_path": str(row.get("log_path", "")),
            "status": "succeeded",
            "finished_at": finished,
            "elapsed_s": float(row.get("elapsed_s", 0.0) or 0.0),
            "events": int(row.get("events", 0) or 0),
            "_sort_ts": _parse_iso_timestamp(finished),
        }
        artifact = _load_artifact_summary(run_id)
        if artifact:
            entry.update(artifact)
        out.append(entry)
    return out


def _load_async_jobs_runs() -> list[dict[str, Any]]:
    jobs = async_jobs.list_jobs(200)
    out: list[dict[str, Any]] = []
    for job in jobs:
        request_summary = job.get("request_summary", {})
        operation = str(request_summary.get("operation", "")).strip()
        kind = _kind_from_operation(operation)
        submitted = str(job.get("submitted_at", "")).strip()
        finished = str(job.get("finished_at", "")).strip()
        sort_ts = _parse_iso_timestamp(finished) or _parse_iso_timestamp(submitted)
        out.append(
            {
                "source": "async_jobs",
                "kind": kind,
                "job_id": str(job.get("job_id", "")),
                "run_id": str(job.get("run_id", "")),
                "status": str(job.get("status", "")),
                "submitted_at": submitted,
                "finished_at": finished,
                "run_log_path": str(job.get("run_log_path", "")),
                "operation": operation,
                "error": str(job.get("error", "")),
                "_sort_ts": sort_ts,
            }
        )
    return out


def _kind_from_operation(operation: str) -> str:
    if operation == "run_repo_agent_job":
        return "repo_agent"
    if operation in {"optimize_replay_function", "optimize_best_replay_function", "optimize_best_replay_in_repo"}:
        return "replay_optimize"
    if operation == "run_ranked_demo_suite":
        return "ranked_demo_suite"
    if operation in {"optimize_file_function", "optimize_input"}:
        return "file_optimize"
    return "async_job"


def _kind_from_run_id(run_id: str) -> str:
    value = str(run_id).strip()
    if value.startswith("async_job_"):
        return "async_job"
    if value.startswith("repo_agent_"):
        return "repo_agent"
    if value.startswith("optimize-"):
        return "file_optimize"
    if "demo" in value:
        return "ranked_demo_suite"
    return "run"


def _parse_iso_timestamp(raw: str) -> float:
    text = str(raw).strip()
    if not text:
        return 0.0
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _normalize_kind(kind: str) -> str:
    normalized = str(kind or "any").strip()
    if normalized == "":
        return "any"
    allowed = {
        "any",
        "run",
        "async_job",
        "file_optimize",
        "replay_optimize",
        "repo_agent",
        "ranked_demo_suite",
    }
    return normalized if normalized in allowed else "any"


def _load_artifact_summary(run_id: str) -> dict[str, Any]:
    rid = str(run_id).strip()
    if rid == "":
        return {}
    path = _ARTIFACTS_DIR / f"{rid}_summary.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {
        "summary_json_path": str(payload.get("summary_json_path", str(path))),
        "timing_graph_path": str(payload.get("timing_graph_path", "")),
        "timing_graph_svg_base64": _read_file_base64(str(payload.get("timing_graph_path", ""))),
        "title": str(payload.get("title", "")),
        "function_name": str(payload.get("function_name", "")),
        "file_path": str(payload.get("file_path", "")),
    }
    for key in (
        "improvement_ratio",
        "time_saved_pct",
        "baseline_time_ms",
        "optimized_time_ms",
        "confidence",
        "is_significant",
    ):
        if key in payload:
            out[key] = payload.get(key)
    return out


def _read_file_base64(raw_path: str) -> str:
    text = str(raw_path).strip()
    if text == "":
        return ""
    path = Path(text).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return ""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
