"""Long-poll bridge for Jac def:pub wait_job_notification."""
from __future__ import annotations

from typing import Any

from src.core.job_event_hub import get_hub


def wait_job_notification(job_id: str, since_seq: int = 0, timeout_s: float = 25.0) -> dict[str, Any]:
    return get_hub().wait_next(str(job_id), int(since_seq), float(timeout_s))
