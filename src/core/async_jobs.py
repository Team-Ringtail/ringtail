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
import signal
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from src.core.optimization_request_contract import normalize_request_defaults
from src.core.worker_runner import run_local_worker_request
from src.utils.run_log import LOGS_DIR, RunLog

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_LOGS_ROOT = Path(LOGS_DIR).resolve()
_JOBS_DIR = Path(os.environ.get("RINGTAIL_ASYNC_JOBS_DIR", Path(LOGS_DIR) / "async_jobs"))
_TERMINAL_STATES = {"succeeded", "failed", "interrupted"}

# Match RunLog._summary generic branch limit so pollers / UI see full payloads.
_ACTIVITY_LOG_SUMMARY_CHARS = 8000


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log_path_for_run_id(run_id: str) -> str:
    return str(Path(LOGS_DIR) / f"{run_id}.jsonl")


def _ensure_jobs_dir() -> None:
    _JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _job_path(job_id: str) -> Path:
    return _JOBS_DIR / f"{job_id}.json"


def _resolve_safe_log_path(log_path: str) -> Path | None:
    """Return a path under LOGS_DIR only (basename for relative paths)."""
    raw = str(log_path or "").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = _LOGS_ROOT / candidate.name
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    try:
        resolved.relative_to(_LOGS_ROOT)
    except ValueError:
        return None
    if resolved.suffix != ".jsonl":
        return None
    return resolved


def _tail_jsonl_activity(log_path: str, *, max_lines: int = 100) -> list[str]:
    path = _resolve_safe_log_path(log_path)
    if path is None or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    out: list[str] = []
    for raw in tail:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            out.append(raw[:_ACTIVITY_LOG_SUMMARY_CHARS])
            continue
        if not isinstance(obj, dict):
            out.append(str(obj)[:_ACTIVITY_LOG_SUMMARY_CHARS])
            continue
        kind = str(obj.get("kind", "event"))
        elapsed = obj.get("elapsed_s", "")
        payload = {k: v for k, v in obj.items() if k not in ("ts", "seq", "kind", "elapsed_s")}
        summary = RunLog._summary(kind, payload, max_payload_chars=_ACTIVITY_LOG_SUMMARY_CHARS)
        out.append(f"+{elapsed}s  [{kind}]  {summary}")
    return out


def _activity_overlay_for_job(job: dict[str, Any]) -> list[str]:
    """Human-readable job status + tail of structured run log for pollers / UI."""
    lines: list[str] = []
    status = str(job.get("status", ""))
    run_id = str(job.get("run_id", ""))
    run_log_path = str(job.get("run_log_path", "")).strip()

    wm = str(job.get("worker_message", "")).strip()
    if wm:
        lines.append(f"[job] {wm}")

    if status == "queued":
        lines.append(f"[job] Queued — starting background worker (run_id={run_id})")
    elif status == "running":
        lines.append(
            "[job] Running — Jac worker subprocess is executing (LLM calls can take several minutes)."
        )
    elif status == "succeeded":
        lines.append("[job] Succeeded — optimization finished.")
    elif status == "failed":
        err = str(job.get("error", "")).strip()
        if err:
            lines.append(f"[job] Failed — {err[:800]}")
        # If the optimizer produced structured failure feedback, surface the
        # falsifying example to avoid forcing users to open the jsonl log.
        res = job.get("result")
        if isinstance(res, dict):
            fb = res.get("feedback")
            if isinstance(fb, dict):
                fx = str(fb.get("falsifying_example", "")).strip()
                if fx:
                    lines.append("[property_tests] Falsifying example:")
                    # Keep it readable inside a <pre>.
                    lines.append(fx[:1200])
    elif status == "interrupted":
        lines.append("[job] Interrupted — server restarted or job was orphaned.")

    tail = _tail_jsonl_activity(run_log_path, max_lines=100)
    if tail:
        lines.append("--- run log (latest) ---")
        lines.extend(tail)
    elif status in ("queued", "running") and run_log_path:
        lines.append(
            "[job] No run-log lines yet — they appear once the optimizer creates the log file."
        )

    return lines


