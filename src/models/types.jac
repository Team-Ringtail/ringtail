"""Shared data models for the Ringtail optimization system."""

import from typing { Optional, List, Any }


obj Metrics {
    has execution_time: float;
    has memory_usage: float;
    has cpu_usage: Optional[float] = None;
    has code_complexity: Optional[int] = None;
    has test_coverage: Optional[float] = None;
}


obj ProfileResult {
    has median_ms: float;
    has mean_ms: float;
    has min_ms: float;
    has max_ms: float;
    has stdev_ms: float;
    has iqr_ms: float = 0.0;
    has q1_ms: float = 0.0;
    has q3_ms: float = 0.0;
    has peak_memory_kb: float = 0.0;
    has rounds: int = 0;
    has outliers: str = "";
    has success: bool = True;
    has error: str = "";
}


obj LineProfile {
    has lineno: int;
    has cpu_percent: float;
    has memory_mb: float;
    has python_fraction: float;
}


obj DetailedProfile {
    has line_profiles: list = [];
    has hotspots: list = [];
    has python_vs_native_ratio: float = 1.0;
    has total_cpu_seconds: float = 0.0;
    has total_memory_mb: float = 0.0;
    has success: bool = True;
    has error: str = "";
}


obj FunctionInput {
    has source_code: str;
    has function_name: str;
    has language: str = "python";
    has test_cases: Optional[list] = None;
}


obj OptimizationPlan {
    has analysis: str;
    has optimization_strategy: str;
    has estimated_improvement: float;
    has target_metrics: Optional[Metrics] = None;
}


obj ConvergenceStatus {
    has should_continue: bool;
    has reason: str;
    has converged: bool;
}


obj OptimizationResult {
    has optimized_code: str;
    has iteration_number: int;
    has metrics: Metrics;
    has test_passed: bool;
    has improvement_ratio: float;
}
