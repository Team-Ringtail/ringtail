"""
Metrics aggregation and comparison utilities.

Pure Jac implementation; takes Metrics (obj) and returns dicts where the loop expects them.
"""

import from src.models.types { Metrics };


def aggregate_metrics(metrics_list: list) -> Metrics {
    if metrics_list is None or len(metrics_list) == 0 {
        return Metrics(execution_time=0.0, memory_usage=0.0);
    }

    sum_time = 0.0;
    sum_mem = 0.0;
    for m in metrics_list {
        sum_time = sum_time + m.execution_time;
        sum_mem = sum_mem + m.memory_usage;
    }
    n = len(metrics_list);
    avg_time = sum_time / float(n);
    avg_mem = sum_mem / float(n);

    cpu_vals: list = [];
    complexity_vals: list = [];
    coverage_vals: list = [];
    for m in metrics_list {
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

    avg_cpu: float | None = None;
    if len(cpu_vals) > 0 {
        s = 0.0;
        for v in cpu_vals { s = s + v; }
        avg_cpu = s / float(len(cpu_vals));
    }
    avg_complexity: int | None = None;
    if len(complexity_vals) > 0 {
        s = 0;
        for v in complexity_vals { s = s + v; }
        avg_complexity = int(float(s) / float(len(complexity_vals)));
    }
    avg_coverage: float | None = None;
    if len(coverage_vals) > 0 {
        s = 0.0;
        for v in coverage_vals { s = s + v; }
        avg_coverage = s / float(len(coverage_vals));
    }

    return Metrics(
        execution_time=avg_time,
        memory_usage=avg_mem,
        cpu_usage=avg_cpu,
        code_complexity=avg_complexity,
        test_coverage=avg_coverage
    );
}


def compare_metrics(baseline: Metrics, current: Metrics) -> dict {
    improvement_ratio = 1.0;
    time_improvement = 0.0;
    if baseline.execution_time > 0 {
        improvement_ratio = baseline.execution_time / current.execution_time;
        time_improvement = ((baseline.execution_time - current.execution_time) / baseline.execution_time) * 100.0;
    }

    memory_improvement = 0.0;
    if baseline.memory_usage > 0 {
        memory_improvement = ((baseline.memory_usage - current.memory_usage) / baseline.memory_usage) * 100.0;
    }

    is_better = improvement_ratio > 1.0 and current.memory_usage <= baseline.memory_usage;

    return {
        "improvement_ratio": improvement_ratio,
        "time_improvement": time_improvement,
        "memory_improvement": memory_improvement,
        "is_better": is_better
    };
}


def calculate_score(metrics: Metrics, criteria: dict) -> float {
    total_weight = float(criteria.get("performance_weight", 0.0) + criteria.get("code_quality_weight", 0.0) + criteria.get("functionality_weight", 0.0));

    perf_weight = 1.0 / 3.0;
    code_weight = 1.0 / 3.0;
    func_weight = 1.0 / 3.0;
    if total_weight > 0 {
        perf_weight = float(criteria.get("performance_weight", 0.0)) / total_weight;
        code_weight = float(criteria.get("code_quality_weight", 0.0)) / total_weight;
        func_weight = float(criteria.get("functionality_weight", 0.0)) / total_weight;
    }

    max_time = 10.0;
    perf_score = 1.0 - (metrics.execution_time / max_time);
    if perf_score < 0.0 { perf_score = 0.0; }

    quality_score = 0.5;
    if metrics.code_complexity is not None {
        max_complexity = 50.0;
        quality_score = 1.0 - (float(metrics.code_complexity) / max_complexity);
        if quality_score < 0.0 { quality_score = 0.0; }
    }

    func_score = 0.5;
    if metrics.test_coverage is not None {
        func_score = metrics.test_coverage / 100.0;
    }

    return perf_weight * perf_score + code_weight * quality_score + func_weight * func_score;
}
