#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.reporting import create_optimization_artifacts

CSV_FIELDS = [
    "rank",
    "name",
    "status",
    "file_path",
    "function_name",
    "function_call",
    "median_ms_ranked",
    "termination_reason",
    "improvement_ratio",
    "baseline_time_ms",
    "optimized_time_ms",
    "time_saved_pct",
    "timing_graph_path",
    "summary_json_path",
    "optimized_code_path",
    "run_log_path",
    "error",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a ranking-first local Ringtail file suite")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--source-root",
        default=str(REPO_ROOT / "benchmarks" / "ranked_pitch_repo"),
        help="Directory to rank and optimize",
    )
    parser.add_argument(
        "--tests-root",
        default=str(REPO_ROOT / "benchmarks" / "ranked_pitch_repo" / "tests"),
        help="Tests directory used for ranking signals",
    )
    parser.add_argument("--top-k", type=int, default=3, help="How many ranked targets to optimize")
    parser.add_argument("--per-file-k", type=int, default=1, help="How many top functions to keep from each file before global rerank")
    parser.add_argument("--config-name", default="live-fast")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    source_root = str(Path(args.source_root).expanduser().resolve())
    tests_root = str(Path(args.tests_root).expanduser().resolve())
    suite_name = "pitch-ranked-file-suite"
    output_dir = _resolve_output_dir(args.output_dir, suite_name)
    run_label = output_dir.name
    optimized_dir = output_dir / "optimized_code"
    optimized_dir.mkdir(parents=True, exist_ok=True)

    _probe_server(args.server_url)
    full_ranked = _discover_ranked_targets(args.server_url, source_root, tests_root, 100)
    if not full_ranked:
        raise RuntimeError("Ranking returned no targets")
    per_file_finalists = _pick_per_file_finalists(full_ranked, int(args.per_file_k))
    ranked = _rerank_finalists(per_file_finalists, int(args.top_k))

    rows: list[dict[str, Any]] = []
    for idx, entry in enumerate(ranked, start=1):
        name = f"{Path(str(entry.get('source_file', ''))).stem}::{entry.get('function_name', '')}"
        print(f"[{idx}/{len(ranked)}] rank={idx} {name}", flush=True)
        row = _run_target(
            entry,
            rank=idx,
            suite_name=suite_name,
            run_label=run_label,
            server_url=args.server_url,
            tests_root=tests_root,
            config_name=str(args.config_name),
            optimized_dir=optimized_dir,
        )
        rows.append(row)
        print(
            f"  status={row['status']} ranked_ms={row['median_ms_ranked']:.6f} "
            f"speedup={row['improvement_ratio']:.3f}x graph={row['timing_graph_path']}",
            flush=True,
        )
        if row["status"] != "pass":
            print(f"  error={row['error']}", flush=True)

    summary = _build_summary(suite_name, source_root, rows, output_dir)
    summary_json = output_dir / "suite_summary.json"
    summary_csv = output_dir / "suite_results.csv"
    summary_svg = output_dir / "suite_overview.svg"
    ranking_json = output_dir / "ranking.json"
    per_file_json = output_dir / "per_file_finalists.json"
    final_rank_json = output_dir / "final_ranked_targets.json"
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    summary_svg.write_text(_build_suite_svg(summary))
    ranking_json.write_text(json.dumps(full_ranked, indent=2, sort_keys=True))
    per_file_json.write_text(json.dumps(per_file_finalists, indent=2, sort_keys=True))
    final_rank_json.write_text(json.dumps(ranked, indent=2, sort_keys=True))
    _write_csv(summary_csv, rows)

    print("", flush=True)
    print(f"suite_name: {suite_name}", flush=True)
    print(f"source_root: {source_root}", flush=True)
    print(f"pass_count: {summary['pass_count']}/{summary['target_count']}", flush=True)
    print(f"ranking_json: {ranking_json}", flush=True)
    print(f"per_file_finalists_json: {per_file_json}", flush=True)
    print(f"final_ranked_targets_json: {final_rank_json}", flush=True)
    print(f"summary_json: {summary_json}", flush=True)
    print(f"summary_csv: {summary_csv}", flush=True)
    print(f"suite_overview_graph: {summary_svg}", flush=True)
    print("target_graphs:", flush=True)
    for row in rows:
        print(f"  - #{row['rank']} {row['name']}: {row['timing_graph_path']}", flush=True)

    return 0 if summary["fail_count"] == 0 else 1


