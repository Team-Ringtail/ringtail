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
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from src.core.optimization_request_contract import normalize_request_defaults
from src.core.worker_runner import run_local_worker_request
from src.utils.run_log import LOGS_DIR

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
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
        payload = normalize_request_defaults(dict(request))
        payload["job_id"] = job_id
        payload["run_id"] = run_id
        payload["run_name"] = run_name

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
        try:
            self._update_job(job_id, status="running", started_at=_utc_timestamp())
            worker = run_local_worker_request(request)
            self._update_job(job_id, pid=worker.get("pid"))
            result = worker.get("result")

            if int(worker.get("returncode", -1)) == 0 and isinstance(result, dict):
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

            error_message = str(worker.get("stderr", "")).strip() or "Async worker failed"
            if isinstance(result, dict) and result.get("error"):
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
