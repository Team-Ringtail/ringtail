"""Unit tests for src/utils/metrics.jac."""

import from src.models.types { Metrics }
import from src.utils.metrics { aggregate_metrics, compare_metrics, calculate_score }


test "aggregate_metrics single item" {
    m = Metrics(execution_time=1.0, memory_usage=10.0, cpu_usage=50.0, code_complexity=5, test_coverage=80.0);
    agg = aggregate_metrics([m]);

    assert agg.execution_time == 1.0;
    assert agg.memory_usage == 10.0;
    assert agg.cpu_usage == 50.0;
    assert agg.code_complexity == 5;
    assert agg.test_coverage == 80.0;
}

test "aggregate_metrics multiple items" {
    m1 = Metrics(execution_time=1.0, memory_usage=10.0, cpu_usage=50.0, code_complexity=4, test_coverage=80.0);
    m2 = Metrics(execution_time=3.0, memory_usage=14.0, cpu_usage=70.0, code_complexity=6, test_coverage=60.0);
    agg = aggregate_metrics([m1, m2]);

    assert agg.execution_time == 2.0;
    assert agg.memory_usage == 12.0;
    assert agg.cpu_usage == 60.0;
    assert agg.code_complexity == 5;
    assert agg.test_coverage == 70.0;
}

test "aggregate_metrics empty list returns defaults" {
    agg = aggregate_metrics([]);

    assert agg.execution_time == 0.0;
    assert agg.memory_usage == 0.0;
}

test "compare_metrics improvement when faster and less memory" {
    baseline = Metrics(execution_time=4.0, memory_usage=20.0);
    current = Metrics(execution_time=2.0, memory_usage=10.0);
    result = compare_metrics(
        baseline,
        current,
        0.0,
        0.0,
        0,
        0
    );

    assert result["improvement_ratio"] == 2.0;
    assert result["time_improvement"] > 0;
    assert result["memory_improvement"] > 0;
    assert result["is_better"] is True;
}

test "compare_metrics no improvement when more memory" {
    baseline = Metrics(execution_time=2.0, memory_usage=10.0);
    current = Metrics(execution_time=1.0, memory_usage=20.0);
    result = compare_metrics(
        baseline,
        current,
        0.0,
        0.0,
        0,
        0
    );

    assert result["improvement_ratio"] > 1.0;
    assert result["is_better"] is False;
}

test "compare_metrics handles zero baseline" {
    baseline = Metrics(execution_time=0.0, memory_usage=0.0);
    current = Metrics(execution_time=1.0, memory_usage=10.0);
    result = compare_metrics(
        baseline,
        current,
        0.0,
        0.0,
        0,
        0
    );

    assert result["improvement_ratio"] == 1.0;
    assert result["time_improvement"] == 0.0;
    assert result["memory_improvement"] == 0.0;
}

test "calculate_score normalized weights" {
    metrics = Metrics(execution_time=1.0, memory_usage=10.0, code_complexity=5, test_coverage=80.0);
    criteria = {"performance_weight": 2.0, "code_quality_weight": 3.0, "functionality_weight": 5.0};
    score = calculate_score(metrics, criteria);

    assert score >= 0.0;
    assert score <= 1.0;
}

test "calculate_score default equal weights when zero total" {
    metrics = Metrics(execution_time=1.0, memory_usage=10.0, code_complexity=5, test_coverage=80.0);
    criteria = {"performance_weight": 0.0, "code_quality_weight": 0.0, "functionality_weight": 0.0};
    score = calculate_score(metrics, criteria);

    assert score >= 0.0;
    assert score <= 1.0;
}

test "calculate_score uses neutral values for missing metrics" {
    metrics = Metrics(execution_time=1.0, memory_usage=10.0);
    criteria = {"performance_weight": 1.0, "code_quality_weight": 1.0, "functionality_weight": 1.0};
    score = calculate_score(metrics, criteria);

    assert score >= 0.0;
    assert score <= 1.0;
}
