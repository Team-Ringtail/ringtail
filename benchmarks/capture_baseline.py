#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture baseline optimization performance before code changes. "
            "Run this from your own shell (e.g. infisical run -- python benchmarks/capture_baseline.py)."
        )
    )
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--config-name", default="baseline-measure")
    parser.add_argument("--analysis-mode", default="llm")
    parser.add_argument("--llm-model", default="")
    parser.add_argument("--max-targets", type=int, default=1)
    parser.add_argument("--async-timeout", type=float, default=500.0)
    parser.add_argument("--repo-prompt", default="Optimize the slowest function without changing behavior.")
    parser.add_argument(
        "--repo-url",
        default=str(REPO_ROOT / "benchmarks" / "ranked_pitch_repo"),
        help="Repo URL or local repo path for repo-agent baseline case.",
    )
    parser.add_argument(
        "--tests-root",
        default=str(REPO_ROOT / "benchmarks" / "local_file_suite"),
        help="Tests root used by file/replay cases.",
    )
    parser.add_argument(
        "--estimate-input-usd-per-1m-tokens",
        type=float,
        default=0.0,
        help="Optional cost model for prompt/input tokens (USD per 1M tokens).",
    )
    parser.add_argument(
        "--estimate-output-usd-per-1m-tokens",
        type=float,
        default=0.0,
        help="Optional cost model for completion/output tokens (USD per 1M tokens).",
    )
    parser.add_argument(
        "--skip-replay",
        action="store_true",
        help="Skip replay-based case if your environment cannot run replay tracing.",
    )
    args = parser.parse_args()

    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "baseline_raw.jsonl"
    summary_path = output_dir / "baseline_summary.json"
    report_path = output_dir / "baseline_report.md"

    _probe_server(args.server_url)
    replay_fixture = _build_replay_fixture(output_dir)

    cases = _build_cases(args, replay_fixture)
    if args.skip_replay:
        cases = [case for case in cases if case["name"] != "replay_sync_optimize_replay_function"]

    records: list[dict[str, Any]] = []
    for case in cases:
        print(f"case: {case['name']}", flush=True)
        total_runs = args.warmups + args.trials
        for run_idx in range(total_runs):
            measured = run_idx >= args.warmups
            sample = _run_case(
                server_url=args.server_url,
                case=case,
                poll_interval=float(args.poll_interval),
                async_timeout=float(args.async_timeout),
            )
            if measured:
                sample["trial_index"] = run_idx - args.warmups
                records.append(sample)
                print(
                    "  "
                    + f"trial={sample['trial_index']} status={sample['status']} "
                    + f"wall_ms={sample['wall_time_ms']:.2f}",
                    flush=True,
                )
            else:
                print("  warmup complete", flush=True)

    _write_jsonl(raw_path, records)
    summary = _summarize(records, args)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    report_path.write_text(_build_report(summary, args, output_dir))

    print("", flush=True)
    print(f"baseline_raw: {raw_path}", flush=True)
    print(f"baseline_summary: {summary_path}", flush=True)
    print(f"baseline_report: {report_path}", flush=True)
    print("done", flush=True)
    return 0


def _resolve_output_dir(raw_output_dir: str) -> Path:
    if str(raw_output_dir).strip():
        return Path(raw_output_dir).expanduser().resolve()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    return (REPO_ROOT / "benchmarks" / "baselines" / f"baseline_{stamp}").resolve()


def _probe_server(server_url: str) -> None:
    try:
        with urllib.request.urlopen(server_url.rstrip("/") + "/", timeout=8) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise RuntimeError(f"Server probe returned HTTP {status}")
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach Ringtail server at {server_url}. Start it first "
            "(for example via infisical run -- ringtail serve)."
        ) from exc


