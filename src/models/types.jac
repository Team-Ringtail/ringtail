"""
Shared data models for the Ringtail optimization system.
"""

obj Metrics {
    has execution_time: float;
    has memory_usage: float;
    has cpu_usage: float | None = None;
    has code_complexity: int | None = None;
    has test_coverage: float | None = None;
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


obj TestCase {
    has call: str;
    has name: str | None = None;
    has expected: any | None = None;
    has raises: str | None = None;
}


obj FunctionInput {
    has source_code: str;
    has function_call: str;
    has function_name: str | None = None;
    has language: str = "python";
    has test_cases: list | None = None;  # list[TestCase] when used structurally
    has analysis_mode: str | None = None;
    has extra: dict | None = None;
}


obj OptimizationPlan {
    has estimated_time_sec: float;
    has estimated_memory_mb: float;
    has steps: list = [];  # list[str]
    has num_lines: int = 0;
    has num_loops: int = 0;
    has criteria: dict = {};
    has language: str | None = None;
    has function_metadata: dict | None = None;
    has test_cases: list | None = None;  # list[TestCase]
    has analysis_agent: str | None = None;
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
    has baseline_metrics: Metrics | None = None;
    has termination_reason: str | None = None;
    has converged: bool | None = None;
    has error: str | None = None;
}
