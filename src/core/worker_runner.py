"""
Shared local Jac worker execution helpers.

Both async jobs and repo workspace local execution paths use this module to
avoid drift in subprocess invocation and JSON result extraction behavior.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_WORKER_PATH = _WORKSPACE_ROOT / "src" / "core" / "async_optimize_worker.jac"


def extract_json_result(stdout: str) -> Any | None:
    for raw_line in reversed(stdout.splitlines()):
        line = raw_line.strip()
        if not (line.startswith("{") or line.startswith("[")):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, (dict, list)):
            return data
    return None


def run_local_worker_request(
    request: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
    on_spawned: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """
    Execute async_optimize_worker.jac with a JSON request payload.

    ``on_spawned`` is invoked with the child PID immediately after ``Popen``,
    before ``communicate()`` — so async job cancellation can ``SIGTERM`` the
    process while it is still running. (Previously PID was only known after the
    worker exited, so cancel could not kill the subprocess.)

    Returns a structured dict:
    {
      "returncode": int,
      "stdout": str,
      "stderr": str,
      "result": dict | None,
      "pid": int | None,
      "elapsed_ms": float
    }
    """
    started = time.perf_counter()
    request_file: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="ringtail_worker_",
            suffix=".json",
            delete=False,
        ) as handle:
            json.dump(request, handle)
            request_file = handle.name

        env = os.environ.copy()
        env["RINGTAIL_ASYNC_REQUEST_FILE"] = request_file
        proc = subprocess.Popen(
            ["jac", "run", str(_WORKER_PATH)],
            cwd=str(_WORKSPACE_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if on_spawned is not None:
            try:
                on_spawned(int(proc.pid))
            except Exception:
                pass
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return {
                "returncode": -1,
                "stdout": stdout,
                "stderr": stderr or "Worker timed out",
                "result": extract_json_result(stdout),
                "pid": proc.pid,
                "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            }

        return {
            "returncode": int(proc.returncode),
            "stdout": stdout,
            "stderr": stderr,
            "result": extract_json_result(stdout),
            "pid": proc.pid,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
        }
    finally:
        if request_file and os.path.exists(request_file):
            os.remove(request_file)
