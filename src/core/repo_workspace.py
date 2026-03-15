"""
Repo workspace execution helpers for local and Blaxel-backed validation.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_RINGTAIL_ROOT = Path(__file__).resolve().parents[2]


def detect_repo_bootstrap(
    repo_path: str,
    explicit_setup_commands: list[str] | None = None,
    explicit_test_command: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_path)
    setup_commands = list(explicit_setup_commands or [])
    strategy: list[str] = []

    if len(setup_commands) == 0:
        if (root / "requirements-dev.txt").exists():
            setup_commands.append("python -m pip install -r requirements-dev.txt")
            strategy.append("requirements-dev")
        if (root / "requirements.txt").exists():
            setup_commands.append("python -m pip install -r requirements.txt")
            strategy.append("requirements")
        elif (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            setup_commands.append("python -m pip install -e .")
            strategy.append("editable-install")

    test_command = explicit_test_command or _detect_test_command(root)
    if test_command != "":
        strategy.append("pytest")

    return {
        "setup_commands": setup_commands,
        "test_command": test_command,
        "strategy": strategy,
    }


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


def run_ringtail_worker_request(
    request: dict[str, Any],
    *,
    repo_path: str | None = None,
    backend_config: dict[str, Any] | None = None,
    timeout: int = 180,
) -> Any:
    cfg = backend_config or {}
    backend = str(cfg.get("backend", "local"))
    if backend == "blaxel":
        return _run_ringtail_worker_request_blaxel(request, repo_path=repo_path, config=cfg, timeout=timeout)
    return _run_ringtail_worker_request_local(request)


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


def _run_ringtail_worker_request_local(request: dict[str, Any]) -> Any:
    worker_path = _RINGTAIL_ROOT / "src" / "core" / "async_optimize_worker.jac"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        json.dump(request, handle)
        request_file = handle.name
    try:
        env = os.environ.copy()
        env["RINGTAIL_ASYNC_REQUEST_FILE"] = request_file
        proc = subprocess.run(
            ["jac", "run", str(worker_path)],
            cwd=str(_RINGTAIL_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        result = _extract_json_result(proc.stdout)
        if proc.returncode != 0:
            raise RuntimeError(result.get("error", proc.stderr.strip() or "worker request failed"))
        return result
    finally:
        os.remove(request_file)


def _normalize_local_command(command: str) -> str:
    stripped = command.strip()
    if stripped.startswith("python "):
        return sys.executable + stripped[len("python") :]
    if stripped == "python":
        return sys.executable
    return command


def _extract_json_result(stdout: str) -> Any:
    for raw_line in reversed(stdout.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Worker did not produce JSON output")


def _detect_test_command(root: Path) -> str:
    if (root / "tests").exists():
        return "python -m pytest tests"
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        return "python -m pytest"
    for path in root.rglob("test_*.py"):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        return "python -m pytest"
    return ""


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


def _run_ringtail_worker_request_blaxel(
    request: dict[str, Any],
    *,
    repo_path: str | None,
    config: dict[str, Any],
    timeout: int,
) -> Any:
    try:
        return asyncio.get_event_loop().run_until_complete(
            _run_ringtail_worker_request_blaxel_async(request, repo_path=repo_path, config=config, timeout=timeout)
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _run_ringtail_worker_request_blaxel_async(request, repo_path=repo_path, config=config, timeout=timeout)
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


async def _run_ringtail_worker_request_blaxel_async(
    request: dict[str, Any],
    *,
    repo_path: str | None,
    config: dict[str, Any],
    timeout: int,
) -> Any:
    try:
        from blaxel.core import SandboxInstance
    except ImportError:
        raise RuntimeError("blaxel SDK not installed. Run: pip install blaxel")

    sandbox = None
    ringtail_root = "/workspace/ringtail"
    remote_repo_root = "/workspace/target_repo"
    try:
        create_opts = {
            "name": "ringtail-worker-%s" % os.urandom(4).hex(),
            "image": config.get("image", "sandbox/ringtail-python:yjetxvb6idjq"),
            "memory": config.get("memory_mb", 2048),
        }
        if config.get("region"):
            create_opts["region"] = config["region"]

        sandbox = await SandboxInstance.create(create_opts)

        for rel_path, contents in _read_tree(_RINGTAIL_ROOT).items():
            await sandbox.fs.write(f"{ringtail_root}/{rel_path}", contents)
        if repo_path:
            for rel_path, contents in _read_tree(Path(repo_path)).items():
                await sandbox.fs.write(f"{remote_repo_root}/{rel_path}", contents)

        rewritten_request = _rewrite_request_paths(request, repo_path, remote_repo_root)
        request_json = json.dumps(rewritten_request)
        await sandbox.fs.write(f"{ringtail_root}/tmp_request.json", request_json)

        process = await sandbox.process.exec(
            {
                "command": (
                    f"cd {ringtail_root} && "
                    f"RINGTAIL_ASYNC_REQUEST_FILE={ringtail_root}/tmp_request.json "
                    f"jac run {ringtail_root}/src/core/async_optimize_worker.jac"
                ),
                "working_dir": ringtail_root,
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
        result = _extract_json_result(stdout)
        if returncode != 0:
            raise RuntimeError(result.get("error", stderr or "remote worker request failed"))
        return result
    finally:
        if sandbox is not None:
            try:
                await sandbox.delete()
            except Exception:
                pass


def _rewrite_request_paths(
    request: dict[str, Any],
    repo_path: str | None,
    remote_repo_root: str,
) -> dict[str, Any]:
    rewritten = json.loads(json.dumps(request))
    if not repo_path:
        return rewritten
    local_root = str(Path(repo_path).resolve())
    for key in ("file_path", "script_path", "source_root", "tests_root"):
        value = rewritten.get(key, None)
        if not isinstance(value, str) or value == "":
            continue
        if value == local_root:
            rewritten[key] = remote_repo_root
        elif value.startswith(local_root + os.sep):
            rewritten[key] = remote_repo_root + value[len(local_root):]
    if isinstance(rewritten.get("input"), dict):
        input_data = rewritten["input"]
        extra = input_data.get("extra", {})
        for key in ("source_file", "replay_script"):
            value = extra.get(key, None)
            if isinstance(value, str) and value.startswith(local_root):
                extra[key] = remote_repo_root + value[len(local_root):]
    return rewritten


def _read_repo_tree(repo_path: str) -> dict[str, str]:
    return _read_tree(Path(repo_path))


def _read_tree(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if ".git" in rel_parts or "__pycache__" in rel_parts or ".pytest_cache" in rel_parts:
            continue
        if any(part in {"node_modules", ".venv", "venv", ".jac_gen"} for part in rel_parts):
            continue
        if rel_parts and rel_parts[0] == "logs":
            continue
        files[str(path.relative_to(root))] = path.read_text()
    return files
