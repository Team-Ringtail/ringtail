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
    """Latest run across index + async jobs (for browse / legacy callers)."""
    normalized_kind = _normalize_kind(kind)
    merged: list[dict[str, Any]] = []
    merged.extend(_load_index_runs())
    merged.extend(_load_async_jobs_runs())
    if normalized_kind != "any":
        merged = [entry for entry in merged if str(entry.get("kind", "any")) == normalized_kind]
    merged.sort(
        key=lambda entry: (
            -float(entry.get("_sort_ts", 0.0)),
            str(entry.get("job_id", entry.get("run_id", ""))),
        )
    )
    if not merged:
        return {
            "success": False,
            "kind": normalized_kind,
            "error": f"No runs found for kind '{normalized_kind}'",
        }
    top = merged[0]
    top.pop("_sort_ts", None)
    return {
        "success": True,
        "kind": normalized_kind,
        "latest": top,
    }


def _outcome_bucket(status: str) -> str:
    s = str(status or "").strip().lower()
    if s == "succeeded":
        return "success"
    if s == "failed":
        return "failure"
    return "other"


def _normalize_surface(surface: str) -> str:
    s = str(surface or "any").strip().lower()
    if s in {"paste", "repo_local", "repo_github", "any"}:
        return s
    return "any"


def _normalize_outcome(outcome: str) -> str:
    o = str(outcome or "any").strip().lower()
    if o in {"success", "failure", "other", "any"}:
        return o
    return "any"


