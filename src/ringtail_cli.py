from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.core.reporting import create_optimization_artifacts
from src.core.product_support import config_doctor
from src.utils.run_log import LOGS_DIR

_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SERVER = "http://127.0.0.1:8000"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ringtail", description="Local CLI for Ringtail")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Start the local Ringtail web app")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.set_defaults(func=_cmd_serve)

    config_parser = subparsers.add_parser("config", help="Inspect local Ringtail configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    doctor_parser = config_subparsers.add_parser("doctor", help="Run the Ringtail config doctor")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    doctor_parser.set_defaults(func=_cmd_config_doctor)

    repo_parser = subparsers.add_parser("repo", help="Work with repo-agent jobs")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_command", required=True)

    submit_parser = repo_subparsers.add_parser("submit", help="Submit a repo-agent job")
    _add_repo_request_arguments(submit_parser)
    submit_parser.add_argument("--wait", action="store_true")
    submit_parser.add_argument("--verbose", action="store_true")
    submit_parser.add_argument("--poll-interval", type=float, default=5.0)
    submit_parser.add_argument("--json", action="store_true", dest="as_json")
    submit_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    submit_parser.set_defaults(func=_cmd_repo_submit)

    run_parser = repo_subparsers.add_parser("run", help="Run a repo-agent job and wait for completion")
    _add_repo_request_arguments(run_parser)
    run_parser.add_argument("--verbose", action="store_true")
    run_parser.add_argument("--poll-interval", type=float, default=5.0)
    run_parser.add_argument("--json", action="store_true", dest="as_json")
    run_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    run_parser.set_defaults(func=_cmd_repo_run)

    status_parser = repo_subparsers.add_parser("status", help="Poll a repo-agent job")
    status_parser.add_argument("job_id")
    status_parser.add_argument("--watch", action="store_true")
    status_parser.add_argument("--verbose", action="store_true")
    status_parser.add_argument("--poll-interval", type=float, default=5.0)
    status_parser.add_argument("--json", action="store_true", dest="as_json")
    status_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    status_parser.set_defaults(func=_cmd_repo_status)

    watch_parser = repo_subparsers.add_parser("watch", help="Watch a repo-agent job until completion")
    watch_parser.add_argument("job_id")
    watch_parser.add_argument("--verbose", action="store_true")
    watch_parser.add_argument("--poll-interval", type=float, default=5.0)
    watch_parser.add_argument("--json", action="store_true", dest="as_json")
    watch_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    watch_parser.set_defaults(func=_cmd_repo_watch)

    logs_parser = repo_subparsers.add_parser("logs", help="Stream async repo job logs")
    logs_parser.add_argument("job_id")
    logs_parser.add_argument("--poll-interval", type=float, default=2.0)
    logs_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    logs_parser.set_defaults(func=_cmd_repo_logs)

    file_parser = subparsers.add_parser("file", help="Optimize a single function")
    file_subparsers = file_parser.add_subparsers(dest="file_command", required=True)

    optimize_parser = file_subparsers.add_parser("optimize", help="Run function optimization")
    optimize_parser.add_argument("file_path")
    optimize_parser.add_argument("function_name")
    optimize_parser.add_argument("--function-call", default="")
    optimize_parser.add_argument("--tests-root", default="tests")
    optimize_parser.add_argument("--config-name", default="live-fast")
    optimize_parser.add_argument("--json", action="store_true", dest="as_json")
    optimize_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    optimize_parser.set_defaults(func=_cmd_file_optimize)

    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    command = ["jac", "start", "main.jac", "--port", str(args.port)]
    return subprocess.call(command, cwd=str(_WORKSPACE_ROOT))


def _cmd_config_doctor(args: argparse.Namespace) -> int:
    doctor = config_doctor()
    if args.as_json:
        print(json.dumps(doctor, indent=2, sort_keys=True))
    else:
        print(_render_doctor_text(doctor))
    return 0 if doctor.get("ok", False) else 1


def _cmd_repo_submit(args: argparse.Namespace) -> int:
    payload = _build_repo_submit_request(args)
    response = _unwrap_function_response(
        _post_json(args.server_url, _function_route("submit_repo_agent_job"), {"request": payload})
    )
    if args.wait:
        if not args.as_json:
            print(f"submitted repo job {response.get('job_id', '')}")
        return _watch_repo_job(
            args.server_url,
            str(response.get("job_id", "")),
            poll_interval=float(args.poll_interval),
            as_json=bool(args.as_json),
            verbose=bool(args.verbose),
        )
    _print_output(response, as_json=bool(args.as_json), formatter=_format_repo_job_payload)
    return 0


def _cmd_repo_run(args: argparse.Namespace) -> int:
    payload = _build_repo_submit_request(args)
    response = _unwrap_function_response(
        _post_json(args.server_url, _function_route("submit_repo_agent_job"), {"request": payload})
    )
    if not args.as_json:
        print(f"submitted repo job {response.get('job_id', '')}")
    return _watch_repo_job(
        args.server_url,
        str(response.get("job_id", "")),
        poll_interval=float(args.poll_interval),
        as_json=bool(args.as_json),
        verbose=bool(args.verbose),
    )


def _cmd_repo_status(args: argparse.Namespace) -> int:
    if args.watch:
        return _watch_repo_job(
            args.server_url,
            args.job_id,
            poll_interval=float(args.poll_interval),
            as_json=bool(args.as_json),
            verbose=bool(args.verbose),
        )
    response = _fetch_repo_job(args.server_url, args.job_id)
    _print_output(response, as_json=bool(args.as_json), formatter=_format_repo_job_payload)
    return 0 if response.get("status", "") != "failed" else 1


def _cmd_repo_watch(args: argparse.Namespace) -> int:
    return _watch_repo_job(
        args.server_url,
        args.job_id,
        poll_interval=float(args.poll_interval),
        as_json=bool(args.as_json),
        verbose=bool(args.verbose),
    )


def _cmd_repo_logs(args: argparse.Namespace) -> int:
    return _stream_repo_logs(
        args.server_url,
        args.job_id,
        poll_interval=float(args.poll_interval),
    )


def _cmd_file_optimize(args: argparse.Namespace) -> int:
    payload = _build_file_optimize_request(args)
    response = _unwrap_function_response(
        _post_json(args.server_url, _function_route("optimize_sync"), {"request": payload})
    )
    artifacts = create_optimization_artifacts(
        response,
        artifact_prefix=str(response.get("run_id", "")).strip() or "file_optimize",
        title=f"Ringtail Function Timing Comparison: {args.function_name}",
        extra_summary={
            "file_path": args.file_path,
            "function_name": args.function_name,
        },
    )
    if artifacts:
        response["summary_stats"] = artifacts
        response["artifacts"] = {
            "summary_json_path": artifacts.get("summary_json_path", ""),
            "timing_graph_path": artifacts.get("timing_graph_path", ""),
        }
    _print_output(response, as_json=bool(args.as_json), formatter=_format_file_optimize_payload)
    return 0 if response.get("success", True) else 1


def _add_repo_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("repo", help="GitHub URL or local repo path")
    parser.add_argument("prompt", help="Natural-language optimization prompt")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--backend", choices=["local", "blaxel"], default="local")
    parser.add_argument("--config-name", default="")
    parser.add_argument("--publish-pr", action="store_true")
    parser.add_argument("--test-command", default="")
    parser.add_argument("--setup-command", action="append", default=[])
    parser.add_argument("--max-targets", type=int, default=3)


def _build_repo_submit_request(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "repo_url": _normalize_repo_input(args.repo),
        "prompt": args.prompt,
        "base_branch": args.branch,
        "publish_pr": bool(args.publish_pr),
        "max_targets": int(args.max_targets),
        "backend_config": {"backend": args.backend},
    }
    if str(args.config_name).strip():
        payload["config_name"] = str(args.config_name).strip()
    if args.test_command.strip():
        payload["test_command"] = args.test_command.strip()
    if args.setup_command:
        payload["setup_commands"] = [entry.strip() for entry in args.setup_command if entry.strip()]
    return payload


def _build_file_optimize_request(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "operation": "optimize_file_function",
        "file_path": _normalize_existing_path(args.file_path, label="file_path"),
        "function_name": args.function_name,
        "tests_root": _normalize_optional_local_path(args.tests_root),
    }
    if str(args.config_name).strip():
        payload["config_name"] = str(args.config_name).strip()
    if args.function_call.strip():
        payload["function_call"] = args.function_call.strip()
    return payload


def _normalize_repo_input(raw_path: str) -> str:
    stripped = str(raw_path).strip()
    if _looks_like_remote_repo(stripped):
        return stripped
    return str(Path(stripped).expanduser().resolve())


def _normalize_existing_path(raw_path: str, *, label: str) -> str:
    resolved = Path(str(raw_path).strip()).expanduser().resolve()
    if not resolved.exists():
        raise RuntimeError(f"{label} does not exist: {resolved}")
    return str(resolved)


def _normalize_optional_local_path(raw_path: str) -> str:
    stripped = str(raw_path).strip()
    if stripped == "":
        return stripped
    path = Path(stripped).expanduser()
    if path.exists():
        return str(path.resolve())
    return stripped


def _looks_like_remote_repo(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://") or value.startswith("git@") or value.startswith("file://")


def _render_doctor_text(doctor: dict[str, Any]) -> str:
    auth = doctor.get("auth", {})
    issues = doctor.get("issues", [])
    lines = [
        f"overall_ok: {doctor.get('ok', False)}",
        f"jac: {_doctor_check_text(doctor, 'jac')}",
        f"git: {_doctor_check_text(doctor, 'git')}",
        f"openssl: {_doctor_check_text(doctor, 'openssl')}",
        f"repo_agent_config_present: {doctor.get('env', {}).get('repo_agent_config_present', False)}",
        f"anthropic_configured: {doctor.get('env', {}).get('anthropic_configured', False)}",
        f"blaxel_configured: {doctor.get('env', {}).get('blaxel_configured', False)}",
        f"auth_mode: {auth.get('auth_mode', 'none')}",
        f"installation_id: {auth.get('installation_id', None)}",
        f"jobs_dir: {doctor.get('jobs_dir', '')}",
    ]
    if issues:
        lines.append("issues:")
        for issue in issues:
            lines.append(f"- {issue}")
    return "\n".join(lines)


def _doctor_check_text(doctor: dict[str, Any], key: str) -> str:
    check = doctor.get("checks", {}).get(key, {})
    if check.get("available", False):
        return str(check.get("path", ""))
    return "missing"


def _function_route(name: str) -> str:
    return "/function/" + name.lstrip("/")


def _unwrap_function_response(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"raw_response": response}
    data = response.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return response


def _fetch_repo_job(server_url: str, job_id: str) -> dict[str, Any]:
    return _unwrap_function_response(
        _post_json(server_url, _function_route("get_repo_agent_job"), {"job_id": job_id})
    )


def _watch_repo_job(server_url: str, job_id: str, *, poll_interval: float, as_json: bool, verbose: bool) -> int:
    last_status = ""
    positions: dict[str, int] = {}
    announced: set[str] = set()
    waiting_notice_printed = False
    while True:
        response = _fetch_repo_job(server_url, job_id)
        status = str(response.get("status", "unknown"))
        if verbose and not as_json:
            _, waiting_notice_printed = _stream_repo_logs_iteration(
                response,
                positions=positions,
                announced=announced,
                waiting_notice_printed=waiting_notice_printed,
            )
        if status != last_status and not as_json:
            print(f"[{status}] job_id={job_id}")
            if status in {"queued", "running"}:
                summary = response.get("request_summary", {})
                print(
                    f"  repo={summary.get('repo_url', '')} prompt={summary.get('prompt', '')} max_targets={summary.get('max_targets', '')}"
                )
        last_status = status
        if status in {"succeeded", "failed", "interrupted", "not_found"}:
            _print_output(response, as_json=as_json, formatter=_format_repo_job_payload)
            return 0 if status == "succeeded" else 1
        time.sleep(max(0.5, poll_interval))


def _stream_repo_logs(server_url: str, job_id: str, *, poll_interval: float) -> int:
    positions: dict[str, int] = {}
    announced: set[str] = set()
    terminal_quiet_cycles = 0
    waiting_notice_printed = False
    while True:
        response = _fetch_repo_job(server_url, job_id)
        status = str(response.get("status", "unknown"))
        progress, waiting_notice_printed = _stream_repo_logs_iteration(
            response,
            positions=positions,
            announced=announced,
            waiting_notice_printed=waiting_notice_printed,
        )
        if status in {"succeeded", "failed", "interrupted", "not_found"}:
            if not progress:
                terminal_quiet_cycles += 1
            else:
                terminal_quiet_cycles = 0
            if terminal_quiet_cycles >= 2:
                _emit("")
                _emit(_format_repo_job_payload(response))
                return 0 if status == "succeeded" else 1
        time.sleep(max(0.5, poll_interval))


def _stream_repo_logs_iteration(
    response: dict[str, Any],
    *,
    positions: dict[str, int],
    announced: set[str],
    waiting_notice_printed: bool,
) -> tuple[bool, bool]:
    status = str(response.get("status", "unknown"))
    log_paths = _collect_repo_log_paths(response)
    if status in {"queued", "running"}:
        for path in _discover_recent_run_logs(response):
            _append_log_path(log_paths, path)
    progress = False
    for raw_path in log_paths:
        path = str(Path(raw_path).resolve())
        if path not in announced:
            _emit(f"==> {path} <==")
            announced.add(path)
        if not os.path.exists(path):
            continue
        progress = _drain_log_file(path, positions) or progress
    if not progress and not waiting_notice_printed and status in {"queued", "running"}:
        _emit("(waiting for run logs to appear...)")
        waiting_notice_printed = True
    if progress:
        waiting_notice_printed = False
    return progress, waiting_notice_printed


def _print_output(payload: dict[str, Any], *, as_json: bool, formatter: Any) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(formatter(payload))


def _format_repo_job_payload(payload: dict[str, Any]) -> str:
    if payload.get("status", "") in {"queued", "running"}:
        summary = payload.get("request_summary", {})
        return "\n".join(
            [
                f"status: {payload.get('status', '')}",
                f"job_id: {payload.get('job_id', '')}",
                f"repo: {summary.get('repo_url', '')}",
                f"prompt: {summary.get('prompt', '')}",
                f"run_log: {payload.get('run_log_path', '')}",
            ]
        )
    if payload.get("status", "") == "succeeded" and isinstance(payload.get("result"), dict):
        return _format_repo_success(payload["result"], job_id=str(payload.get("job_id", "")))
    if payload.get("status", "") in {"failed", "interrupted"}:
        return "\n".join(
            [
                f"status: {payload.get('status', '')}",
                f"job_id: {payload.get('job_id', '')}",
                f"error: {payload.get('error', '')}",
                f"run_log: {payload.get('run_log_path', '')}",
            ]
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def _format_repo_success(result: dict[str, Any], *, job_id: str = "") -> str:
    summary = result.get("summary_stats", {})
    lines = [
        "status: succeeded",
    ]
    if job_id:
        lines.append(f"job_id: {job_id}")
    lines.extend(
        [
            f"repo: {result.get('repo_url', '')}",
            f"selected_target: {result.get('selected_target', {}).get('source_file', '')}::{result.get('selected_target', {}).get('function_name', '')}",
            f"candidate_count: {result.get('candidate_count', 0)}",
            f"evaluated_candidate_count: {result.get('evaluated_candidate_count', 0)}",
            f"validation_success: {result.get('validation_result', {}).get('success', False)}",
            f"improvement_ratio: {summary.get('improvement_ratio', result.get('winner_result', {}).get('improvement_ratio', 0.0)):.3f}x",
            f"baseline_time_ms: {summary.get('baseline_time_ms', 0.0):.3f}",
            f"optimized_time_ms: {summary.get('optimized_time_ms', 0.0):.3f}",
            f"time_saved_pct: {summary.get('time_saved_pct', 0.0):.2f}",
            f"timing_graph: {result.get('artifacts', {}).get('timing_graph_path', '')}",
            f"summary_json: {result.get('artifacts', {}).get('summary_json_path', '')}",
            f"run_logs: {', '.join(result.get('artifacts', {}).get('run_log_paths', []))}",
        ]
    )
    pr = result.get("pull_request", {})
    if pr.get("published", False):
        lines.append(f"pull_request: {pr.get('url', '')}")
    elif pr.get("preview_only", False):
        lines.append("pull_request: preview_only")
    return "\n".join(lines)


def _format_file_optimize_payload(payload: dict[str, Any]) -> str:
    summary = payload.get("summary_stats", {})
    error_text = str(payload.get("error", ""))
    failure_feedback = payload.get("failure_feedback", {})
    lines = [
        f"test_passed: {payload.get('test_passed', False)}",
        f"termination_reason: {payload.get('termination_reason', '')}",
        f"improvement_ratio: {payload.get('improvement_ratio', 0.0):.3f}x",
        f"baseline_time_ms: {summary.get('baseline_time_ms', 0.0):.3f}",
        f"optimized_time_ms: {summary.get('optimized_time_ms', 0.0):.3f}",
        f"time_saved_pct: {summary.get('time_saved_pct', 0.0):.2f}",
        f"timing_graph: {payload.get('artifacts', {}).get('timing_graph_path', '')}",
        f"summary_json: {payload.get('artifacts', {}).get('summary_json_path', '')}",
        f"run_log: {payload.get('run_log_path', '')}",
    ]
    if error_text:
        lines.append(f"error: {error_text}")
    if "No optimizer backend configured" in error_text:
        lines.append("hint: restart `ringtail serve` so the server picks up new config profiles")
    if isinstance(failure_feedback, dict) and failure_feedback:
        feedback_type = str(failure_feedback.get("type", "")).strip()
        candidate_label = str(
            payload.get("candidate_label", "") or failure_feedback.get("candidate_label", "")
        ).strip()
        falsifying_example = str(failure_feedback.get("falsifying_example", "")).strip()
        failures = failure_feedback.get("failures", [])
        if feedback_type:
            lines.append(f"failure_type: {feedback_type}")
        if candidate_label:
            lines.append(f"failed_candidate: {candidate_label}")
        if falsifying_example:
            lines.append("falsifying_example:")
            lines.extend(_indent_block(falsifying_example))
        if isinstance(failures, list) and failures:
            lines.append("failure_details:")
            shown = 0
            for failure in failures:
                if not isinstance(failure, dict):
                    continue
                detail = str(failure.get("message", "") or failure.get("test", "")).strip()
                if detail:
                    lines.extend(_indent_block(detail))
                    shown += 1
                extra_example = str(failure.get("falsifying_example", "")).strip()
                if extra_example and extra_example != falsifying_example:
                    lines.extend(_indent_block(extra_example))
                    shown += 1
                if shown >= 3:
                    break
        candidate_output = str(
            payload.get("optimized_code", "") or failure_feedback.get("previous_code", "")
        ).rstrip()
        if candidate_output:
            lines.append("candidate_output:")
            lines.extend(_indent_block(candidate_output))
    return "\n".join(lines)


def _indent_block(text: str, prefix: str = "  ") -> list[str]:
    return [prefix + line for line in str(text).splitlines()]


def _collect_repo_log_paths(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    _append_log_path(paths, payload.get("run_log_path", ""))
    result = payload.get("result", {})
    if isinstance(result, dict):
        _append_log_path(paths, result.get("run_log_path", ""))
        artifacts = result.get("artifacts", {})
        if isinstance(artifacts, dict):
            for path in artifacts.get("run_log_paths", []) or []:
                _append_log_path(paths, path)
        for item in result.get("candidate_summaries", []) or []:
            if isinstance(item, dict):
                _append_log_path(paths, item.get("run_log_path", ""))
        for item in result.get("child_jobs", []) or []:
            if isinstance(item, dict):
                _append_log_path(paths, item.get("run_log_path", ""))
    return paths


def _append_log_path(paths: list[str], value: Any) -> None:
    path = str(value or "").strip()
    if path and path not in paths:
        paths.append(path)


def _discover_recent_run_logs(payload: dict[str, Any]) -> list[str]:
    cutoff = _job_start_epoch(payload)
    log_dir = Path(LOGS_DIR)
    if not log_dir.exists():
        return []
    discovered: list[str] = []
    for path in sorted(log_dir.glob("*.jsonl"), key=lambda item: item.stat().st_mtime):
        name = path.name
        if name == "runs.jsonl":
            continue
        if name.startswith("async_job_") and not name.startswith("async_job_repo_agent_"):
            continue
        if path.stat().st_mtime + 1.0 < cutoff:
            continue
        discovered.append(str(path))
    return discovered


def _job_start_epoch(payload: dict[str, Any]) -> float:
    for key in ("started_at", "submitted_at"):
        raw = str(payload.get(key, "")).strip()
        if raw:
            try:
                return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
    return time.time()


def _drain_log_file(path: str, positions: dict[str, int]) -> bool:
    last_pos = positions.get(path, 0)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        handle.seek(last_pos)
        chunk = handle.readlines()
        positions[path] = handle.tell()
    for line in chunk:
        text = line.rstrip("\n")
        if not text:
            continue
        _emit(_format_log_line(path, text))
    return len(chunk) > 0


def _format_log_line(path: str, text: str) -> str:
    prefix = "[" + Path(path).name + "]"
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return f"{prefix} {text}"
    if not isinstance(event, dict):
        return f"{prefix} {text}"
    kind = str(event.get("kind", "event"))
    elapsed = event.get("elapsed_s", None)
    elapsed_text = f"{float(elapsed):6.2f}s" if isinstance(elapsed, (int, float)) else "   ??.??s"
    details = _format_log_event_details(event)
    return f"{prefix} {elapsed_text} {kind}: {details}".rstrip()


def _format_log_event_details(event: dict[str, Any]) -> str:
    kind = str(event.get("kind", ""))
    if kind == "run_start":
        return f"run_name={event.get('run_name', '')}"
    if kind == "run_metadata":
        return (
            f"function={event.get('function_name', '')} "
            f"config={event.get('config_name', '')} "
            f"analysis_mode={event.get('analysis_mode', None)}"
        )
    if kind == "llm_call":
        return (
            f"phase={event.get('phase', '')} "
            f"model={event.get('model', '')} "
            f"in={event.get('prompt_tokens', 0)} "
            f"out={event.get('completion_tokens', 0)}"
        )
    if kind == "plan_summary":
        return (
            f"backend={event.get('backend', '')} "
            f"steps={event.get('step_count', 0)} "
            f"candidates={event.get('candidate_count', 0)} "
            f"analysis={event.get('analysis_excerpt', '')}"
        )
    if kind == "candidate_plan":
        return (
            f"iteration={event.get('iteration', '')} "
            f"candidate={event.get('candidate_label', '')} "
            f"steps={event.get('steps', [])}"
        )
    if kind == "codegen_start":
        return (
            f"iteration={event.get('iteration', '')} "
            f"candidate={event.get('candidate_label', '')} "
            f"backend={event.get('backend', '')}"
        )
    if kind == "baseline_metrics":
        return (
            f"median_ms={event.get('median_ms', 0.0):.6f} "
            f"peak_memory_kb={event.get('peak_memory_kb', 0.0)}"
        )
    if kind in {"iteration_start", "candidate_selected"}:
        return " ".join(
            [
                f"iteration={event.get('iteration', '')}",
                f"candidate={event.get('candidate_label', '')}",
                f"improvement_ratio={event.get('improvement_ratio', '')}",
            ]
        ).strip()
    if kind in {"tests", "property_tests", "profile", "candidate_evaluation", "optimization_step"}:
        keys = [
            "iteration",
            "candidate_label",
            "passed",
            "success",
            "improvement_ratio",
            "coverage_percent",
            "is_significant",
            "confidence",
            "agent_reason",
            "error",
        ]
        parts = [f"{key}={event.get(key)}" for key in keys if key in event and event.get(key) not in ("", None)]
        return " ".join(parts)
    if kind == "error":
        return str(event.get("message", ""))
    if kind == "run_end":
        return f"events={event.get('total_events', '')}"
    parts = [
        f"{key}={value}"
        for key, value in event.items()
        if key not in {"ts", "elapsed_s", "seq", "kind"} and value not in ("", None)
    ]
    return " ".join(parts)


def _emit(text: str) -> None:
    print(text, flush=True)


def _post_json(server_url: str, route: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        server_url.rstrip("/") + route,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ringtail server returned HTTP {exc.code} for {route}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach local Ringtail server at {server_url}. Run `ringtail serve` first."
        ) from exc

if __name__ == "__main__":
    raise SystemExit(main())
