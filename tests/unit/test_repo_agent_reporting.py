from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core import optimization_dag as optimization_dag_module
from src.core.cprofile_analyzer import CallDAG, FunctionProfile
from src.core.optimization_dag import FunctionResult, _reject_slower_results
from src.core.repo_agent import _build_dag_pr_body


def test_build_dag_pr_body_hides_skipped_rows_and_simplifies_summary() -> None:
    dag_result = SimpleNamespace(
        successful_optimizations=1,
        failed_optimizations=1,
        skipped_functions=1,
        skipped_by_reason={"non-function profiler symbol": 1},
        baseline_total_time=0.20,
        optimized_total_time=0.10,
        overall_speedup=2.0,
        baseline_program_time=1.5,
        optimized_program_time=0.75,
        program_speedup=2.0,
        levels_processed=2,
        total_functions=3,
        function_results={
            "ok": FunctionResult(
                func_key="ok",
                function_name="real_func",
                file_path="/tmp/repo/real.py",
                original_source="def real_func():\n    return 1\n",
                optimized_source="def real_func():\n    return 2\n",
                success=True,
                attempts=[],
                baseline_tottime=0.2,
                optimized_tottime=0.1,
                speedup=2.0,
            ),
            "fail": FunctionResult(
                func_key="fail",
                function_name="other_func",
                file_path="/tmp/repo/other.py",
                original_source="def other_func():\n    return 1\n",
                optimized_source=None,
                success=False,
                attempts=[],
                baseline_tottime=0.1,
                optimized_tottime=None,
                speedup=None,
                error="Failed after 3 attempts",
            ),
            "skip": FunctionResult(
                func_key="skip",
                function_name="<module>",
                file_path="/tmp/repo/runner.py",
                original_source="",
                optimized_source=None,
                success=False,
                attempts=[],
                baseline_tottime=0.5,
                optimized_tottime=None,
                speedup=None,
                error="non-function profiler symbol",
                skipped=True,
                skip_reason="non-function profiler symbol",
            ),
        },
    )
    analysis = SimpleNamespace(total_time=1.5, functions={"a": 1, "b": 2, "c": 3})
    body = _build_dag_pr_body(
        {"prompt": "make this faster", "entry_point": "python runner.py"},
        dag_result,
        analysis,
        {"success": True},
        {"mode": "github_app_installation"},
    )

    assert "**Strategy:**" not in body
    assert "Functions analyzed" not in body
    assert "Hot functions identified" not in body
    assert "DAG levels" not in body
    assert "Skipped" not in body
    assert "Failed to optimize: 1" in body
    assert "| Function | File | Baseline (s) | Optimized (s) | Speedup | Attempts | Status |" in body
    assert "`real_func`" in body
    assert "0.1000" in body
    assert "2.00x" in body
    assert "`<module>`" not in body


def test_reject_slower_results_reverts_source_file() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="ringtail_regression_gate_") as tmp_dir:
        target = Path(tmp_dir) / "demo.py"
        original = "def demo():\n    return 1\n"
        slower = "def demo():\n    return 2\n"
        target.write_text(slower, encoding="utf-8")

        result = FunctionResult(
            func_key="demo",
            function_name="demo",
            file_path=str(target),
            original_source=original,
            optimized_source=slower,
            success=True,
            attempts=[],
            baseline_tottime=0.2,
            optimized_tottime=0.4,
            speedup=0.5,
        )

        rejected = _reject_slower_results({"demo": result})

        assert rejected == 1
        assert result.success is False
        assert "Rejected: slower after profiling" in result.error
        assert result.optimized_tottime is None
        assert result.speedup is None
        assert target.read_text(encoding="utf-8") == original


def test_optimize_dag_raises_when_post_profile_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "demo.py"
    target.write_text("def demo():\n    return 1\n", encoding="utf-8")
    func_key = f"{target}:1:demo"
    dag = CallDAG(
        levels=[[func_key]],
        nodes={
            func_key: FunctionProfile(
                module="demo",
                name="demo",
                file_path=str(target),
                lineno=1,
                tottime=0.2,
                cumtime=0.2,
                ncalls=1,
            )
        },
        edges={},
    )

    monkeypatch.setattr(
        optimization_dag_module,
        "optimize_single_function",
        lambda **kwargs: FunctionResult(
            func_key=func_key,
            function_name="demo",
            file_path=str(target),
            original_source=target.read_text(encoding="utf-8"),
            optimized_source=target.read_text(encoding="utf-8"),
            success=True,
            attempts=[],
            baseline_tottime=0.2,
            optimized_tottime=None,
            speedup=None,
        ),
    )
    monkeypatch.setattr(
        optimization_dag_module,
        "run_cprofile_analysis",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="Post-optimization profiling failed: boom"):
        optimization_dag_module.optimize_dag(
            repo_path=str(tmp_path),
            dag=dag,
            io_data={},
            config={"analysis_mode": "mock", "max_parallel_candidates": 1},
            entry_point="python demo.py",
        )
