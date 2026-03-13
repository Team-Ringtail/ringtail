"""
Metrics aggregation and comparison utilities.

Pure Jac implementation; takes Metrics (obj) and returns dicts where the loop expects them.
"""

import math;
import from src.models.types { Metrics }


def aggregate_metrics(metrics_list: list) -> Metrics {
    if metrics_list is None or len(metrics_list) == 0 {
        return Metrics(execution_time=0.0, memory_usage=0.0);
    }

    sum_time = 0.0;
    sum_mem = 0.0;
    cpu_vals: list = [];
    complexity_vals: list = [];
    coverage_vals: list = [];

    for m in metrics_list {
        sum_time = sum_time + m.execution_time;
        sum_mem = sum_mem + m.memory_usage;

        if m.cpu_usage is not None {
            cpu_vals.append(m.cpu_usage);
        }
        if m.code_complexity is not None {
            complexity_vals.append(m.code_complexity);
        }
        if m.test_coverage is not None {
            coverage_vals.append(m.test_coverage);
        }
    }

    n = len(metrics_list);
    avg_time = sum_time / float(n);
    avg_mem = sum_mem / float(n);

    avg_cpu: float | None = None;
    if len(cpu_vals) > 0 {
        s = 0.0;
        for v in cpu_vals { s = s + v; }
        avg_cpu = s / float(len(cpu_vals));
    }

    avg_complexity: int | None = None;
    if len(complexity_vals) > 0 {
        s2 = 0;
        for v in complexity_vals { s2 = s2 + v; }
        avg_complexity = int(float(s2) / float(len(complexity_vals)));
    }

    avg_coverage: float | None = None;
    if len(coverage_vals) > 0 {
        s3 = 0.0;
        for v in coverage_vals { s3 = s3 + v; }
        avg_coverage = s3 / float(len(coverage_vals));
    }

    return Metrics(
        execution_time=avg_time,
        memory_usage=avg_mem,
        cpu_usage=avg_cpu,
        code_complexity=avg_complexity,
        test_coverage=avg_coverage
    );
}
"""Compare two Metrics instances, with optional statistical data for significance."""
def compare_metrics(
    baseline: Metrics,
    current: Metrics,
    baseline_stdev: float = 0.0,
    current_stdev: float = 0.0,
    baseline_n: int = 0,
    current_n: int = 0
) -> dict {
    # Time-based improvement
    improvement_ratio = 1.0;
    time_improvement = 0.0;
    if baseline.execution_time > 0.0 and current.execution_time > 0.0 {
        improvement_ratio = baseline.execution_time / current.execution_time;
        time_improvement = ((baseline.execution_time - current.execution_time) / baseline.execution_time) * 100.0;
    }

    # Memory improvement
    memory_improvement = 0.0;
    if baseline.memory_usage > 0.0 {
        memory_improvement = ((baseline.memory_usage - current.memory_usage) / baseline.memory_usage) * 100.0;
    }

    is_better = improvement_ratio > 1.0 and current.memory_usage <= baseline.memory_usage;

    # Statistical significance via Welch's t-test approximation
    is_significant = False;
    confidence = 0.0;
    have_stats = (
        baseline_stdev > 0.0 and current_stdev > 0.0
        and baseline_n >= 2 and current_n >= 2
    );
    if have_stats {
        se_b = baseline_stdev / math.sqrt(float(baseline_n));
        se_c = current_stdev / math.sqrt(float(current_n));
        se_diff = math.sqrt(se_b ** 2 + se_c ** 2);
        if se_diff > 0.0 {
            t_stat = math.fabs(baseline.execution_time - current.execution_time) / se_diff;
            numerator = (se_b ** 2 + se_c ** 2) ** 2;
            denominator = (se_b ** 4 / float(baseline_n - 1)) + (se_c ** 4 / float(current_n - 1));
            df = numerator / denominator if denominator > 0.0 else 1.0;
            z = t_stat;
            if df < 30.0 {
                z = t_stat * (1.0 - 1.0 / (4.0 * df));
            }
            p_one_tail = 0.5 * math.erfc(z / math.sqrt(2.0));
            p_two_tail = 2.0 * p_one_tail;
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
    total_weight = (
        criteria.get("performance_weight", 0.0) +
        criteria.get("code_quality_weight", 0.0) +
        criteria.get("functionality_weight", 0.0)
    );

    if total_weight == 0.0 {
        perf_weight = 1.0 / 3.0;
        code_weight = 1.0 / 3.0;
        func_weight = 1.0 / 3.0;
    } else {
        perf_weight = criteria.get("performance_weight", 0.0) / total_weight;
        code_weight = criteria.get("code_quality_weight", 0.0) / total_weight;
        func_weight = criteria.get("functionality_weight", 0.0) / total_weight;
    }

    # Performance: prefer speedups over baseline when provided, otherwise absolute time
    if baseline_time > 0.0 and metrics.execution_time > 0.0 {
        speedup = baseline_time / metrics.execution_time;
        perf_score = speedup / 2.0;
        if perf_score > 1.0 { perf_score = 1.0; }
    } else {
        max_time = 10.0;
        perf_score = 1.0 - (metrics.execution_time / max_time);
        if perf_score < 0.0 { perf_score = 0.0; }
    }

    # Code quality: lower complexity is better
    max_complexity = 50.0;
    if metrics.code_complexity is not None {
        quality_score = 1.0 - (float(metrics.code_complexity) / max_complexity);
        if quality_score < 0.0 { quality_score = 0.0; }
    } else {
        quality_score = 0.5;
    }

    # Functionality: coverage percentage
    if metrics.test_coverage is not None {
        func_score = float(metrics.test_coverage) / 100.0;
        if func_score > 1.0 { func_score = 1.0; }
    } else {
        func_score = 0.5;
    }

    # Memory penalty for very memory-heavy solutions
    memory_penalty = 0.0;
    if metrics.memory_usage > 100.0 {
        memory_penalty = (metrics.memory_usage - 100.0) / 1000.0;
        if memory_penalty > 0.1 { memory_penalty = 0.1; }
    }

    weighted_score = (
        perf_weight * perf_score +
        code_weight * quality_score +
        func_weight * func_score
    ) - memory_penalty;

    if weighted_score < 0.0 { weighted_score = 0.0; }
    if weighted_score > 1.0 { weighted_score = 1.0; }
    return weighted_score;
}