def _attach_activity_view(job: dict[str, Any]) -> dict[str, Any]:
    view = copy.deepcopy(job)
    if view.get("status") == "not_found":
        view["activity_log_lines"] = []
        return view
    view["activity_log_lines"] = _activity_overlay_for_job(view)
    return view


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
        self._cancel_requested: set[str] = set()
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
        try:
            from src.core.job_event_hub import get_hub

            get_hub().notify(job_id)
        except Exception:
            pass
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                persisted = self._read_persisted_job(job_id)
                if persisted is not None:
                    self._jobs[job_id] = persisted
                    return _attach_activity_view(copy.deepcopy(persisted))
                return _attach_activity_view(
                    {
                        "job_id": job_id,
                        "status": "not_found",
                        "error": f"Unknown job_id: {job_id}",
                    }
                )
            return _attach_activity_view(copy.deepcopy(job))

    def _update_job(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if str(job.get("status", "")) == "interrupted" and "status" in changes:
                new_st = str(changes.get("status", ""))
                if new_st != "interrupted":
                    changes = {k: v for k, v in changes.items() if k != "status"}
                    if not changes:
                        return
            job.update(changes)
            self._persist_job(job)
        try:
            from src.core.job_event_hub import (
                ensure_demo_progress_watcher,
                ensure_log_tail_watcher,
                get_hub,
            )

            get_hub().notify(job_id)
            if str(changes.get("status", "")) == "running":
                with self._lock:
                    j = self._jobs.get(job_id)
                if j:
                    summary = j.get("request_summary")
                    if isinstance(summary, dict) and str(summary.get("operation", "")) == "run_ranked_demo_suite":
                        ensure_demo_progress_watcher(job_id)
                    if str(j.get("run_log_path", "")).strip():
                        ensure_log_tail_watcher(job_id)
        except Exception:
            pass

    def _run_job(self, job_id: str, request: dict[str, Any]) -> None:
        try:
            with self._lock:
                if job_id in self._cancel_requested:
                    self._cancel_requested.discard(job_id)
                    job = self._jobs.get(job_id)
                    if job is not None and str(job.get("status", "")) not in _TERMINAL_STATES:
                        job.update(
                            status="interrupted",
                            finished_at=_utc_timestamp(),
                            error="Cancelled by user",
                            worker_message="",
                        )
                        self._persist_job(job)
                    try:
                        from src.core.job_event_hub import get_hub

                        get_hub().notify(job_id)
                    except Exception:
                        pass
                    return

            self._update_job(
                job_id,
                status="running",
                started_at=_utc_timestamp(),
                worker_message="Worker thread started; invoking `jac run async_optimize_worker.jac`…",
            )
            worker = run_local_worker_request(request)

            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None and str(job.get("status", "")) == "interrupted":
                    return

            self._update_job(job_id, pid=worker.get("pid"))
            result = worker.get("result")

            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None and str(job.get("status", "")) == "interrupted":
                    return

            if int(worker.get("returncode", -1)) == 0 and isinstance(result, dict):
                err_txt = str(result.get("error", "")).strip()
                if err_txt:
                    self._update_job(
                        job_id,
                        status="failed",
                        finished_at=_utc_timestamp(),
                        result=result,
                        error=err_txt,
                        pid=None,
                        worker_message="",
                    )
                    return
                self._update_job(
                    job_id,
                    status="succeeded",
                    finished_at=_utc_timestamp(),
                    result=result,
                    error="",
                    pid=None,
                    worker_message="",
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
                worker_message="",
            )
        except Exception as exc:  # pragma: no cover - defensive bridge path
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None and str(job.get("status", "")) == "interrupted":
                    return
            self._update_job(
                job_id,
                status="failed",
                finished_at=_utc_timestamp(),
                error=str(exc),
                pid=None,
                worker_message="",
            )

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Mark a queued or running job interrupted; SIGTERM the worker PID when known."""
        job_id = str(job_id or "").strip()
        if not job_id:
            return _attach_activity_view(
                {
                    "success": False,
                    "error": "job_id required",
                    "job_id": "",
                    "status": "not_found",
                }
            )

        pid_to_kill: int | None = None
        not_found = False
        already_terminal = False
        terminal_status = ""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                persisted = self._read_persisted_job(job_id)
                if persisted is not None:
                    self._jobs[job_id] = persisted
                    job = persisted
            if job is None:
                not_found = True
            else:
                st = str(job.get("status", ""))
                if st in _TERMINAL_STATES:
                    already_terminal = True
                    terminal_status = st
                elif st == "queued":
                    self._cancel_requested.add(job_id)
                elif st == "running":
                    raw_pid = job.get("pid")
                    if isinstance(raw_pid, int) and raw_pid > 0:
                        pid_to_kill = raw_pid
                    job.update(
                        status="interrupted",
                        finished_at=_utc_timestamp(),
                        error="Cancelled by user",
                        pid=None,
                        worker_message="",
                    )
                    self._persist_job(job)
                else:
                    self._cancel_requested.add(job_id)

        if not_found:
            return _attach_activity_view(
                {
                    "success": False,
                    "error": "not_found",
                    "job_id": job_id,
                    "status": "not_found",
                }
            )

        if already_terminal:
            view = self.get_job(job_id)
            if isinstance(view, dict):
                merged = dict(view)
                merged["success"] = False
                merged["error"] = "already_terminal"
                return merged
            return {
                "success": False,
                "error": "already_terminal",
                "job_id": job_id,
                "status": terminal_status,
            }

        if pid_to_kill is not None:
            try:
                os.kill(pid_to_kill, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, ValueError, TypeError, OSError):
                pass

        try:
            from src.core.job_event_hub import get_hub

            get_hub().notify(job_id)
        except Exception:
            pass

        view = self.get_job(job_id)
        if isinstance(view, dict):
            merged = dict(view)
            merged["success"] = True
            return merged
        return {"success": True, "job_id": job_id, "status": "interrupted"}

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


def cancel_job(job_id: str) -> dict[str, Any]:
    return _MANAGER.cancel_job(job_id)


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
