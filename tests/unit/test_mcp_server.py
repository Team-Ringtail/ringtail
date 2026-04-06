from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.cprofile_analyzer import CallDAG, FunctionProfile, ProfileAnalysis
from src.core.optimization_dag import AttemptResult, DAGResult, FunctionResult
from src.mcp import acceptance
from src.mcp import server


def _write_profile_fixture_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "target.py").write_text(
        "\n".join(
            [
                "def slow_sum(n: int) -> int:",
                "    total = 0",
                "    for _ in range(1000):",
                "        for value in range(n):",
                "            total += value",
                "    return total",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo_dir / "runner.py").write_text(
        "\n".join(
            [
                "from target import slow_sum",
                "",
                "def main() -> None:",
                "    slow_sum(200)",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return repo_dir


def _profile_analysis_for(path: Path) -> tuple[str, ProfileAnalysis]:
    function_path = str(path / "target.py")
    hotspot_key = f"{function_path}:1:slow_sum"
    profile = FunctionProfile(
        module="target",
        name="slow_sum",
        file_path=function_path,
        lineno=1,
        tottime=0.8,
        cumtime=0.8,
        ncalls=1,
        callers=[],
        callees=[],
        hotness_pct=80.0,
    )
    return hotspot_key, ProfileAnalysis(
        functions={hotspot_key: profile},
        call_graph={},
        total_time=1.0,
        entry_point="python runner.py",
        repo_path=str(path),
    )


def test_profile_repo_returns_structured_contract(tmp_path: Path) -> None:
    repo_dir = _write_profile_fixture_repo(tmp_path)

    payload = json.loads(
        server.profile_repo(
            repo_path=str(repo_dir),
            entry_point="python runner.py",
            pct_threshold=1.0,
            max_results=5,
            timeout_s=30,
        )
    )

    assert payload["success"] is True
    assert payload["kind"] == "profile_report"
    assert payload["recommended_targets"]
    assert payload["hotspots"]
    hotspot = payload["hotspots"][0]
    assert hotspot["id"]
    assert hotspot["ownership"] in {"user_code", "mixed", "library_bound"}
    assert isinstance(hotspot["callers"], list)
    assert isinstance(hotspot["callees"], list)
    assert "optimize_hotspot" in payload["next_action"]


def test_profile_repo_returns_structured_error_for_missing_repo() -> None:
    payload = json.loads(
        server.profile_repo(
            repo_path="/tmp/does-not-exist-ringtail-mcp",
            entry_point="python runner.py",
        )
    )

    assert payload["success"] is False
    assert payload["error"]["code"] == "profile_repo_failed"
    assert "traceback" not in json.dumps(payload).lower()


def test_rank_hotspots_orders_by_hotness_and_time(tmp_path: Path) -> None:
    repo_dir = _write_profile_fixture_repo(tmp_path)
    target = str(repo_dir / "target.py")
    faster_key = f"{target}:1:first"
    slower_key = f"{target}:8:second"
    analysis = SimpleNamespace(
        functions={
            faster_key: FunctionProfile(
                module="target",
                name="first",
                file_path=target,
                lineno=1,
                tottime=0.2,
                cumtime=0.2,
                ncalls=1,
                hotness_pct=20.0,
            ),
            slower_key: FunctionProfile(
                module="target",
                name="second",
                file_path=target,
                lineno=8,
                tottime=0.5,
                cumtime=0.7,
                ncalls=1,
                hotness_pct=50.0,
            ),
        }
    )

    ranked = server._rank_hotspots(analysis, {faster_key, slower_key})

    assert [item[0] for item in ranked] == [slower_key, faster_key]


def test_build_hotspot_summary_marks_library_bound(tmp_path: Path) -> None:
    repo_dir = _write_profile_fixture_repo(tmp_path)
    target_path = str(repo_dir / "target.py")
    function_profile = FunctionProfile(
        module="target",
        name="slow_sum",
        file_path=target_path,
        lineno=1,
        tottime=0.05,
        cumtime=0.50,
        ncalls=1,
        callers=[],
        callees=[],
        hotness_pct=50.0,
    )
    dag = CallDAG(levels=[["node"]], nodes={"node": function_profile}, edges={})

    summary = server._build_hotspot_summary(
        key="node",
        function_profile=function_profile,
        dag=dag,
        rank=1,
    )

    assert summary.ownership == "library_bound"
    assert summary.worth_optimizing is False
    assert "outside editable repo code" in summary.skip_reason


def test_optimize_hotspot_returns_validated_patch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_dir = _write_profile_fixture_repo(tmp_path)
    hotspot_key, analysis = _profile_analysis_for(repo_dir)
    target_path = str(repo_dir / "target.py")

    import src.core.arg_capture as arg_capture
    import src.core.cprofile_analyzer as analyzer
    import src.core.optimization_dag as optimization_dag

    monkeypatch.setattr(analyzer, "run_cprofile_analysis", lambda *args, **kwargs: analysis)
    monkeypatch.setattr(analyzer, "compute_hotness_threshold", lambda *args, **kwargs: {hotspot_key})
    monkeypatch.setattr(arg_capture, "capture_function_io", lambda *args, **kwargs: {hotspot_key: []})
    monkeypatch.setattr(
        optimization_dag,
        "optimize_dag",
        lambda **kwargs: DAGResult(
            function_results={
                hotspot_key: FunctionResult(
                    func_key=hotspot_key,
                    function_name="slow_sum",
                    file_path=target_path,
                    original_source="def slow_sum(n: int) -> int:\n    return n\n",
                    optimized_source="def slow_sum(n: int) -> int:\n    return n + 1\n",
                    success=True,
                    attempts=[
                        AttemptResult(
                            attempt=1,
                            optimized_code="def slow_sum(n: int) -> int:\n    return n + 1\n",
                            test_passed=True,
                            test_output={"failures": []},
                        )
                    ],
                    baseline_tottime=0.8,
                    optimized_tottime=0.4,
                    speedup=2.0,
                )
            },
            baseline_total_time=0.8,
            optimized_total_time=0.4,
            overall_speedup=2.0,
            levels_processed=1,
            total_functions=1,
            successful_optimizations=1,
            failed_optimizations=0,
            skipped_functions=0,
            skipped_by_reason={},
            baseline_program_time=1.0,
            optimized_program_time=0.5,
            program_speedup=2.0,
        ),
    )

    payload = json.loads(
        server.optimize_hotspot(
            repo_path=str(repo_dir),
            entry_point="python runner.py",
            hotspot_id=hotspot_key,
            analysis_mode="mock",
            min_speedup=1.1,
        )
    )

    assert payload["success"] is True
    assert payload["validation"]["accepted"] is True
    assert payload["metrics"]["function_speedup"] == 2.0
    assert payload["patch"]["diff"].startswith("--- ")


def test_optimize_hotspot_rejects_below_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_dir = _write_profile_fixture_repo(tmp_path)
    hotspot_key, analysis = _profile_analysis_for(repo_dir)
    target_path = str(repo_dir / "target.py")

    import src.core.arg_capture as arg_capture
    import src.core.cprofile_analyzer as analyzer
    import src.core.optimization_dag as optimization_dag

    monkeypatch.setattr(analyzer, "run_cprofile_analysis", lambda *args, **kwargs: analysis)
    monkeypatch.setattr(analyzer, "compute_hotness_threshold", lambda *args, **kwargs: {hotspot_key})
    monkeypatch.setattr(arg_capture, "capture_function_io", lambda *args, **kwargs: {hotspot_key: []})
    monkeypatch.setattr(
        optimization_dag,
        "optimize_dag",
        lambda **kwargs: DAGResult(
            function_results={
                hotspot_key: FunctionResult(
                    func_key=hotspot_key,
                    function_name="slow_sum",
                    file_path=target_path,
                    original_source="def slow_sum(n: int) -> int:\n    return n\n",
                    optimized_source="def slow_sum(n: int) -> int:\n    return n\n",
                    success=True,
                    attempts=[
                        AttemptResult(
                            attempt=1,
                            optimized_code="def slow_sum(n: int) -> int:\n    return n\n",
                            test_passed=True,
                            test_output={"failures": []},
                        )
                    ],
                    baseline_tottime=0.8,
                    optimized_tottime=0.75,
                    speedup=1.06,
                )
            },
            baseline_total_time=0.8,
            optimized_total_time=0.75,
            overall_speedup=1.06,
            levels_processed=1,
            total_functions=1,
            successful_optimizations=1,
            failed_optimizations=0,
            skipped_functions=0,
            skipped_by_reason={},
            baseline_program_time=1.0,
            optimized_program_time=0.95,
            program_speedup=1.05,
        ),
    )

    payload = json.loads(
        server.optimize_hotspot(
            repo_path=str(repo_dir),
            entry_point="python runner.py",
            hotspot_id=hotspot_key,
            analysis_mode="mock",
            min_speedup=1.1,
        )
    )

    assert payload["success"] is False
    assert payload["error"]["code"] == "optimization_rejected"
    assert payload["validation"]["accepted"] is False
    assert payload["metrics"]["function_speedup"] is None


def test_submit_and_get_async_repo_job(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.core.async_jobs as async_jobs

    monkeypatch.setattr(
        async_jobs,
        "submit_job",
        lambda request: {
            "job_id": "job-123",
            "status": "queued",
            "run_id": "run-123",
            "run_log_path": "/tmp/run-123.jsonl",
        },
    )
    monkeypatch.setattr(
        async_jobs,
        "get_job",
        lambda job_id: {
            "job_id": job_id,
            "status": "running",
            "run_id": "run-123",
        },
    )

    submit_payload = json.loads(
        server.submit_optimize_repo_job(
            repo_url="/tmp/local-repo",
            entry_point="python runner.py",
        )
    )
    status_payload = json.loads(server.get_optimize_repo_job("job-123"))

    assert submit_payload["success"] is True
    assert submit_payload["job_id"] == "job-123"
    assert status_payload["success"] is True
    assert status_payload["job"]["status"] == "running"


def test_acceptance_gate_rejects_missing_speedup() -> None:
    decision = acceptance.evaluate_hotspot_acceptance(
        tests_passed=True,
        speedup=None,
        post_profile_completed=True,
        min_speedup=1.1,
    )

    assert decision.accepted is False
    assert "no measured speedup was produced" in decision.reasons
