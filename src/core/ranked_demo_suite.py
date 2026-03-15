from __future__ import annotations

import ast
import base64
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.core import async_jobs

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = WORKSPACE_ROOT / "benchmarks" / "ranked_pitch_repo"
DEFAULT_TESTS_ROOT = DEFAULT_SOURCE_ROOT / "tests"
RUNS_ROOT = WORKSPACE_ROOT / "benchmarks" / "ranked_file_suite_runs"
RUNNER_PATH = WORKSPACE_ROOT / "benchmarks" / "ranked_file_suite_runner.py"
DEFAULT_SUITE_NAME = "pitch-ranked-file-suite"
PROGRESS_ROOT = RUNS_ROOT / "_progress"
BENCHMARK_SUITES = {
    "ranked-pitch-repo": {
        "id": "ranked-pitch-repo",
        "label": "Ranked Pitch Repo",
        "description": "Multi-file ranked benchmark suite with per-file finalists and final top-k targets.",
        "source_root": DEFAULT_SOURCE_ROOT,
        "tests_root": DEFAULT_TESTS_ROOT,
    }
}


def get_demo_benchmarks() -> dict[str, Any]:
    suites = []
    for suite in BENCHMARK_SUITES.values():
        suites.append(
            {
                "id": str(suite["id"]),
                "label": str(suite["label"]),
                "description": str(suite["description"]),
                "source_root": str(Path(suite["source_root"]).resolve()),
                "tests_root": str(Path(suite["tests_root"]).resolve()),
            }
        )
    return {
        "default_benchmark_id": "ranked-pitch-repo",
        "benchmarks": suites,
    }


def get_demo_job_progress(job_id: str) -> dict[str, Any]:
    progress = _read_progress(job_id)
    job = async_jobs.get_job(job_id)
    if not isinstance(progress, dict):
        progress = {
            "job_id": job_id,
            "status": str(job.get("status", "unknown")),
            "stage": "Waiting for progress...",
            "progress_pct": 0,
            "log_lines": [],
        }
    progress["job_status"] = str(job.get("status", "unknown"))
    progress["job_error"] = str(job.get("error", ""))
    progress["run_log_path"] = str(job.get("run_log_path", ""))
    if isinstance(job.get("result"), dict):
        progress["result"] = job["result"]
    if str(job.get("status", "")) == "failed" and not str(progress.get("error", "")).strip():
        progress["error"] = str(job.get("error", ""))
    return progress


def _resolve_benchmark(benchmark_id: str | None = None) -> dict[str, Any]:
    selected = str(benchmark_id or "ranked-pitch-repo").strip() or "ranked-pitch-repo"
    suite = BENCHMARK_SUITES.get(selected)
    if suite is None:
        suite = BENCHMARK_SUITES["ranked-pitch-repo"]
    return suite


def get_demo_suite_catalog(benchmark_id: str | None = None) -> dict[str, Any]:
    suite = _resolve_benchmark(benchmark_id)
    root = Path(suite["source_root"]).resolve()
    files = []
    for path in sorted(root.glob("*.py")):
        functions = _discover_python_functions(path)
        files.append(
            {
                "file_name": path.name,
                "file_path": str(path),
                "functions": functions,
            }
        )
    return {
        "benchmark_id": str(suite["id"]),
        "label": str(suite["label"]),
        "description": str(suite["description"]),
        "source_root": str(root),
        "tests_root": str(Path(suite["tests_root"]).resolve()),
        "file_count": len(files),
        "files": files,
    }