def _build_replay_fixture(output_dir: Path) -> dict[str, str]:
    fixture_root = output_dir / "_replay_fixture"
    fixture_root.mkdir(parents=True, exist_ok=True)

    source_file = fixture_root / "math_ops.py"
    script_file = fixture_root / "drive_math_ops.py"
    tests_root = fixture_root / "tests"
    tests_root.mkdir(parents=True, exist_ok=True)
    tests_file = tests_root / "test_math_ops.py"

    source_file.write_text(
        "\n".join(
            [
                "def sum_up(nums):",
                "    total = 0",
                "    for value in nums:",
                "        total += value",
                "    return total",
                "",
            ]
        )
    )
    script_file.write_text(
        "\n".join(
            [
                "from math_ops import sum_up",
                "",
                "def main():",
                "    sum_up([1, 2, 3])",
                "    sum_up([10, -5, 2])",
                "    sum_up([])",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        )
    )
    tests_file.write_text(
        "\n".join(
            [
                "from math_ops import sum_up",
                "",
                "def test_sum_up_basic():",
                "    assert sum_up([1, 2, 3]) == 6",
                "",
            ]
        )
    )
    return {
        "source_file": str(source_file),
        "script_file": str(script_file),
        "tests_root": str(tests_root),
    }


def _build_cases(args: argparse.Namespace, replay_fixture: dict[str, str]) -> list[dict[str, Any]]:
    llm_model = str(args.llm_model).strip()
    shared: dict[str, Any] = {
        "config_name": str(args.config_name).strip(),
        "analysis_mode": str(args.analysis_mode).strip(),
        "enable_run_log": True,
    }
    if llm_model:
        shared["llm_model"] = llm_model

    file_fixture = REPO_ROOT / "benchmarks" / "local_file_suite" / "slow_sum.py"

    function_input = {
        "source_code": "\n".join(
            [
                "def slow_add(n):",
                "    total = 0",
                "    for i in range(n):",
                "        total += i",
                "    return total",
                "",
            ]
        ),
        "function_name": "slow_add",
        "function_call": "slow_add(2000)",
        "test_cases": [{"call": "slow_add(5)", "expected": 10}],
    }

    return [
        {
            "name": "function_sync_optimize_input",
            "mode": "sync",
            "request": {
                "operation": "optimize_input",
                "input": function_input,
                **shared,
            },
        },
        {
            "name": "file_sync_optimize_file_function",
            "mode": "sync",
            "request": {
                "operation": "optimize_file_function",
                "file_path": str(file_fixture.resolve()),
                "function_name": "slow_sum",
                "function_call": "slow_sum(10000)",
                "tests_root": str(Path(args.tests_root).expanduser().resolve()),
                **shared,
            },
        },
        {
            "name": "replay_sync_optimize_replay_function",
            "mode": "sync",
            "request": {
                "operation": "optimize_replay_function",
                "file_path": replay_fixture["source_file"],
                "function_name": "sum_up",
                "script_path": replay_fixture["script_file"],
                "tests_root": replay_fixture["tests_root"],
                **shared,
            },
        },
        {
            "name": "repo_sync_run_repo_agent_job",
            "mode": "sync",
            "request": {
                "operation": "run_repo_agent_job",
                "repo_url": str(args.repo_url).strip(),
                "prompt": str(args.repo_prompt).strip(),
                "backend_config": {"backend": "local", "fanout_mode": "threadpool"},
                "base_branch": "main",
                "max_targets": max(1, int(args.max_targets)),
                "publish_pr": False,
                "keep_repo_checkout": False,
                **shared,
            },
        },
        {
            "name": "file_async_submit_optimization_job",
            "mode": "async",
            "request": {
                "operation": "optimize_file_function",
                "file_path": str(file_fixture.resolve()),
                "function_name": "slow_sum",
                "function_call": "slow_sum(10000)",
                "tests_root": str(Path(args.tests_root).expanduser().resolve()),
                **shared,
            },
        },
    ]


def _run_case(
    *,
    server_url: str,
    case: dict[str, Any],
    poll_interval: float,
    async_timeout: float,
) -> dict[str, Any]:
    started_at = time.time()
    job_payload: dict[str, Any] | None = None
    response: dict[str, Any]
    transport_error = ""
    try:
        if case["mode"] == "sync":
            response = _unwrap_response(_post_json(server_url, "/function/optimize_sync", {"request": case["request"]}))
            finished_at = time.time()
        else:
            submitted = _unwrap_response(
                _post_json(server_url, "/function/submit_optimization_job", {"request": case["request"]})
            )
            job_id = str(submitted.get("job_id", ""))
            job_payload = _wait_for_job(
                server_url=server_url,
                job_id=job_id,
                poll_interval=poll_interval,
                timeout_seconds=async_timeout,
            )
            response = dict(job_payload.get("result", {})) if isinstance(job_payload.get("result"), dict) else {}
            finished_at = time.time()
    except Exception as exc:
        # Keep baseline capture progressing even when a single endpoint call fails.
        transport_error = str(exc)
        response = {"error": transport_error}
        finished_at = time.time()

    run_log_path = str(response.get("run_log_path", ""))
    log_stats = _run_log_stats(run_log_path)
    tokens_in = int(log_stats.get("prompt_tokens", 0))
    tokens_out = int(log_stats.get("completion_tokens", 0))

    sample: dict[str, Any] = {
        "case": case["name"],
        "mode": case["mode"],
        "wall_time_ms": (finished_at - started_at) * 1000.0,
        "status": "ok" if not response.get("error") and transport_error == "" else "error",
        "error": transport_error or str(response.get("error", "")),
        "termination_reason": str(response.get("termination_reason", "")),
        "iteration_number": int(response.get("iteration_number", 0) or 0),
        "candidate_count_evaluated": int(response.get("candidate_count_evaluated", 0) or 0),
        "improvement_ratio": float(response.get("improvement_ratio", 0.0) or 0.0),
        "run_id": str(response.get("run_id", "")),
        "run_log_path": run_log_path,
        "llm_calls": int(log_stats.get("llm_calls", 0)),
        "prompt_tokens": tokens_in,
        "completion_tokens": tokens_out,
        "stage_ms": log_stats.get("stage_ms", {}),
        "async_overhead_ms": {},
    }

    if case["mode"] == "async" and job_payload is not None:
        submitted_ts = _parse_iso_timestamp(job_payload.get("submitted_at", ""))
        started_ts = _parse_iso_timestamp(job_payload.get("started_at", ""))
        finished_ts = _parse_iso_timestamp(job_payload.get("finished_at", ""))
        queue_ms = _safe_ms_delta(submitted_ts, started_ts)
        worker_ms = _safe_ms_delta(started_ts, finished_ts)
        total_ms = _safe_ms_delta(submitted_ts, finished_ts)
        sample["async_overhead_ms"] = {
            "queue_ms": queue_ms,
            "worker_runtime_ms": worker_ms,
            "job_total_ms": total_ms,
        }
    return sample


def _run_log_stats(run_log_path: str) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "stage_ms": {
            "plan": None,
            "codegen_total": 0.0,
            "tests_total": 0.0,
            "property_total": 0.0,
            "profile_total": 0.0,
        },
    }
    if not run_log_path:
        return stats

    path = Path(run_log_path)
    if not path.exists():
        return stats

    events: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)

    for event in events:
        if event.get("kind") == "llm_call":
            stats["llm_calls"] += 1
            stats["prompt_tokens"] += int(event.get("prompt_tokens", 0) or 0)
            stats["completion_tokens"] += int(event.get("completion_tokens", 0) or 0)

    # Approximate stage durations using elapsed_s from sequential phase markers.
    # This is intentionally best-effort until explicit stage start/end events exist.
    def first_elapsed(kind: str) -> float | None:
        for event in events:
            if event.get("kind") == kind and isinstance(event.get("elapsed_s"), (int, float)):
                return float(event["elapsed_s"])
        return None

    plan_start = first_elapsed("iteration_start")
    plan_end = first_elapsed("plan_summary")
    if plan_start is not None and plan_end is not None and plan_end >= plan_start:
        stats["stage_ms"]["plan"] = (plan_end - plan_start) * 1000.0

    # Per-candidate stage approximation from ordered events.
    stage_open: dict[str, float] = {}
    for event in events:
        kind = str(event.get("kind", ""))
        elapsed = event.get("elapsed_s", None)
        if not isinstance(elapsed, (int, float)):
            continue
        elapsed = float(elapsed)

        if kind == "codegen_start":
            stage_open["codegen_start"] = elapsed
        elif kind == "tests":
            if "codegen_start" in stage_open and elapsed >= stage_open["codegen_start"]:
                stats["stage_ms"]["codegen_total"] += (elapsed - stage_open["codegen_start"]) * 1000.0
            stage_open["tests"] = elapsed
        elif kind == "property_tests":
            if "tests" in stage_open and elapsed >= stage_open["tests"]:
                stats["stage_ms"]["tests_total"] += (elapsed - stage_open["tests"]) * 1000.0
            stage_open["property_tests"] = elapsed
        elif kind == "profile":
            if "property_tests" in stage_open and elapsed >= stage_open["property_tests"]:
                stats["stage_ms"]["property_total"] += (elapsed - stage_open["property_tests"]) * 1000.0
            elif "tests" in stage_open and elapsed >= stage_open["tests"]:
                stats["stage_ms"]["tests_total"] += (elapsed - stage_open["tests"]) * 1000.0
            stage_open["profile"] = elapsed
        elif kind == "candidate_evaluation":
            if "profile" in stage_open and elapsed >= stage_open["profile"]:
                stats["stage_ms"]["profile_total"] += (elapsed - stage_open["profile"]) * 1000.0
            stage_open = {}

    return stats


