"""cancel_job marks in-flight async jobs as interrupted."""

from __future__ import annotations

import time
import uuid

import pytest


def test_cancel_while_worker_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.async_jobs as aj

    def _slow_worker(request: dict) -> dict:  # type: ignore[no-untyped-def]
        time.sleep(15.0)
        return {
            "returncode": 0,
            "stdout": '{"optimized_code":"x"}\n',
            "stderr": "",
            "result": {
                "optimized_code": "x",
                "improvement_ratio": 1.0,
                "test_passed": True,
            },
            "pid": None,
        }

    monkeypatch.setattr(aj, "run_local_worker_request", _slow_worker)

    from src.core.async_jobs import cancel_job, get_job, submit_job

    job_id = f"cancel-test-{uuid.uuid4().hex}"
    submit_job(
        {
            "operation": "optimize_input",
            "job_id": job_id,
            "run_name": "unit-cancel",
            "config_name": "test-fast",
            "input": {
                "source_code": "def x():\n    return 1\n",
                "function_name": "x",
                "function_call": "x()",
                "test_cases": [],
            },
        }
    )

    deadline = time.time() + 10.0
    saw_running = False
    while time.time() < deadline:
        if str(get_job(job_id).get("status", "")) == "running":
            saw_running = True
            break
        time.sleep(0.05)

    assert saw_running

    out = cancel_job(job_id)
    assert out.get("success") is True

    deadline = time.time() + 5.0
    status = ""
    while time.time() < deadline:
        status = str(get_job(job_id).get("status", ""))
        if status == "interrupted":
            break
        time.sleep(0.05)

    assert status == "interrupted"