def run_demo_suite(
    *,
    server_url: str = "http://127.0.0.1:8000",
    job_id: str | None = None,
    benchmark_id: str | None = None,
    top_k: int = 3,
    per_file_k: int = 1,
) -> dict[str, Any]:
    suite = _resolve_benchmark(benchmark_id)
    root = Path(suite["source_root"]).resolve()
    tests = Path(suite["tests_root"]).resolve()
    output_dir = _new_output_dir()
    progress_job_id = str(job_id or f"demo-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}")
    progress = {
        "job_id": progress_job_id,
        "benchmark_id": str(suite["id"]),
        "benchmark_label": str(suite["label"]),
        "status": "running",
        "stage": "Preparing benchmark run",
        "progress_pct": 5,
        "output_dir": str(output_dir),
        "log_lines": [
            f"Preparing {suite['label']}",
            f"Source root: {root}",
        ],
        "updated_at": dt.datetime.utcnow().isoformat() + "Z",
    }
    _write_progress(progress_job_id, progress)
    _probe_server(server_url)
    command = [
        sys.executable,
        str(RUNNER_PATH),
        "--server-url",
        server_url,
        "--source-root",
        str(root),
        "--tests-root",
        str(tests),
        "--top-k",
        str(int(top_k)),
        "--per-file-k",
        str(int(per_file_k)),
        "--output-dir",
        str(output_dir),
    ]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        command,
        cwd=str(WORKSPACE_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    stdout_lines: list[str] = []
    try:
        if proc.stdout is not None:
            for raw_line in proc.stdout:
                line = raw_line.rstrip()
                stdout_lines.append(line)
                progress["log_lines"] = (progress.get("log_lines", []) + [line])[-20:]
                progress["stage"], progress["progress_pct"] = _stage_for_line(
                    line,
                    top_k=int(top_k),
                    current_pct=int(progress.get("progress_pct", 5)),
                )
                progress["updated_at"] = dt.datetime.utcnow().isoformat() + "Z"
                _write_progress(progress_job_id, progress)
        stderr_text = proc.stderr.read() if proc.stderr is not None else ""
        return_code = proc.wait(timeout=600)
    except Exception:
        proc.kill()
        raise

    payload = load_demo_suite_result(str(output_dir))
    payload["runner_stdout"] = "\n".join(stdout_lines)
    payload["runner_stderr"] = stderr_text
    payload["success"] = return_code == 0 and int(payload.get("summary", {}).get("fail_count", 1)) == 0
    if return_code != 0 and not payload["success"]:
        payload["error"] = (stderr_text or "\n".join(stdout_lines) or "ranked suite runner failed").strip()
    progress["status"] = "succeeded" if bool(payload.get("success", False)) else "failed"
    progress["stage"] = "Benchmark run finished" if bool(payload.get("success", False)) else "Benchmark run failed"
    progress["progress_pct"] = 100 if bool(payload.get("success", False)) else max(int(progress.get("progress_pct", 0)), 90)
    progress["updated_at"] = dt.datetime.utcnow().isoformat() + "Z"
    progress["result"] = payload
    if not bool(payload.get("success", False)):
        progress["error"] = str(payload.get("error", ""))
    _write_progress(progress_job_id, progress)
    return payload


def get_latest_demo_suite_result() -> dict[str, Any]:
    latest = _latest_output_dir()
    if latest is None:
        return {
            "success": False,
            "error": "No ranked demo suite runs found yet.",
        }
    payload = load_demo_suite_result(str(latest))
    payload["success"] = int(payload.get("summary", {}).get("fail_count", 1)) == 0
    return payload


def load_demo_suite_result(output_dir: str) -> dict[str, Any]:
    root = Path(output_dir).expanduser().resolve()
    summary = json.loads((root / "suite_summary.json").read_text())
    ranking = json.loads((root / "ranking.json").read_text())
    per_file = json.loads((root / "per_file_finalists.json").read_text())
    final_ranked = json.loads((root / "final_ranked_targets.json").read_text())
    overview_svg_path = root / "suite_overview.svg"

    enriched_results = []
    for row in summary.get("results", []):
        enriched = dict(row)
        enriched["original_code"] = _read_text(row.get("file_path", ""))
        enriched["optimized_code"] = _read_text(row.get("optimized_code_path", ""))
        enriched["graph_svg_base64"] = _read_base64(row.get("timing_graph_path", ""))
        enriched_results.append(enriched)

    return {
        "output_dir": str(root),
        "summary": {**summary, "results": enriched_results},
        "ranking": ranking,
        "per_file_finalists": per_file,
        "final_ranked_targets": final_ranked,
        "suite_overview_svg_base64": _read_base64(str(overview_svg_path)),
    }


def _new_output_dir() -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RUNS_ROOT / f"{DEFAULT_SUITE_NAME}_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _latest_output_dir() -> Path | None:
    if not RUNS_ROOT.exists():
        return None
    runs = [path for path in RUNS_ROOT.iterdir() if path.is_dir()]
    if not runs:
        return None
    runs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return runs[0]


def _probe_server(server_url: str) -> None:
    with urllib.request.urlopen(server_url.rstrip("/") + "/", timeout=10) as response:
        if getattr(response, "status", 200) >= 400:
            raise RuntimeError(f"Server probe failed with status {response.status}")


def _discover_python_functions(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    functions = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    return functions


def _read_text(raw_path: str) -> str:
    path = Path(str(raw_path).strip())
    if not path.exists():
        return ""
    return path.read_text()


def _read_base64(raw_path: str) -> str:
    path = Path(str(raw_path).strip())
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _progress_path(job_id: str) -> Path:
    PROGRESS_ROOT.mkdir(parents=True, exist_ok=True)
    return PROGRESS_ROOT / f"{job_id}.json"


def _write_progress(job_id: str, payload: dict[str, Any]) -> None:
    _progress_path(job_id).write_text(json.dumps(payload, indent=2, sort_keys=True))


def _read_progress(job_id: str) -> dict[str, Any] | None:
    path = _progress_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _stage_for_line(line: str, *, top_k: int, current_pct: int) -> tuple[str, int]:
    text = str(line).strip()
    if text.startswith("[") and "]" in text:
        prefix = text.split("]", 1)[0].lstrip("[")
        current = 0
        total = max(1, int(top_k))
        if "/" in prefix:
            raw_current, raw_total = prefix.split("/", 1)
            try:
                current = int(raw_current)
                total = max(1, int(raw_total))
            except ValueError:
                current = 0
        pct = min(88, max(current_pct, 18 + int((current / total) * 60)))
        return (f"Optimizing target {max(current, 1)} of {total}", pct)
    if text.startswith("suite_name:") or text.startswith("summary_json:"):
        return ("Finalizing summary artifacts", max(current_pct, 92))
    if text.startswith("target_graphs:"):
        return ("Rendering benchmark graphs", max(current_pct, 96))
    return ("Ranking and optimizing benchmark targets", max(current_pct, 12))
