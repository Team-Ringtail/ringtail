"""JobEventHub long-poll notify behavior."""

from __future__ import annotations

import threading
import time

from src.core.job_event_hub import build_job_snapshot, get_hub


def test_notify_increments_seq_and_unblocks_wait() -> None:
    hub = get_hub()
    job_id = f"hub-test-{threading.get_ident()}"
    start = time.monotonic()
    out: dict = {}

    def waiter() -> None:
        out.update(hub.wait_next(job_id, since_seq=0, timeout_s=2.0))

    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    time.sleep(0.05)
    hub.notify(job_id)
    t.join(timeout=3.0)
    assert not t.is_alive()
    assert out.get("seq", 0) >= 1
    assert time.monotonic() - start < 1.5
    kind, _payload = build_job_snapshot(job_id)
    assert kind in ("async_job", "demo")
