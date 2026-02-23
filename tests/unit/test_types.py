import json
from dataclasses import asdict

from src.models.types import (
    Metrics,
    FunctionInput,
    OptimizationPlan,
    ConvergenceStatus,
    OptimizationResult,
)


def test_metrics_basic_init():
    m = Metrics(execution_time=1.0, memory_usage=10.0)

    assert m.execution_time == 1.0
    assert m.memory_usage == 10.0
    assert m.cpu_usage is None
    assert m.code_complexity is None
    assert m.test_coverage is None


def test_function_input_defaults():
    fi = FunctionInput(source_code="def f(): pass", function_name="f")

    assert fi.source_code.startswith("def f()")
    assert fi.function_name == "f"
    assert fi.language == "python"
    assert fi.test_cases is None


def test_optimization_plan_optional_target_metrics():
    base_plan = OptimizationPlan(
        analysis="ok",
        optimization_strategy="none",
        estimated_improvement=0.0,
    )
    assert base_plan.target_metrics is None

    metrics = Metrics(execution_time=1.0, memory_usage=5.0)
    plan_with_target = OptimizationPlan(
        analysis="improve",
        optimization_strategy="inline",
        estimated_improvement=1.5,
        target_metrics=metrics,
    )
    assert plan_with_target.target_metrics is metrics


def test_convergence_status_fields():
    status = ConvergenceStatus(
        should_continue=False,
        reason="max iterations",
        converged=False,
    )

    assert status.should_continue is False
    assert status.reason == "max iterations"
    assert status.converged is False


def test_optimization_result_contains_metrics_and_is_serializable():
    metrics = Metrics(execution_time=0.5, memory_usage=3.0)
    result = OptimizationResult(
        optimized_code="def f(): return 1",
        iteration_number=2,
        metrics=metrics,
        test_passed=True,
        improvement_ratio=1.2,
    )

    # Nested dataclass preserved
    assert isinstance(result.metrics, Metrics)
    assert result.metrics.execution_time == 0.5

    # Round-trip via asdict and JSON
    result_dict = asdict(result)
    assert result_dict["metrics"]["execution_time"] == 0.5
    # Should be JSON serializable without error
    json.dumps(result_dict)