def list_recent_runs(
    limit: int = 20,
    kind: str = "any",
    surface: str = "any",
    outcome: str = "any",
) -> list[dict[str, Any]]:
    """List recent async jobs only; jobs without submission_channel + ui_surface are omitted."""
    normalized_kind = _normalize_kind(kind)
    normalized_surface = _normalize_surface(surface)
    normalized_outcome = _normalize_outcome(outcome)
    merged = _load_async_jobs_runs()
    if normalized_kind != "any":
        merged = [entry for entry in merged if str(entry.get("kind", "any")) == normalized_kind]
    if normalized_surface != "any":
        merged = [entry for entry in merged if str(entry.get("ui_surface", "")) == normalized_surface]
    if normalized_outcome != "any":
        merged = [entry for entry in merged if str(entry.get("outcome_bucket", "")) == normalized_outcome]
    merged.sort(
        key=lambda entry: (
            -float(entry.get("_sort_ts", 0.0)),
            str(entry.get("job_id", "")),
        )
    )
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
    jobs = async_jobs.list_jobs(500)
    out: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        request_summary = job.get("request_summary", {}) if isinstance(job.get("request_summary"), dict) else {}
        ch = str(job.get("submission_channel", "") or request_summary.get("submission_channel", "") or "").strip()
        surf = str(job.get("ui_surface", "") or request_summary.get("ui_surface", "") or "").strip()
        if not ch or not surf:
            continue
        operation = str(request_summary.get("operation", "")).strip()
        kind = _kind_from_operation(operation)
        submitted = str(job.get("submitted_at", "")).strip()
        finished = str(job.get("finished_at", "")).strip()
        status = str(job.get("status", "")).strip()
        sort_ts = _parse_iso_timestamp(finished) or _parse_iso_timestamp(submitted)
        out.append(
            {
                "source": "async_jobs",
                "kind": kind,
                "job_id": str(job.get("job_id", "")),
                "run_id": str(job.get("run_id", "")),
                "status": status,
                "submitted_at": submitted,
                "finished_at": finished,
                "run_log_path": str(job.get("run_log_path", "")),
                "operation": operation,
                "error": str(job.get("error", "")),
                "submission_channel": ch,
                "ui_surface": surf,
                "surface_bucket": surf,
                "outcome_bucket": _outcome_bucket(status),
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


def _find_job_id_for_run_id(run_id: str) -> str:
    rid = str(run_id).strip()
    if not rid:
        return ""
    for job in async_jobs.list_jobs(300):
        if str(job.get("run_id", "")).strip() == rid:
            jid = str(job.get("job_id", "")).strip()
            if jid:
                return jid
    return ""


def _coerce_suite_dict(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict) and ("summary" in raw or "suite_overview_svg_base64" in raw):
        return raw
    return None


def _percent_saved_timings(before: float, after: float) -> float:
    if before <= 0.0:
        return 0.0
    return ((before - after) / before) * 100.0


def _peel_optimizer_result(res: dict[str, Any]) -> dict[str, Any]:
    cur: Any = res
    for _ in range(5):
        if not isinstance(cur, dict):
            break
        if "improvement_ratio" in cur or "optimized_code" in cur:
            return cur
        nxt = cur.get("result")
        if isinstance(nxt, dict):
            cur = nxt
            continue
        break
    return cur if isinstance(cur, dict) else {}


def _run_display_meta(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": str(entry.get("kind", "")),
        "job_id": str(entry.get("job_id", "")),
        "run_id": str(entry.get("run_id", "")),
        "status": str(entry.get("status", "")),
        "operation": str(entry.get("operation", "")),
        "source": str(entry.get("source", "")),
        "submission_channel": str(entry.get("submission_channel", "")),
        "ui_surface": str(entry.get("ui_surface", "")),
        "finished_at": str(entry.get("finished_at", "")),
        "submitted_at": str(entry.get("submitted_at", "")),
        "registry_error": str(entry.get("error", "")),
    }


def _run_display_empty(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant": "empty",
        "meta": meta,
        "overview_svg_base64": "",
        "pass_count": 0,
        "target_count": 0,
        "average_speedup": 0.0,
        "average_time_saved_pct": 0.0,
        "results": [],
        "final_ranked_targets": [],
        "per_file_finalists": [],
    }


def _normalize_suite_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows_in = summary.get("results")
    if not isinstance(rows_in, list):
        return []
    rows_out: list[dict[str, Any]] = []
    for row in rows_in[:12]:
        if not isinstance(row, dict):
            continue
        rows_out.append(
            {
                "name": str(row.get("name", "")),
                "improvement_ratio": float(row.get("improvement_ratio", 0.0) or 0.0),
                "time_saved_pct": float(row.get("time_saved_pct", 0.0) or 0.0),
                "median_ms_ranked": float(row.get("median_ms_ranked", 0.0) or 0.0),
                "graph_svg_base64": str(row.get("graph_svg_base64", "")),
                "original_code": str(row.get("original_code", "")),
                "optimized_code": str(row.get("optimized_code", "")),
            }
        )
    return rows_out


def _normalize_target_rows(targets: Any) -> list[dict[str, Any]]:
    if not isinstance(targets, list):
        return []
    out: list[dict[str, Any]] = []
    for t in targets[:4]:
        if not isinstance(t, dict):
            continue
        out.append(
            {
                "function_name": str(t.get("function_name", "")),
                "source_file": str(t.get("source_file", "")),
                "median_ms": float(t.get("median_ms", 0.0) or 0.0),
            }
        )
    return out


def _run_display_from_suite(suite: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    summary = suite.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "variant": "suite",
        "meta": meta,
        "overview_svg_base64": str(suite.get("suite_overview_svg_base64", "")),
        "pass_count": int(summary.get("pass_count", 0) or 0),
        "target_count": int(summary.get("target_count", 0) or 0),
        "average_speedup": float(summary.get("average_speedup", 0.0) or 0.0),
        "average_time_saved_pct": float(summary.get("average_time_saved_pct", 0.0) or 0.0),
        "results": _normalize_suite_rows(summary),
        "final_ranked_targets": _normalize_target_rows(suite.get("final_ranked_targets")),
        "per_file_finalists": _normalize_target_rows(suite.get("per_file_finalists")),
    }


def _run_display_from_index_artifact(entry: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    fn = str(entry.get("function_name", "")).strip()
    label = fn or str(entry.get("run_id", "run")).strip() or "run"
    speedup = float(entry.get("improvement_ratio", 0.0) or 0.0)
    saved = float(entry.get("time_saved_pct", 0.0) or 0.0)
    ranked_ms = float(entry.get("optimized_time_ms", 0.0) or 0.0)
    graph = str(entry.get("timing_graph_svg_base64", ""))
    if not fn and not graph and speedup == 0.0 and ranked_ms == 0.0:
        return _run_display_empty(meta)
    row = {
        "name": label,
        "improvement_ratio": speedup,
        "time_saved_pct": saved,
        "median_ms_ranked": ranked_ms,
        "graph_svg_base64": graph,
        "original_code": "",
        "optimized_code": "",
    }
    return {
        "variant": "single",
        "meta": meta,
        "overview_svg_base64": graph,
        "pass_count": 1,
        "target_count": 1,
        "average_speedup": speedup,
        "average_time_saved_pct": saved,
        "results": [row],
        "final_ranked_targets": [
            {
                "function_name": label,
                "source_file": str(entry.get("file_path", "")),
                "median_ms": ranked_ms,
            }
        ],
        "per_file_finalists": [],
    }


def _run_display_from_single_result(res: dict[str, Any], meta: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    inner = _peel_optimizer_result(res)
    if not inner:
        return _run_display_from_index_artifact(entry, meta)
    name = str(
        inner.get("function_name", "")
        or entry.get("function_name", "")
        or meta.get("run_id", "target")
    )
    speedup = float(inner.get("improvement_ratio", 0.0) or 0.0)
    saved = float(inner.get("time_saved_pct", 0.0) or 0.0)
    after = inner.get("metrics", {})
    before = inner.get("baseline_metrics", {})
    if not isinstance(after, dict):
        after = {}
    if not isinstance(before, dict):
        before = {}
    median_after = float(after.get("execution_time", after.get("median_ms", 0.0)) or 0.0) if isinstance(after, dict) else 0.0
    median_before = (
        float(before.get("execution_time", before.get("median_ms", 0.0)) or 0.0) if isinstance(before, dict) else 0.0
    )
    if saved == 0.0 and median_before > 0.0:
        saved = _percent_saved_timings(median_before, median_after)
    row = {
        "name": name,
        "improvement_ratio": speedup,
        "time_saved_pct": saved,
        "median_ms_ranked": median_after or median_before,
        "graph_svg_base64": str(inner.get("timing_graph_svg_base64", "") or ""),
        "original_code": str(inner.get("original_source_code", "")),
        "optimized_code": str(inner.get("optimized_code", "")),
    }
    if not row["original_code"] and not row["optimized_code"] and speedup == 0.0:
        return _run_display_from_index_artifact(entry, meta)
    return {
        "variant": "single",
        "meta": meta,
        "overview_svg_base64": row["graph_svg_base64"],
        "pass_count": 1,
        "target_count": 1,
        "average_speedup": speedup,
        "average_time_saved_pct": saved,
        "results": [row],
        "final_ranked_targets": [
            {
                "function_name": name,
                "source_file": str(entry.get("file_path", "")),
                "median_ms": float(row["median_ms_ranked"] or 0.0),
            }
        ],
        "per_file_finalists": [],
    }


def hydrate_run_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Build activity log lines + a run_display payload for the Run history UI tab.
    """
    if not isinstance(entry, dict):
        return {"success": False, "error": "entry must be an object", "activity_log_lines": [], "run_display": {}}

    meta = _run_display_meta(entry)
    log_path = str(entry.get("run_log_path", "")).strip()
    activity: list[str] = [
        "[run]"
        + f" surface={meta.get('ui_surface', '')} channel={meta.get('submission_channel', '')}"
        + f" kind={meta['kind']} run_id={meta['run_id']} job_id={meta['job_id']}"
        + f" status={meta['status']} op={meta['operation']}"
    ]
    if meta.get("registry_error"):
        activity.append(f"[run] registry_error={meta['registry_error']}")

    kind = str(entry.get("kind", "run")).strip() or "run"
    job_id = str(entry.get("job_id", "")).strip()
    run_id = str(entry.get("run_id", "")).strip()
    if not job_id and run_id:
        job_id = _find_job_id_for_run_id(run_id)

    run_display: dict[str, Any] = _run_display_empty(meta)

    if kind == "ranked_demo_suite" and job_id:
        from src.core.ranked_demo_suite import get_demo_job_progress, load_demo_suite_result

        prog = get_demo_job_progress(job_id)
        log_lines = prog.get("log_lines")
        if isinstance(log_lines, list):
            for ln in log_lines[-40:]:
                activity.append(str(ln))

        suite: dict[str, Any] | None = _coerce_suite_dict(prog.get("result"))
        if suite is None:
            res = prog.get("result")
            if isinstance(res, dict) and res.get("output_dir"):
                try:
                    suite = load_demo_suite_result(str(res["output_dir"]))
                except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError):
                    suite = None
        if suite is None and prog.get("output_dir"):
            try:
                suite = load_demo_suite_result(str(prog["output_dir"]))
            except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError):
                suite = None
        if suite is not None:
            run_display = _run_display_from_suite(suite, meta)
        else:
            run_display = _run_display_from_index_artifact(entry, meta)
    elif job_id:
        job = async_jobs.get_job(job_id)
        res = job.get("result") if isinstance(job.get("result"), dict) else {}
        suite_candidate = _coerce_suite_dict(res)
        if suite_candidate is not None:
            run_display = _run_display_from_suite(suite_candidate, meta)
        elif res:
            run_display = _run_display_from_single_result(res, meta, entry)
        if run_display.get("variant") == "empty":
            run_display = _run_display_from_index_artifact(entry, meta)
    else:
        run_display = _run_display_from_index_artifact(entry, meta)

    tail = async_jobs.tail_run_log_activity(log_path, max_lines=120)
    if tail:
        activity.append("--- run log (tail) ---")
        activity.extend(tail)

    return {"success": True, "error": "", "activity_log_lines": activity, "run_display": run_display}
