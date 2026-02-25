"""Metrics aggregation, comparison, and scoring utilities."""

import math;
import from src.models.types { Metrics }


def aggregate_metrics(metrics_list: list) -> Metrics {
    if not metrics_list {
        return Metrics(execution_time=0.0, memory_usage=0.0);
    }

    avg_execution_time = sum(m.execution_time for m in metrics_list) / len(metrics_list);
    avg_memory_usage = sum(m.memory_usage for m in metrics_list) / len(metrics_list);

    cpu_usages = [m.cpu_usage for m in metrics_list if m.cpu_usage is not None];
    avg_cpu_usage = sum(cpu_usages) / len(cpu_usages) if cpu_usages else None;

    complexities = [m.code_complexity for m in metrics_list if m.code_complexity is not None];
    avg_complexity = int(sum(complexities) / len(complexities)) if complexities else None;

    coverages = [m.test_coverage for m in metrics_list if m.test_coverage is not None];
    avg_coverage = sum(coverages) / len(coverages) if coverages else None;

    return Metrics(
        execution_time=avg_execution_time,
        memory_usage=avg_memory_usage,
        cpu_usage=avg_cpu_usage,
        code_complexity=avg_complexity,
        test_coverage=avg_coverage
    );
}


def compare_metrics(
    baseline: Metrics,
    current: Metrics,
    baseline_stdev: float = 0.0,
    current_stdev: float = 0.0,
    baseline_n: int = 0,
    current_n: int = 0
) -> dict {
    """Compare two Metrics instances. Returns improvement ratio, significance, etc."""

    if baseline.execution_time > 0 and current.execution_time > 0 {
        improvement_ratio = baseline.execution_time / current.execution_time;
        time_improvement = ((baseline.execution_time - current.execution_time) / baseline.execution_time) * 100;
    } else {
        improvement_ratio = 1.0;
        time_improvement = 0.0;
    }

    if baseline.memory_usage > 0 {
        memory_improvement = ((baseline.memory_usage - current.memory_usage) / baseline.memory_usage) * 100;
    } else {
        memory_improvement = 0.0;
    }

    is_better = improvement_ratio > 1.0 and current.memory_usage <= baseline.memory_usage;

    # Statistical significance via Welch's t-test approximation
    is_significant = False;
    confidence = 0.0;
    have_stats = (
        baseline_stdev > 0 and current_stdev > 0
        and baseline_n >= 2 and current_n >= 2
    );
    if have_stats {
        se_b = baseline_stdev / math.sqrt(baseline_n);
        se_c = current_stdev / math.sqrt(current_n);
        se_diff = math.sqrt(se_b ** 2 + se_c ** 2);
        if se_diff > 0 {
            t_stat = abs(baseline.execution_time - current.execution_time) / se_diff;
            numerator = (se_b ** 2 + se_c ** 2) ** 2;
            denominator = (se_b ** 4 / (baseline_n - 1)) + (se_c ** 4 / (current_n - 1));
            df = numerator / denominator if denominator > 0 else 1.0;
            z = t_stat;
            if df < 30 {
                z = t_stat * (1 - 1 / (4 * df));
            }
            p_one_tail = 0.5 * math.erfc(z / math.sqrt(2));
            p_two_tail = 2 * p_one_tail;
            confidence = 1.0 - p_two_tail;
            is_significant = p_two_tail < 0.05;
        }
    }

    return {
        "improvement_ratio": improvement_ratio,
        "time_improvement": time_improvement,
        "memory_improvement": memory_improvement,
        "is_better": is_better,
        "is_significant": is_significant,
        "confidence": confidence
    };
}


def calculate_score(
    metrics: Metrics,
    criteria: dict,
    baseline_time: float = 0.0
) -> float {
    """Weighted score in [0.0, 1.0] based on metrics and optimization criteria."""
    total_weight = (
        criteria.get("performance_weight", 0.0) +
        criteria.get("code_quality_weight", 0.0) +
        criteria.get("functionality_weight", 0.0)
    );

    if total_weight == 0 {
        perf_weight = 1.0 / 3.0;
        code_weight = 1.0 / 3.0;
        func_weight = 1.0 / 3.0;
    } else {
        perf_weight = criteria.get("performance_weight", 0.0) / total_weight;
        code_weight = criteria.get("code_quality_weight", 0.0) / total_weight;
        func_weight = criteria.get("functionality_weight", 0.0) / total_weight;
    }

    if baseline_time > 0 and metrics.execution_time > 0 {
        speedup = baseline_time / metrics.execution_time;
        perf_score = min(1.0, speedup / 2.0);
    } else {
        max_time = 10.0;
        perf_score = max(0.0, 1.0 - (metrics.execution_time / max_time));
    }

    max_complexity = 50.0;
    if metrics.code_complexity is not None {
        quality_score = max(0.0, 1.0 - (metrics.code_complexity / max_complexity));
    } else {
        quality_score = 0.5;
    }

    if metrics.test_coverage is not None {
        func_score = min(metrics.test_coverage / 100.0, 1.0);
    } else {
        func_score = 0.5;
    }

    memory_penalty = 0.0;
    if metrics.memory_usage > 100.0 {
        memory_penalty = min(0.1, (metrics.memory_usage - 100.0) / 1000.0);
    }

    weighted_score = (
        perf_weight * perf_score +
        code_weight * quality_score +
        func_weight * func_score
    ) - memory_penalty;

    return max(0.0, min(1.0, weighted_score));
}
