"""
Repo workspace execution helpers for local and Blaxel-backed validation.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.core.worker_runner import run_local_worker_request

_RINGTAIL_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_WORKER_MAX_ATTEMPTS = 3


def detect_repo_bootstrap(
    repo_path: str,
    explicit_setup_commands: list[str] | None = None,
    explicit_test_command: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_path)
    setup_commands = list(explicit_setup_commands or [])
    strategy: list[str] = []
    pkg_manager = _detect_package_manager(root)

    if len(setup_commands) == 0:
        setup_commands, strategy = _build_auto_setup(root, pkg_manager)
    else:
        strategy.append("explicit")

    test_command = str(explicit_test_command or "").strip()
    if test_command != "":
        strategy.append("explicit-test-command")

    venv_python = _find_venv_python(root, pkg_manager)

    return {
        "setup_commands": setup_commands,
        "test_command": test_command,
        "strategy": strategy,
        "pkg_manager": pkg_manager,
        "venv_python": venv_python,
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
    last_worker: dict[str, Any] | None = None
    for attempt in range(_LOCAL_WORKER_MAX_ATTEMPTS):
        worker = run_local_worker_request(request)
        last_worker = worker
        result = worker.get("result")
        if isinstance(result, dict):
            if int(worker.get("returncode", -1)) != 0:
                raise RuntimeError(str(result.get("error", str(worker.get("stderr", "")).strip() or "worker request failed")))
            return result
        # Jac worker startup can intermittently fail without emitting JSON when many
        # subprocesses are spawned; retry before surfacing a hard error.
        if attempt + 1 < _LOCAL_WORKER_MAX_ATTEMPTS:
            continue

    raise RuntimeError(_local_worker_json_error(last_worker))


def _normalize_local_command(command: str) -> str:
    stripped = command.strip()
    if stripped.startswith("python "):
        return sys.executable + stripped[len("python") :]
    if stripped == "python":
        return sys.executable
    return command


def _local_worker_json_error(worker: dict[str, Any] | None) -> str:
    if not isinstance(worker, dict):
        return "Worker did not produce JSON output"
    returncode = int(worker.get("returncode", -1))
    stderr = str(worker.get("stderr", "")).strip()
    stdout = str(worker.get("stdout", "")).strip()
    details: list[str] = [f"Worker did not produce JSON output (returncode={returncode})"]
    if stderr:
        details.append("stderr: " + _truncate_for_error(stderr))
    elif stdout:
        details.append("stdout: " + _truncate_for_error(stdout))
    return " | ".join(details)


def _truncate_for_error(text: str, limit: int = 400) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "...(truncated)"


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


def _detect_package_manager(root: Path) -> str:
    """Detect which package manager a Python project uses based on lock/config files."""
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "Pipfile.lock").exists() or (root / "Pipfile").exists():
        return "pipenv"
    return "pip"


def _resolve_tool(tool: str) -> str:
    """Return the full path to a CLI tool, installing it via pip if needed."""
    found = shutil.which(tool)
    if found:
        return found
    # Tools like uv/poetry install their binary next to the Python executable
    bin_dir = os.path.dirname(sys.executable)
    candidate = os.path.join(bin_dir, tool)
    if os.path.isfile(candidate):
        return candidate
    # Not found anywhere — install it
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", tool],
        capture_output=True, check=True, text=True,
    )
    if os.path.isfile(candidate):
        return candidate
    found = shutil.which(tool)
    if found:
        return found
    raise RuntimeError(
        f"Installed {tool} via pip but cannot find the binary. "
        f"Checked PATH and {bin_dir}"
    )


def _build_auto_setup(root: Path, pkg_manager: str) -> tuple[list[str], list[str]]:
    """Build setup commands based on detected package manager."""
    commands: list[str] = []
    strategy: list[str] = []

    if pkg_manager == "uv":
        uv = _resolve_tool("uv")
        commands.append(f"{uv} sync")
        strategy.append("uv")
    elif pkg_manager == "poetry":
        poetry = _resolve_tool("poetry")
        commands.append(f"{poetry} install --no-interaction")
        strategy.append("poetry")
    elif pkg_manager == "pipenv":
        pipenv = _resolve_tool("pipenv")
        commands.append(f"{pipenv} install --dev")
        strategy.append("pipenv")
    else:
        venv_dir = root / ".venv"
        if not venv_dir.exists():
            commands.append(f"{sys.executable} -m venv .venv")
            strategy.append("venv-create")

        pip = ".venv/bin/pip"
        if (root / "requirements-dev.txt").exists():
            commands.append(f"{pip} install -r requirements-dev.txt")
            strategy.append("requirements-dev")
        if (root / "requirements.txt").exists():
            commands.append(f"{pip} install -r requirements.txt")
            strategy.append("requirements")
        elif (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            commands.append(f"{pip} install -e .")
            strategy.append("editable-install")

    return commands, strategy


def _find_venv_python(root: Path, pkg_manager: str) -> str:
    """Return the path to the venv python for this repo, or empty string."""
    # uv, poetry, pipenv all create .venv by default in modern versions
    for venv_dir in (".venv", "venv"):
        candidate = root / venv_dir / "bin" / "python"
        if candidate.exists():
            return str(candidate)

    # After setup commands run, the venv will exist at .venv
    if pkg_manager in ("uv", "pip"):
        return str(root / ".venv" / "bin" / "python")
    if pkg_manager == "poetry":
        return str(root / ".venv" / "bin" / "python")

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
        try:
            files[str(path.relative_to(root))] = path.read_text()
        except (UnicodeDecodeError, ValueError):
            pass
    return files
