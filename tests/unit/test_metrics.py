from src.models.types import Metrics
from src.utils.metrics import aggregate_metrics, compare_metrics, calculate_score


def test_aggregate_metrics_single_item():
    m = Metrics(execution_time=1.0, memory_usage=10.0, cpu_usage=50.0, code_complexity=5, test_coverage=80.0)

    agg = aggregate_metrics([m])

    assert agg.execution_time == 1.0
    assert agg.memory_usage == 10.0
    assert agg.cpu_usage == 50.0
    assert agg.code_complexity == 5
    assert agg.test_coverage == 80.0


def test_aggregate_metrics_multiple_items():
    m1 = Metrics(execution_time=1.0, memory_usage=10.0, cpu_usage=50.0, code_complexity=4, test_coverage=80.0)
    m2 = Metrics(execution_time=3.0, memory_usage=14.0, cpu_usage=70.0, code_complexity=6, test_coverage=60.0)

    agg = aggregate_metrics([m1, m2])

    assert agg.execution_time == (1.0 + 3.0) / 2
    assert agg.memory_usage == (10.0 + 14.0) / 2
    assert agg.cpu_usage == (50.0 + 70.0) / 2
    assert agg.code_complexity == int((4 + 6) / 2)
    assert agg.test_coverage == (80.0 + 60.0) / 2


def test_aggregate_metrics_empty_list_returns_defaults():
    agg = aggregate_metrics([])

    assert agg.execution_time == 0.0
    assert agg.memory_usage == 0.0


def test_compare_metrics_improvement_when_faster_and_less_memory():
    baseline = Metrics(execution_time=4.0, memory_usage=20.0)
    current = Metrics(execution_time=2.0, memory_usage=10.0)

    result = compare_metrics(baseline, current)

    assert result["improvement_ratio"] == 4.0 / 2.0
    assert result["time_improvement"] > 0
    assert result["memory_improvement"] > 0
    assert result["is_better"] is True


def test_compare_metrics_no_improvement_when_slower_or_more_memory():
    baseline = Metrics(execution_time=2.0, memory_usage=10.0)
    # Faster but more memory
    current = Metrics(execution_time=1.0, memory_usage=20.0)

    result = compare_metrics(baseline, current)

    assert result["improvement_ratio"] > 1.0
    assert result["is_better"] is False


def test_compare_metrics_handles_zero_baseline():
    baseline = Metrics(execution_time=0.0, memory_usage=0.0)
    current = Metrics(execution_time=1.0, memory_usage=10.0)

    result = compare_metrics(baseline, current)

    assert result["improvement_ratio"] == 1.0
    assert result["time_improvement"] == 0.0
    assert result["memory_improvement"] == 0.0


def test_calculate_score_normalized_weights():
    metrics = Metrics(execution_time=1.0, memory_usage=10.0, code_complexity=5, test_coverage=80.0)
    criteria = {
        "performance_weight": 2.0,
        "code_quality_weight": 3.0,
        "functionality_weight": 5.0,
    }

    score = calculate_score(metrics, criteria)

    assert 0.0 <= score <= 1.0


def test_calculate_score_default_equal_weights_when_zero_total():
    metrics = Metrics(execution_time=1.0, memory_usage=10.0, code_complexity=5, test_coverage=80.0)
    criteria = {
        "performance_weight": 0.0,
        "code_quality_weight": 0.0,
        "functionality_weight": 0.0,
    }

    score = calculate_score(metrics, criteria)

    assert 0.0 <= score <= 1.0


def test_calculate_score_uses_neutral_values_for_missing_metrics():
    metrics = Metrics(execution_time=1.0, memory_usage=10.0)
    criteria = {
        "performance_weight": 1.0,
        "code_quality_weight": 1.0,
        "functionality_weight": 1.0,
    }

    score = calculate_score(metrics, criteria)

    # With missing code_complexity and test_coverage, function should not error and score should be in range.
    assert 0.0 <= score <= 1.0

