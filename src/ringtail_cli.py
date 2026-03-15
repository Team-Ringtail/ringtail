from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.core.product_support import config_doctor

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
    submit_parser.add_argument("repo", help="GitHub URL or local repo path")
    submit_parser.add_argument("prompt", help="Natural-language optimization prompt")
    submit_parser.add_argument("--branch", default="main")
    submit_parser.add_argument("--backend", choices=["local", "blaxel"], default="local")
    submit_parser.add_argument("--publish-pr", action="store_true")
    submit_parser.add_argument("--test-command", default="")
    submit_parser.add_argument("--setup-command", action="append", default=[])
    submit_parser.add_argument("--max-targets", type=int, default=3)
    submit_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    submit_parser.set_defaults(func=_cmd_repo_submit)

    status_parser = repo_subparsers.add_parser("status", help="Poll a repo-agent job")
    status_parser.add_argument("job_id")
    status_parser.add_argument("--server-url", default=_DEFAULT_SERVER)
    status_parser.set_defaults(func=_cmd_repo_status)

    file_parser = subparsers.add_parser("file", help="Optimize a single function")
    file_subparsers = file_parser.add_subparsers(dest="file_command", required=True)

    optimize_parser = file_subparsers.add_parser("optimize", help="Run function optimization")
    optimize_parser.add_argument("file_path")
    optimize_parser.add_argument("function_name")
    optimize_parser.add_argument("--function-call", default="")
    optimize_parser.add_argument("--tests-root", default="tests")
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
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


def _cmd_repo_status(args: argparse.Namespace) -> int:
    response = _unwrap_function_response(
        _post_json(args.server_url, _function_route("get_repo_agent_job"), {"job_id": args.job_id})
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0 if response.get("status", "") != "failed" else 1


def _cmd_file_optimize(args: argparse.Namespace) -> int:
    payload = _build_file_optimize_request(args)
    response = _unwrap_function_response(
        _post_json(args.server_url, _function_route("optimize_sync"), {"request": payload})
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0 if response.get("success", True) else 1


def _build_repo_submit_request(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "repo_url": args.repo,
        "prompt": args.prompt,
        "base_branch": args.branch,
        "publish_pr": bool(args.publish_pr),
        "max_targets": int(args.max_targets),
        "backend_config": {"backend": args.backend},
    }
    if args.test_command.strip():
        payload["test_command"] = args.test_command.strip()
    if args.setup_command:
        payload["setup_commands"] = [entry.strip() for entry in args.setup_command if entry.strip()]
    return payload


def _build_file_optimize_request(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "operation": "optimize_file_function",
        "file_path": args.file_path,
        "function_name": args.function_name,
        "tests_root": args.tests_root,
    }
    if args.function_call.strip():
        payload["function_call"] = args.function_call.strip()
    return payload


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