def _discover_ranked_targets(server_url: str, source_root: str, tests_root: str, limit: int) -> list[dict[str, Any]]:
    payload = {
        "request": {
            "operation": "discover_and_rank_directory",
            "source_root": source_root,
            "tests_root": tests_root,
            "limit": limit,
        }
    }
    response = _unwrap_function_response(_post_json(server_url, "/function/optimize_sync", payload))
    if not isinstance(response, list):
        raise RuntimeError(f"Expected ranked target list, got: {response}")
    return [dict(item) for item in response]


def _pick_per_file_finalists(entries: list[dict[str, Any]], per_file_k: int) -> list[dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        source_file = str(entry.get("source_file", ""))
        current = by_file.get(source_file, [])
        if len(current) < per_file_k:
            current.append(entry)
            by_file[source_file] = current
    finalists: list[dict[str, Any]] = []
    for source_file in sorted(by_file.keys()):
        finalists.extend(by_file[source_file])
    return finalists


def _rerank_finalists(entries: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    scored = sorted(entries, key=_ranking_score, reverse=True)
    return scored[:top_k]


def _run_target(
    entry: dict[str, Any],
    *,
    rank: int,
    suite_name: str,
    run_label: str,
    server_url: str,
    tests_root: str,
    config_name: str,
    optimized_dir: Path,
) -> dict[str, Any]:
    file_path = str(entry.get("source_file", ""))
    function_name = str(entry.get("function_name", ""))
    function_call = str(entry.get("function_call", ""))
    payload = {
        "request": {
            "operation": "optimize_file_function",
            "file_path": file_path,
            "function_name": function_name,
            "function_call": function_call,
            "tests_root": tests_root,
            "config_name": config_name,
        }
    }
    response = _unwrap_function_response(_post_json(server_url, "/function/optimize_sync", payload))
    artifact_prefix = f"{run_label}_rank{rank}_{Path(file_path).stem}_{function_name}"
    artifacts = create_optimization_artifacts(
        response,
        artifact_prefix=artifact_prefix,
        title=f"Ringtail Ranked Suite: #{rank} {Path(file_path).stem}::{function_name}",
        extra_summary={
            "suite_name": suite_name,
            "rank": rank,
            "file_path": file_path,
            "function_name": function_name,
            "ranked_median_ms": _safe_float(entry.get("median_ms", 0.0)),
        },
    )
    optimized_code_path = optimized_dir / f"{rank:02d}_{_safe_name(Path(file_path).stem)}_{_safe_name(function_name)}.py"
    optimized_code = str(response.get("optimized_code", "")).rstrip()
    if optimized_code:
        optimized_code_path.write_text(optimized_code + "\n")

    return {
        "rank": rank,
        "name": f"{Path(file_path).stem}::{function_name}",
        "status": "pass" if bool(response.get("test_passed", False)) else "fail",
        "file_path": file_path,
        "function_name": function_name,
        "function_call": function_call,
        "median_ms_ranked": _safe_float(entry.get("median_ms", 0.0)),
        "termination_reason": str(response.get("termination_reason", "")),
        "improvement_ratio": _safe_float(response.get("improvement_ratio", 0.0)),
        "baseline_time_ms": _safe_float(artifacts.get("baseline_time_ms", 0.0)),
        "optimized_time_ms": _safe_float(artifacts.get("optimized_time_ms", 0.0)),
        "time_saved_pct": _safe_float(artifacts.get("time_saved_pct", 0.0)),
        "timing_graph_path": str(artifacts.get("timing_graph_path", "")),
        "summary_json_path": str(artifacts.get("summary_json_path", "")),
        "optimized_code_path": str(optimized_code_path) if optimized_code else "",
        "run_log_path": str(response.get("run_log_path", "")),
        "error": str(response.get("error", "")),
    }


def _build_summary(suite_name: str, source_root: str, rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    pass_count = sum(1 for row in rows if row["status"] == "pass")
    return {
        "suite_name": suite_name,
        "source_root": source_root,
        "target_count": len(rows),
        "pass_count": pass_count,
        "fail_count": len(rows) - pass_count,
        "average_speedup": _average(row["improvement_ratio"] for row in rows if row["status"] == "pass"),
        "average_time_saved_pct": _average(row["time_saved_pct"] for row in rows if row["status"] == "pass"),
        "output_dir": str(output_dir),
        "results": rows,
    }


def _ranking_score(entry: dict[str, Any]) -> float:
    runtime_component = _safe_float(entry.get("median_ms", 0.0))
    complexity_component = _safe_float(entry.get("cyclomatic_complexity", 0))
    test_bonus = _safe_float(entry.get("discovered_test_count", 0)) * 100.0
    return runtime_component * 1000.0 + complexity_component + test_bonus


def _resolve_output_dir(raw_output_dir: str, suite_name: str) -> Path:
    if str(raw_output_dir).strip():
        output_dir = Path(raw_output_dir).expanduser().resolve()
    else:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = (REPO_ROOT / "benchmarks" / "ranked_file_suite_runs" / f"{_safe_name(suite_name)}_{stamp}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _probe_server(server_url: str) -> None:
    try:
        with urllib.request.urlopen(server_url.rstrip("/") + "/", timeout=5) as response:
            if getattr(response, "status", 200) >= 400:
                raise RuntimeError(f"Server probe failed with status {response.status}")
    except Exception as exc:
        raise RuntimeError(f"Could not reach local Ringtail server at {server_url}: {exc}") from exc


def _post_json(server_url: str, route: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        server_url.rstrip("/") + route,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _unwrap_function_response(response: dict[str, Any]) -> Any:
    if isinstance(response.get("data"), dict) and "result" in response["data"]:
        return response["data"]["result"]
    return response


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})


def _build_suite_svg(summary: dict[str, Any]) -> str:
    rows = list(summary.get("results", []) or [])
    chart_rows = rows[: min(8, len(rows))]
    width = 920
    height = 150 + (len(chart_rows) * 60)
    max_ms = max([1.0] + [max(_safe_float(row.get("baseline_time_ms")), _safe_float(row.get("optimized_time_ms"))) for row in chart_rows])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Ringtail ranked file suite overview">',
        f'<rect width="{width}" height="{height}" fill="#0f172a" rx="18" />',
        f'<text x="28" y="38" fill="#f8fafc" font-size="22" font-family="Arial, sans-serif" font-weight="700">{_escape_xml(str(summary.get("suite_name", "Ranked File Suite")))}</text>',
        f'<text x="28" y="64" fill="#cbd5e1" font-size="14" font-family="Arial, sans-serif">pass {summary.get("pass_count", 0)}/{summary.get("target_count", 0)} | avg speedup {_safe_float(summary.get("average_speedup", 0.0)):.2f}x</text>',
    ]
    y = 108
    for row in chart_rows:
        label = _escape_xml(f"#{row.get('rank')} {row.get('name')}")
        baseline_ms = _safe_float(row.get("baseline_time_ms", 0.0))
        optimized_ms = _safe_float(row.get("optimized_time_ms", 0.0))
        baseline_width = max(16.0, (baseline_ms / max_ms) * 520.0) if baseline_ms > 0 else 16.0
        optimized_width = max(16.0, (optimized_ms / max_ms) * 520.0) if optimized_ms > 0 else 16.0
        parts.append(f'<text x="28" y="{y}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif" font-weight="600">{label}</text>')
        parts.append(f'<text x="28" y="{y + 18}" fill="#94a3b8" font-size="11" font-family="Arial, sans-serif">ranked {row.get("median_ms_ranked", 0.0):.6f} ms</text>')
        parts.append(f'<rect x="260" y="{y - 14}" width="{baseline_width:.1f}" height="14" fill="#ef4444" rx="6" />')
        parts.append(f'<rect x="260" y="{y + 8}" width="{optimized_width:.1f}" height="14" fill="#22c55e" rx="6" />')
        parts.append(f'<text x="{276 + baseline_width:.1f}" y="{y - 2}" fill="#fecaca" font-size="12" font-family="Arial, sans-serif">{baseline_ms:.10f} ms</text>')
        parts.append(f'<text x="{276 + optimized_width:.1f}" y="{y + 20}" fill="#bbf7d0" font-size="12" font-family="Arial, sans-serif">{optimized_ms:.10f} ms</text>')
        y += 60
    parts.append("</svg>")
    return "\n".join(parts)


def _average(values: Any) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    return sum(items) / len(items)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