def _wait_for_job(
    *,
    server_url: str,
    job_id: str,
    poll_interval: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    latest: dict[str, Any] = {"job_id": job_id, "status": "unknown"}
    while time.time() < deadline:
        latest = _unwrap_response(_post_json(server_url, "/function/get_optimization_job", {"job_id": job_id}))
        status = str(latest.get("status", ""))
        if status in {"succeeded", "failed", "interrupted", "not_found"}:
            return latest
        time.sleep(max(0.1, poll_interval))
    latest["status"] = str(latest.get("status", "timeout"))
    if not latest.get("error"):
        latest["error"] = f"Timed out waiting for async job {job_id}"
    return latest


def _post_json(server_url: str, route: str, payload: dict[str, Any], timeout: float = 300.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        server_url.rstrip("/") + route,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {route}: {detail}") from exc


def _unwrap_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"error": "Unexpected response type"}
    data = payload.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return dict(data["result"])
    return payload


def _parse_iso_timestamp(value: str) -> float | None:
    raw = str(value).strip()
    if raw == "":
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _safe_ms_delta(start_s: float | None, end_s: float | None) -> float | None:
    if start_s is None or end_s is None:
        return None
    if end_s < start_s:
        return None
    return (end_s - start_s) * 1000.0


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return float(ordered[index])


def _sum_numeric(values: list[float | int | None]) -> float:
    total = 0.0
    for value in values:
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def _summarize(records: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_case.setdefault(str(record.get("case", "unknown")), []).append(record)

    case_summaries: dict[str, Any] = {}
    for case_name, rows in by_case.items():
        wall_times = [float(row.get("wall_time_ms", 0.0)) for row in rows]
        mean_ms = statistics.fmean(wall_times) if wall_times else 0.0
        stdev_ms = statistics.pstdev(wall_times) if len(wall_times) > 1 else 0.0
        cv = (stdev_ms / mean_ms) if mean_ms > 0 else 0.0

        prompt_tokens = int(_sum_numeric([row.get("prompt_tokens", 0) for row in rows]))
        completion_tokens = int(_sum_numeric([row.get("completion_tokens", 0) for row in rows]))

        est_cost_usd = (
            (prompt_tokens / 1_000_000.0) * float(args.estimate_input_usd_per_1m_tokens)
            + (completion_tokens / 1_000_000.0) * float(args.estimate_output_usd_per_1m_tokens)
        )

        stage_plan_values = [
            row.get("stage_ms", {}).get("plan")
            for row in rows
            if isinstance(row.get("stage_ms"), dict) and row.get("stage_ms", {}).get("plan") is not None
        ]
        stage_codegen_values = [
            row.get("stage_ms", {}).get("codegen_total", 0.0) for row in rows if isinstance(row.get("stage_ms"), dict)
        ]
        stage_tests_values = [
            row.get("stage_ms", {}).get("tests_total", 0.0) for row in rows if isinstance(row.get("stage_ms"), dict)
        ]
        stage_property_values = [
            row.get("stage_ms", {}).get("property_total", 0.0) for row in rows if isinstance(row.get("stage_ms"), dict)
        ]
        stage_profile_values = [
            row.get("stage_ms", {}).get("profile_total", 0.0) for row in rows if isinstance(row.get("stage_ms"), dict)
        ]

        queue_values = [
            row.get("async_overhead_ms", {}).get("queue_ms")
            for row in rows
            if isinstance(row.get("async_overhead_ms"), dict)
        ]
        worker_values = [
            row.get("async_overhead_ms", {}).get("worker_runtime_ms")
            for row in rows
            if isinstance(row.get("async_overhead_ms"), dict)
        ]

        case_summaries[case_name] = {
            "samples": len(rows),
            "status_counts": {
                "ok": sum(1 for row in rows if str(row.get("status", "")) == "ok"),
                "error": sum(1 for row in rows if str(row.get("status", "")) != "ok"),
            },
            "wall_time_ms": {
                "p50": _quantile(wall_times, 0.50),
                "p95": _quantile(wall_times, 0.95),
                "mean": mean_ms,
                "stdev": stdev_ms,
                "cv": cv,
            },
            "llm_usage": {
                "calls": int(_sum_numeric([row.get("llm_calls", 0) for row in rows])),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "estimated_cost_usd": est_cost_usd,
            },
            "stage_ms": {
                "plan_mean": statistics.fmean(stage_plan_values) if stage_plan_values else None,
                "codegen_total_mean": statistics.fmean(stage_codegen_values) if stage_codegen_values else None,
                "tests_total_mean": statistics.fmean(stage_tests_values) if stage_tests_values else None,
                "property_total_mean": statistics.fmean(stage_property_values) if stage_property_values else None,
                "profile_total_mean": statistics.fmean(stage_profile_values) if stage_profile_values else None,
            },
            "async_overhead_ms": {
                "queue_mean": statistics.fmean([v for v in queue_values if isinstance(v, (int, float))])
                if any(isinstance(v, (int, float)) for v in queue_values)
                else None,
                "worker_runtime_mean": statistics.fmean([v for v in worker_values if isinstance(v, (int, float))])
                if any(isinstance(v, (int, float)) for v in worker_values)
                else None,
            },
            "termination_reasons": sorted(
                {str(row.get("termination_reason", "")) for row in rows if str(row.get("termination_reason", ""))}
            ),
        }

    return {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config": {
            "server_url": str(args.server_url),
            "warmups": int(args.warmups),
            "trials": int(args.trials),
            "config_name": str(args.config_name),
            "analysis_mode": str(args.analysis_mode),
            "llm_model": str(args.llm_model),
            "repo_url": str(args.repo_url),
            "repo_prompt": str(args.repo_prompt),
            "tests_root": str(args.tests_root),
            "estimate_input_usd_per_1m_tokens": float(args.estimate_input_usd_per_1m_tokens),
            "estimate_output_usd_per_1m_tokens": float(args.estimate_output_usd_per_1m_tokens),
        },
        "case_count": len(case_summaries),
        "cases": case_summaries,
        "notes": {
            "stage_timing_method": (
                "Best-effort approximation from run_log elapsed_s phase markers. "
                "For exact stage timing, add explicit start/end events in optimization_loop."
            )
        },
    }


def _build_report(summary: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> str:
    lines = [
        "# Baseline Performance Report",
        "",
        f"- Created: {summary.get('created_at', '')}",
        f"- Output directory: {output_dir}",
        f"- Server URL: {args.server_url}",
        f"- Warmups: {args.warmups}",
        f"- Trials per case: {args.trials}",
        f"- Config: {args.config_name}",
        f"- Analysis mode: {args.analysis_mode}",
        f"- LLM model override: {args.llm_model or '(none)'}",
        f"- Repo target: {args.repo_url}",
        "",
        "## Cases",
    ]
    for case_name in sorted(summary.get("cases", {}).keys()):
        lines.append(f"- {case_name}")
    lines.append("")
    lines.append("## Metrics")
    for case_name in sorted(summary.get("cases", {}).keys()):
        case = summary["cases"][case_name]
        wall = case.get("wall_time_ms", {})
        llm = case.get("llm_usage", {})
        lines.append(
            "- "
            + f"{case_name}: p50={float(wall.get('p50', 0.0)):.2f}ms "
            + f"p95={float(wall.get('p95', 0.0)):.2f}ms "
            + f"cv={float(wall.get('cv', 0.0)):.4f} "
            + f"llm_calls={int(llm.get('calls', 0))} "
            + f"prompt_tokens={int(llm.get('prompt_tokens', 0))} "
            + f"completion_tokens={int(llm.get('completion_tokens', 0))} "
            + f"estimated_cost_usd={float(llm.get('estimated_cost_usd', 0.0)):.6f}"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "- Replay case may fail if replay tracing cannot create cache state in your runtime.",
            "- Stage timings are approximate until explicit stage start/end events exist in run logs.",
            "- Use this report as the locked baseline before implementing optimization/refactor changes.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
