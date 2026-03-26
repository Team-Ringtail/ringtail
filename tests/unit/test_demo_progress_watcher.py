"""Server-side ranked demo progress file watcher (JobEventHub notify)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from src.core.job_event_hub import ensure_demo_progress_watcher, get_hub


def test_demo_progress_watcher_notifies_on_file_change(tmp_path: Path, monkeypatch) -> None:
    from src.core import ranked_demo_suite

    job_id = "demo-progress-notify-" + uuid.uuid4().hex[:10]
    path = tmp_path / f"{job_id}.json"

    monkeypatch.setattr(ranked_demo_suite, "_progress_path", lambda jid: path)

    def fake_get_job(jid: str) -> dict:
        return {"status": "running", "job_id": jid}

    monkeypatch.setattr("src.core.async_jobs.get_job", fake_get_job)

    hub = get_hub()
    seq_before = hub.current_seq(job_id)
    path.write_text(json.dumps({"status": "running"}))

    ensure_demo_progress_watcher(job_id)

    # Real sleep so the daemon thread can observe the file and notify.
    import time

    deadline = time.monotonic() + 3.0
    while hub.current_seq(job_id) <= seq_before and time.monotonic() < deadline:
        time.sleep(0.05)

    assert hub.current_seq(job_id) >= seq_before + 1
