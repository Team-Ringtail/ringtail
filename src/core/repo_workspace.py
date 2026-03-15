"""
Repo workspace execution helpers for local and Blaxel-backed validation.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_repo_commands(
    repo_path: str,
    commands: list[str],
    config: dict[str, Any] | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    cfg = config or {}
    backend = cfg.get("backend", "local")
    if not commands:
        return {"success": True, "backend": backend, "commands": [], "stdout": "", "stderr": ""}
    if backend == "blaxel":
        return _run_repo_commands_blaxel(repo_path, commands, cfg, timeout)
    return _run_repo_commands_local(repo_path, commands, timeout)


def _run_repo_commands_local(repo_path: str, commands: list[str], timeout: int) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    last_stdout = ""
    last_stderr = ""
    for command in commands:
        normalized_command = _normalize_local_command(command)
        proc = subprocess.run(
            normalized_command,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        step = {
            "command": normalized_command,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "success": proc.returncode == 0,
        }
        steps.append(step)
        last_stdout = proc.stdout
        last_stderr = proc.stderr
        if proc.returncode != 0:
            return {
                "success": False,
                "backend": "local",
                "commands": steps,
                "stdout": last_stdout,
                "stderr": last_stderr,
            }
    return {
        "success": True,
        "backend": "local",
        "commands": steps,
        "stdout": last_stdout,
        "stderr": last_stderr,
    }


def _normalize_local_command(command: str) -> str:
    stripped = command.strip()
    if stripped.startswith("python "):
        return sys.executable + stripped[len("python") :]
    if stripped == "python":
        return sys.executable
    return command


def _run_repo_commands_blaxel(
    repo_path: str,
    commands: list[str],
    config: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    try:
        return asyncio.get_event_loop().run_until_complete(
            _run_repo_commands_blaxel_async(repo_path, commands, config, timeout)
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _run_repo_commands_blaxel_async(repo_path, commands, config, timeout)
            )
        finally:
            loop.close()


async def _run_repo_commands_blaxel_async(
    repo_path: str,
    commands: list[str],
    config: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    try:
        from blaxel.core import SandboxInstance
    except ImportError:
        return {
            "success": False,
            "backend": "blaxel",
            "commands": [],
            "stdout": "",
            "stderr": "blaxel SDK not installed. Run: pip install blaxel",
        }

    sandbox = None
    workspace_root = "/workspace/repo"
    try:
        create_opts = {
            "name": "ringtail-repo-%s" % os.urandom(4).hex(),
            "image": config.get("image", "sandbox/ringtail-python:yjetxvb6idjq"),
            "memory": config.get("memory_mb", 2048),
        }
        if config.get("region"):
            create_opts["region"] = config["region"]

        sandbox = await SandboxInstance.create(create_opts)
        for rel_path, contents in _read_repo_tree(repo_path).items():
            await sandbox.fs.write(f"{workspace_root}/{rel_path}", contents)

        steps: list[dict[str, Any]] = []
        last_stdout = ""
        last_stderr = ""
        for command in commands:
            process = await sandbox.process.exec(
                {
                    "command": f"cd {workspace_root} && {command}",
                    "working_dir": workspace_root,
                    "wait_for_completion": True,
                    "timeout": timeout * 1000,
                }
            )
            stdout = getattr(process, "stdout", "") or ""
            stderr = getattr(process, "stderr", "") or ""
            logs_obj = getattr(process, "logs", None)
            if logs_obj:
                stdout = getattr(logs_obj, "stdout", stdout) or stdout
                stderr = getattr(logs_obj, "stderr", stderr) or stderr
            returncode = getattr(process, "exit_code", None)
            if returncode is None:
                returncode = getattr(process, "exitCode", -1)
            step = {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "success": returncode == 0,
            }
            steps.append(step)
            last_stdout = stdout
            last_stderr = stderr
            if returncode != 0:
                return {
                    "success": False,
                    "backend": "blaxel",
                    "commands": steps,
                    "stdout": last_stdout,
                    "stderr": last_stderr,
                }

        return {
            "success": True,
            "backend": "blaxel",
            "commands": steps,
            "stdout": last_stdout,
            "stderr": last_stderr,
        }
    except Exception as exc:
        return {
            "success": False,
            "backend": "blaxel",
            "commands": [],
            "stdout": "",
            "stderr": str(exc),
        }


def _read_repo_tree(repo_path: str) -> dict[str, str]:
    files: dict[str, str] = {}
    root = Path(repo_path)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if ".git" in rel_parts or "__pycache__" in rel_parts or ".pytest_cache" in rel_parts:
            continue
        if any(part in {"node_modules", ".venv", "venv"} for part in rel_parts):
            continue
        files[str(path.relative_to(root))] = path.read_text()
    return files
