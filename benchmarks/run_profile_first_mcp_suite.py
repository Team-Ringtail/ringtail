from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from src.mcp import server


_PYTEST_TARGETS = [
    "tests/unit/test_mcp_server.py",
    "tests/unit/test_cprofile_analyzer.py",
    "tests/unit/test_repo_agent_reporting.py",
    "tests/unit/test_async_job_result_status.py",
]
_DEFAULT_EXTERNAL_REPO = "https://github.com/pallets/click.git"


def _run_pytest_suite() -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", *_PYTEST_TARGETS]
    completed = subprocess.run(command, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
    return {
        "name": "profile_first_fixture_suite",
        "success": completed.returncode == 0,
        "command": command,
        "stdout_tail": completed.stdout.splitlines()[-40:],
        "stderr_tail": completed.stderr.splitlines()[-40:],
        "returncode": completed.returncode,
    }


def _write_click_workload(repo_dir: Path) -> Path:
    workload = repo_dir / "ringtail_click_workload.py"
    workload.write_text(
        "\n".join(
            [
                "import click",
                "",
                "@click.command()",
                "@click.option('--count', default=1, type=int)",
                "@click.argument('name')",
                "def greet(count: int, name: str) -> tuple[int, str]:",
                "    return count, name",
                "",
                "def main() -> None:",
                "    for _ in range(3000):",
                "        args = ['--count', '3', 'world']",
                "        ctx = greet.make_context('greet', args, resilient_parsing=True)",
                "        greet.parse_args(ctx, list(args))",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return workload


def _clone_external_repo(repo_url: str, ref: str | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp_dir = tempfile.TemporaryDirectory(prefix="ringtail_mcp_external_")
    repo_dir = Path(temp_dir.name) / "repo"
    clone_command = ["git", "clone", "--depth", "1"]
    if ref:
        clone_command.extend(["--branch", ref])
    clone_command.extend([repo_url, str(repo_dir)])
    subprocess.run(clone_command, check=True, capture_output=True, text=True)
    return temp_dir, repo_dir


def _run_external_profile(repo_url: str, ref: str | None = None) -> dict[str, object]:
    if repo_url.rstrip("/") != _DEFAULT_EXTERNAL_REPO:
        raise ValueError(
            "External harness currently supports only the pinned Click workload. "
            "Pass https://github.com/pallets/click.git or extend the harness with another explicit workload."
        )
    temp_dir, repo_dir = _clone_external_repo(repo_url, ref)
    try:
        venv_dir = repo_dir / ".venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        venv_python = venv_dir / "bin" / "python"
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        workload = _write_click_workload(repo_dir)
        payload = json.loads(
            server.profile_repo(
                repo_path=str(repo_dir),
                entry_point=f"python {workload.name}",
                pct_threshold=1.0,
                max_results=5,
                timeout_s=120,
            )
        )
        return {
            "name": "external_click_profile",
            "success": bool(payload.get("success", False)),
            "repo_url": repo_url,
            "ref": ref or "default",
            "result": payload,
        }
    finally:
        temp_dir.cleanup()


def _write_summary(output_path: Path, summary: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the profile-first MCP verification suite.")
    parser.add_argument(
        "--output",
        default="logs/profile_first_mcp_suite_summary.json",
        help="Path for the machine-readable summary output.",
    )
    parser.add_argument(
        "--include-external",
        action="store_true",
        help="Also clone and profile a pinned public repo (currently pallets/click).",
    )
    parser.add_argument(
        "--external-repo-url",
        default=_DEFAULT_EXTERNAL_REPO,
        help="Public repo URL for the external profiling pass.",
    )
    parser.add_argument(
        "--external-ref",
        default="",
        help="Optional branch or tag for the external repo clone.",
    )
    args = parser.parse_args()

    summary: dict[str, object] = {
        "success": True,
        "scenarios": [],
    }
    scenarios: list[dict[str, object]] = [ _run_pytest_suite() ]
    if args.include_external:
        scenarios.append(_run_external_profile(args.external_repo_url, args.external_ref or None))

    summary["scenarios"] = scenarios
    summary["success"] = all(bool(item.get("success", False)) for item in scenarios)
    _write_summary(Path(args.output), summary)
    print(json.dumps(summary, indent=2))
    return 0 if bool(summary["success"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
