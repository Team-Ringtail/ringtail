"""Async job manager marks failed when worker returns error-shaped JSON."""

from __future__ import annotations

import time
import uuid

import pytest


@pytest.fixture()
def patch_worker(monkeypatch: pytest.MonkeyPatch):
    def fake_worker(_request: dict):  # type: ignore[no-untyped-def]
        return {
            "returncode": 0,
            "stdout": '{"error":"unit synthetic failure"}\n',
            "stderr": "",
            "result": {
                "error": "unit synthetic failure",
                "test_passed": False,
                "optimized_code": "",
            },
            "pid": None,
        }

    import src.core.async_jobs as aj

    monkeypatch.setattr(aj, "run_local_worker_request", fake_worker)
    return monkeypatch


def test_job_status_failed_when_result_contains_error(
    patch_worker: pytest.MonkeyPatch,
) -> None:
    from src.core.async_jobs import get_job, submit_job

    job_id = f"test-err-{uuid.uuid4().hex}"
    submit_job(
        {
            "operation": "optimize_input",
            "job_id": job_id,
            "run_name": "unit-error-shape",
            "config_name": "test-fast",
            "input": {
                "source_code": "def x():\n    return 1\n",
                "function_name": "x",
                "function_call": "x()",
                "test_cases": [],
            },
        }
    )
    deadline = time.time() + 20.0
    status = ""
    while time.time() < deadline:
        status = str(get_job(job_id).get("status", ""))
        if status in ("failed", "succeeded"):
            break
        time.sleep(0.05)
    assert status == "failed"
    err = str(get_job(job_id).get("error", ""))
    assert "synthetic failure" in err
