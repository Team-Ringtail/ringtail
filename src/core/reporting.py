"""
Pitch-friendly reporting artifacts for optimization runs.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from src.utils.run_log import LOGS_DIR

ARTIFACTS_DIR = Path(LOGS_DIR) / "artifacts"


def create_optimization_artifacts(
    result: dict[str, Any],
    *,
    artifact_prefix: str | None = None,
    title: str = "Ringtail Timing Comparison",
    extra_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = _safe_float((result.get("baseline_metrics", {}) or {}).get("execution_time"))
    optimized = _safe_float((result.get("metrics", {}) or {}).get("execution_time"))
    if baseline <= 0.0 or optimized <= 0.0:
        return {}

    prefix = artifact_prefix or str(result.get("run_id", "")).strip() or f"ringtail_{int(time.time())}"
    prefix = _sanitize_prefix(prefix)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"{prefix}_summary.json"
    graph_path = ARTIFACTS_DIR / f"{prefix}_timing.svg"

    summary = {
        "run_id": result.get("run_id", ""),
        "run_log_path": result.get("run_log_path", ""),
        "title": title,
        "baseline_time_s": baseline,
        "optimized_time_s": optimized,
        "baseline_time_ms": baseline * 1000.0,
        "optimized_time_ms": optimized * 1000.0,
        "improvement_ratio": _safe_float(result.get("improvement_ratio", 0.0)),
        "time_saved_pct": _percent_saved(baseline, optimized),
        "is_significant": bool(result.get("is_significant", False)),
        "confidence": _safe_float(result.get("confidence", 0.0)),
    }
    if extra_summary:
        summary.update(extra_summary)

    summary["timing_graph_path"] = str(graph_path)
    summary["summary_json_path"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    graph_path.write_text(_build_timing_svg(summary))
    return summary


def create_repo_job_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    winner = dict(result.get("winner_result", {}) or {})
    candidate_summaries = list(result.get("candidate_summaries", []) or [])
    summary = create_optimization_artifacts(
        winner,
        artifact_prefix=str(winner.get("run_id", "")).strip() or None,
        title="Ringtail Repo Winner Timing Comparison",
        extra_summary={
            "repo_url": result.get("repo_url", ""),
            "prompt": result.get("prompt", ""),
            "selected_function": result.get("selected_target", {}).get("function_name", ""),
            "selected_source_file": result.get("selected_target", {}).get("source_file", ""),
            "candidate_count": int(result.get("candidate_count", 0)),
            "evaluated_candidate_count": int(result.get("evaluated_candidate_count", 0)),
            "successful_candidate_count": sum(1 for item in candidate_summaries if bool(item.get("success", False))),
            "significant_candidate_count": sum(1 for item in candidate_summaries if bool(item.get("is_significant", False))),
            "validation_success": bool(result.get("validation_result", {}).get("success", False)),
            "pull_request_published": bool(result.get("pull_request", {}).get("published", False)),
            "pull_request_url": result.get("pull_request", {}).get("url", ""),
        },
    )
    if not summary:
        return {}
    summary["top_candidates"] = candidate_summaries[: min(5, len(candidate_summaries))]
    summary_path = Path(summary["summary_json_path"])
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _build_timing_svg(summary: dict[str, Any]) -> str:
    baseline_ms = _safe_float(summary.get("baseline_time_ms", 0.0))
    optimized_ms = _safe_float(summary.get("optimized_time_ms", 0.0))
    max_ms = max(baseline_ms, optimized_ms, 1.0)
    chart_width = 520.0
    baseline_width = max(16.0, (baseline_ms / max_ms) * chart_width)
    optimized_width = max(16.0, (optimized_ms / max_ms) * chart_width)
    title = _escape_xml(str(summary.get("title", "Timing Comparison")))
    subtitle = _escape_xml(
        f"speedup {summary.get('improvement_ratio', 0.0):.2f}x  |  time saved {summary.get('time_saved_pct', 0.0):.1f}%"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="260" viewBox="0 0 760 260" role="img" aria-label="{title}">
  <rect width="760" height="260" fill="#0f172a" rx="18" />
  <text x="28" y="38" fill="#f8fafc" font-size="22" font-family="Arial, sans-serif" font-weight="700">{title}</text>
  <text x="28" y="64" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">{subtitle}</text>
  <text x="28" y="112" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif" font-weight="600">Baseline</text>
  <rect x="140" y="92" width="{baseline_width:.1f}" height="28" fill="#ef4444" rx="8" />
  <text x="{156 + baseline_width:.1f}" y="111" fill="#fecaca" font-size="14" font-family="Arial, sans-serif">{baseline_ms:.10f} ms</text>
  <text x="28" y="170" fill="#e2e8f0" font-size="16" font-family="Arial, sans-serif" font-weight="600">Optimized</text>
  <rect x="140" y="150" width="{optimized_width:.1f}" height="28" fill="#22c55e" rx="8" />
  <text x="{156 + optimized_width:.1f}" y="169" fill="#bbf7d0" font-size="14" font-family="Arial, sans-serif">{optimized_ms:.10f} ms</text>
  <text x="28" y="226" fill="#94a3b8" font-size="13" font-family="Arial, sans-serif">Generated by Ringtail from recorded baseline and optimized execution timings.</text>
</svg>
"""


def _percent_saved(baseline_s: float, optimized_s: float) -> float:
    if baseline_s <= 0.0:
        return 0.0
    return ((baseline_s - optimized_s) / baseline_s) * 100.0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sanitize_prefix(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
