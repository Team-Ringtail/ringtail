"""
In-process Observer subject for async + demo jobs.

Thread-safe notifications used by wait_job_notification (long-poll) so the UI
updates when job state or run logs change without client timer polling.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

_hub_lock = threading.Lock()
_hub: JobEventHub | None = None

_WATCH_LOCK = threading.Lock()
_LOG_TAIL_STARTED: set[str] = set()
_DEMO_PROGRESS_STARTED: set[str] = set()


class JobEventHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq: dict[str, int] = {}
        self._conds: dict[str, threading.Condition] = {}

    def _cond(self, job_id: str) -> threading.Condition:
        if job_id not in self._conds:
            self._conds[job_id] = threading.Condition(self._lock)
        return self._conds[job_id]

    def notify(self, job_id: str) -> None:
        jid = str(job_id or "").strip()
        if not jid:
            return
        with self._lock:
            self._seq[jid] = self._seq.get(jid, 0) + 1
            self._cond(jid).notify_all()

    def current_seq(self, job_id: str) -> int:
        jid = str(job_id or "").strip()
        with self._lock:
            return self._seq.get(jid, 0)

    def wait_next(
        self,
        job_id: str,
        since_seq: int,
        timeout_s: float,
    ) -> dict[str, Any]:
        jid = str(job_id or "").strip()
        deadline = time.monotonic() + max(0.1, float(timeout_s))
        with self._lock:
            cond = self._cond(jid)
            while self._seq.get(jid, 0) <= int(since_seq):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                cond.wait(remaining)
            seq = self._seq.get(jid, 0)

        kind, data = build_job_snapshot(jid)
        terminal = snapshot_is_terminal(kind, data)
        return {
            "seq": seq,
            "heartbeat": seq <= int(since_seq),
            "terminal": terminal,
            "kind": kind,
            "data": data,
        }


def get_hub() -> JobEventHub:
    global _hub
    with _hub_lock:
        if _hub is None:
            _hub = JobEventHub()
        return _hub


def build_job_snapshot(job_id: str) -> tuple[str, dict[str, Any]]:
    from src.core import async_jobs
    from src.core.ranked_demo_suite import _read_progress, get_demo_job_progress

    if _read_progress(job_id) is not None:
        return "demo", get_demo_job_progress(job_id)
    j = async_jobs.get_job(job_id)
    if str(j.get("status")) != "not_found":
        return "async_job", j
    return "demo", get_demo_job_progress(job_id)


def snapshot_is_terminal(kind: str, data: dict[str, Any]) -> bool:
    if kind == "async_job":
        st = str(data.get("status", ""))
        if st not in ("succeeded", "failed", "interrupted", "not_found"):
            return False

        run_log_path = str(data.get("run_log_path", "")).strip()
        # If we don't know of a run log path, consider it terminal to avoid
        # infinite long-polling when logs are disabled.
        if run_log_path == "":
            return True

        # If the log file doesn't exist (e.g., logs disabled), we cannot
        # stream run-log lines, so stop.
        try:
            from src.core.async_jobs import _resolve_safe_log_path  # type: ignore[attr-defined]

            safe_path = _resolve_safe_log_path(run_log_path)
        except Exception:
            return True

        if safe_path is None or not safe_path.exists():
            return True

        act_lines = data.get("activity_log_lines", [])
        if isinstance(act_lines, list):
            for ln in act_lines:
                if "[run_end]" in str(ln):
                    return True

        # Job status may be terminal, but the run log may still be getting
        # its final event written (common with buffered/flushed writers).
        return False
    jst = str(data.get("job_status", ""))
    if jst in ("succeeded", "failed", "interrupted"):
        return True
    dst = str(data.get("status", ""))
    return dst in ("succeeded", "failed")


def ensure_log_tail_watcher(job_id: str) -> None:
    from src.core import async_jobs

    jid = str(job_id or "").strip()
    if not jid:
        return
    with _WATCH_LOCK:
        if jid in _LOG_TAIL_STARTED:
            return
        _LOG_TAIL_STARTED.add(jid)

    def _run() -> None:
        last_size: int | None = None
        last_change_ts: float | None = None
        terminal_start_ts: float | None = None
        stable_after_change_s = 1.5
        max_terminal_wait_s = 6.0
        try:
            from src.core.async_jobs import _resolve_safe_log_path  # type: ignore[attr-defined]

            while True:
                snap = async_jobs.get_job(jid)
                st = str(snap.get("status", ""))
                is_terminal = st not in ("queued", "running")
                rlp = str(snap.get("run_log_path", "")).strip()
                path: Path | None = _resolve_safe_log_path(rlp) if rlp else None

                if path and path.is_file():
                    try:
                        sz = path.stat().st_size
                    except OSError:
                        sz = -1
                    if last_size is None or sz != last_size:
                        last_size = sz
                        last_change_ts = time.monotonic()
                        get_hub().notify(jid)
                else:
                    # In some cases the job status may flip terminal before the
                    # run-log file exists; wait a bit to see if it appears.
                    if is_terminal:
                        if terminal_start_ts is None:
                            terminal_start_ts = time.monotonic()
                        if time.monotonic() - terminal_start_ts > max_terminal_wait_s:
                            break

                if is_terminal:
                    if terminal_start_ts is None:
                        terminal_start_ts = time.monotonic()

                    # Stop once the log size has been stable long enough
                    # (after the final write, which should include `run_end`).
                    if last_change_ts is not None:
                        if time.monotonic() - last_change_ts > stable_after_change_s:
                            break
                    else:
                        # No size changes observed; cap the wait so the UI
                        # doesn't hang when logs never materialize.
                        if time.monotonic() - terminal_start_ts > max_terminal_wait_s:
                            break

                time.sleep(0.75)
        finally:
            with _WATCH_LOCK:
                _LOG_TAIL_STARTED.discard(jid)

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"ringtail-logtail-{jid[:12]}",
    ).start()


def ensure_demo_progress_watcher(job_id: str) -> None:
    """Notify the server hub when ranked-demo `_progress/*.json` changes.

    `run_demo_suite` runs in a worker subprocess; its `get_hub().notify` calls
    do not affect this process. Watching the progress file from the server
    restores live long-poll updates for the benchmark tab.
    """
    from src.core import async_jobs
    from src.core.ranked_demo_suite import _progress_path

    jid = str(job_id or "").strip()
    if not jid:
        return
    with _WATCH_LOCK:
        if jid in _DEMO_PROGRESS_STARTED:
            return
        _DEMO_PROGRESS_STARTED.add(jid)

    def _run() -> None:
        last_size: int | None = None
        terminal_start_ts: float | None = None
        max_terminal_wait_s = 8.0
        try:
            while True:
                snap = async_jobs.get_job(jid)
                st = str(snap.get("status", ""))
                is_terminal = st in ("succeeded", "failed", "interrupted", "not_found")

                path = _progress_path(jid)
                if path.is_file():
                    try:
                        sz = path.stat().st_size
                    except OSError:
                        sz = -1
                    if last_size is None or sz != last_size:
                        last_size = sz
                        get_hub().notify(jid)

                if is_terminal:
                    if terminal_start_ts is None:
                        terminal_start_ts = time.monotonic()
                    if time.monotonic() - terminal_start_ts > max_terminal_wait_s:
                        break

                time.sleep(0.75)
        finally:
            with _WATCH_LOCK:
                _DEMO_PROGRESS_STARTED.discard(jid)

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"ringtail-demoprogress-{jid[:12]}",
    ).start()
