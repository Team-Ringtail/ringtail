"""
Centralized run logging for Ringtail.

Every LLM call, sandbox execution, benchmark result, and optimization step
gets recorded as a structured JSON event in a single timestamped log file
per run.  A human-readable summary is printed to stderr in real time.

Usage:
    from src.utils.run_log import RunLog

    log = RunLog("optimize-two_sum")
    log.event("llm_call", model="claude-sonnet-4-20250514", tokens_in=500, tokens_out=1200)
    log.event("sandbox_exec", backend="blaxel", returncode=0)
    log.event("benchmark", slug="two_sum", passed=1, time_s=0.04)
    log.close()

Logs are written to  logs/<run_id>_<timestamp>.jsonl  (one JSON object per line).
A combined index at  logs/runs.jsonl  tracks every run for quick querying.
"""
import datetime as _dt
import json
import os
import sys
import time

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")


class RunLog:
    def __init__(self, run_name: str = "run"):
        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{run_name}_{ts}"
        self.log_path = os.path.join(LOGS_DIR, f"{self.run_id}.jsonl")
        self.start_time = time.monotonic()
        self._file = open(self.log_path, "a")
        self._event_count = 0

        self.event("run_start", run_name=run_name)
        self._print(f"[run_log] {self.run_id}  ->  {self.log_path}")

    # -- public API ----------------------------------------------------------

    def event(self, kind: str, **data):
        """Append a structured event to the log file and print a summary."""
        entry = {
            "ts": _dt.datetime.utcnow().isoformat() + "Z",
            "elapsed_s": round(time.monotonic() - self.start_time, 3),
            "seq": self._event_count,
            "kind": kind,
            **data,
        }
        self._event_count += 1
        self._file.write(json.dumps(entry, default=str) + "\n")
        self._file.flush()
        self._print(f"  [{kind}] {self._summary(kind, data)}")

    def llm_call(self, *, model: str, prompt_tokens: int = 0, completion_tokens: int = 0, **extra):
        self.event(
            "llm_call",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            **extra,
        )

    def sandbox_exec(self, *, backend: str, command: str = "", returncode: int = -1, **extra):
        self.event("sandbox_exec", backend=backend, command=command, returncode=returncode, **extra)

    def benchmark(self, *, slug: str, passed: int, failed: int, time_s: float, **extra):
        self.event("benchmark", slug=slug, passed=passed, failed=failed, time_s=time_s, **extra)

    def optimization_step(self, *, iteration: int, improvement_ratio: float = 0.0, **extra):
        self.event("optimization_step", iteration=iteration, improvement_ratio=improvement_ratio, **extra)

    def error(self, msg: str, **extra):
        self.event("error", message=msg, **extra)

    def close(self):
        elapsed = round(time.monotonic() - self.start_time, 3)
        self.event("run_end", total_events=self._event_count, elapsed_s=elapsed)
        self._file.close()

        _append_index(self.run_id, self.log_path, elapsed, self._event_count)
        self._print(f"[run_log] done  {self._event_count} events in {elapsed}s")

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _print(msg: str):
        print(msg, file=sys.stderr)

    @staticmethod
    def _summary(kind: str, data: dict) -> str:
        if kind == "llm_call":
            return f"{data.get('model', '?')}  in={data.get('prompt_tokens', '?')} out={data.get('completion_tokens', '?')}"
        if kind == "sandbox_exec":
            rc = data.get("returncode", "?")
            return f"{data.get('backend', '?')}  rc={rc}"
        if kind == "benchmark":
            status = "PASS" if data.get("failed", 1) == 0 else "FAIL"
            return f"{data.get('slug', '?')}  {status}  {data.get('time_s', '?')}s"
        if kind == "error":
            return data.get("message", "")[:120]
        parts = [f"{k}={v}" for k, v in data.items()]
        return " ".join(parts)[:120]


def _append_index(run_id: str, log_path: str, elapsed: float, events: int):
    index_path = os.path.join(LOGS_DIR, "runs.jsonl")
    entry = {
        "run_id": run_id,
        "log_path": log_path,
        "finished": _dt.datetime.utcnow().isoformat() + "Z",
        "elapsed_s": elapsed,
        "events": events,
    }
    with open(index_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
