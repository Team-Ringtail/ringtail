"""
Minimal async optimization job manager.

Jobs are tracked in memory and executed in background threads. Each worker
invokes the existing Jac optimization request path through a small Jac worker
script, then stores the terminal result for polling clients.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from src.utils.run_log import LOGS_DIR

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_WORKER_PATH = _WORKSPACE_ROOT / "src" / "core" / "async_optimize_worker.jac"
_JOBS_DIR = Path(os.environ.get("RINGTAIL_ASYNC_JOBS_DIR", Path(LOGS_DIR) / "async_jobs"))
_TERMINAL_STATES = {"succeeded", "failed", "interrupted"}


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log_path_for_run_id(run_id: str) -> str:
    return str(Path(LOGS_DIR) / f"{run_id}.jsonl")


def _ensure_jobs_dir() -> None:
    _JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _job_path(job_id: str) -> Path:
    return _JOBS_DIR / f"{job_id}.json"


def _request_summary(request: dict[str, Any]) -> dict[str, Any]:
    input_data = request.get("input", {}) if isinstance(request.get("input"), dict) else {}
    return {
        "operation": request.get("operation", "optimize_input"),
        "config_name": request.get("config_name"),
        "criteria_name": request.get("criteria_name"),
        "analysis_mode": request.get("analysis_mode"),
        "function_name": request.get("function_name") or input_data.get("function_name"),
        "file_path": request.get("file_path"),
        "script_path": request.get("script_path"),
        "source_root": request.get("source_root"),
        "repo_url": request.get("repo_url"),
        "prompt": request.get("prompt"),
        "max_targets": request.get("max_targets"),
        "installation_id": request.get("installation_id")
        or (request.get("auth", {}) if isinstance(request.get("auth"), dict) else {}).get("installation_id"),
    }


def _extract_result(stdout: str) -> dict[str, Any] | None:
    for raw_line in reversed(stdout.splitlines()):
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


class AsyncJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        _ensure_jobs_dir()
        self._load_persisted_jobs()

    def submit_job(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be a dict")

        job_id = request.get("job_id") or uuid.uuid4().hex
        run_id = request.get("run_id") or f"async_job_{job_id}"
        run_name = request.get("run_name") or run_id
        payload = dict(request)
        payload.setdefault("operation", "optimize_input")
        payload["job_id"] = job_id
        payload["run_id"] = run_id
        payload["run_name"] = run_name
        payload.setdefault("enable_run_log", True)

        job = {
            "job_id": job_id,
            "status": "queued",
            "submitted_at": _utc_timestamp(),
            "started_at": None,
            "finished_at": None,
            "run_id": run_id,
            "run_name": run_name,
            "run_log_path": _log_path_for_run_id(run_id),
            "request_summary": _request_summary(payload),
            "error": "",
            "result": None,
            "pid": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._persist_job(job)

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, payload),
            daemon=True,
            name=f"ringtail-async-job-{job_id[:8]}",
        )
        thread.start()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                persisted = self._read_persisted_job(job_id)
                if persisted is not None:
                    self._jobs[job_id] = persisted
                    return copy.deepcopy(persisted)
                return {
                    "job_id": job_id,
                    "status": "not_found",
                    "error": f"Unknown job_id: {job_id}",
                }
            return copy.deepcopy(job)

    def _update_job(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.update(changes)
            self._persist_job(job)

    def _run_job(self, job_id: str, request: dict[str, Any]) -> None:
        request_file: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                prefix=f"ringtail_async_{job_id}_",
                suffix=".json",
                delete=False,
            ) as handle:
                json.dump(request, handle)
                request_file = handle.name

            env = os.environ.copy()
            env["RINGTAIL_ASYNC_REQUEST_FILE"] = request_file
            self._update_job(job_id, status="running", started_at=_utc_timestamp())
            proc = subprocess.Popen(
                ["jac", "run", str(_WORKER_PATH)],
                cwd=str(_WORKSPACE_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._update_job(job_id, pid=proc.pid)
            stdout, stderr = proc.communicate()
            result = _extract_result(stdout)

            if proc.returncode == 0 and result is not None:
                self._update_job(
                    job_id,
                    status="succeeded",
                    finished_at=_utc_timestamp(),
                    result=result,
                    error="",
                    pid=None,
                    run_id=result.get("run_id", request.get("run_id")),
                    run_log_path=result.get("run_log_path", _log_path_for_run_id(request["run_id"])),
                )
                return

            error_message = stderr.strip() or "Async worker failed"
            if result is not None and result.get("error"):
                error_message = str(result.get("error"))
            self._update_job(
                job_id,
                status="failed",
                finished_at=_utc_timestamp(),
                result=result,
                error=error_message,
                pid=None,
            )
        except Exception as exc:  # pragma: no cover - defensive bridge path
            self._update_job(
                job_id,
                status="failed",
                finished_at=_utc_timestamp(),
                error=str(exc),
                pid=None,
            )
        finally:
            if request_file and os.path.exists(request_file):
                os.remove(request_file)

    def _persist_job(self, job: dict[str, Any]) -> None:
        path = _job_path(str(job["job_id"]))
        path.write_text(json.dumps(job, sort_keys=True))

    def _read_persisted_job(self, job_id: str) -> dict[str, Any] | None:
        path = _job_path(job_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            return data
        return None

    def _load_persisted_jobs(self) -> None:
        for path in _JOBS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            status = str(data.get("status", ""))
            if status not in _TERMINAL_STATES:
                data["status"] = "interrupted"
                data["finished_at"] = _utc_timestamp()
                previous_error = str(data.get("error", "")).strip()
                data["error"] = (
                    previous_error + "; process restarted before job completed"
                    if previous_error
                    else "Process restarted before job completed"
                )
                data["pid"] = None
                path.write_text(json.dumps(data, sort_keys=True))
            self._jobs[str(data.get("job_id", path.stem))] = data


_MANAGER = AsyncJobManager()


def submit_job(request: dict[str, Any]) -> dict[str, Any]:
    return _MANAGER.submit_job(request)


def get_job(job_id: str) -> dict[str, Any]:
    return _MANAGER.get_job(job_id)


def list_jobs(limit: int = 10) -> list[dict[str, Any]]:
    with _MANAGER._lock:
        jobs = [copy.deepcopy(job) for job in _MANAGER._jobs.values()]
    jobs.sort(key=lambda job: str(job.get("submitted_at", "")), reverse=True)
    return jobs[: max(0, int(limit))]


def is_terminal_status(status: str) -> bool:
    return status in _TERMINAL_STATES


def get_jobs_dir() -> str:
    _ensure_jobs_dir()
    return str(_JOBS_DIR)
