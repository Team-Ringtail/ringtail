"""
Shared data models for the Ringtail optimization system.

Metrics is an obj type used by the loop and metrics utilities.
FunctionInput, OptimizationPlan, ConvergenceStatus, OptimizationResult are
used as dict contracts (JSON-friendly) across the optimization loop and agents.

Dict contracts (documentation):

  FunctionInput (dict):
    - source_code: str (required)
    - function_call: str (required)
    - function_name: str (optional; derived by parse_function if empty)
    - language: str (default "python")
    - test_cases: list[dict] | None (optional). Each case: name?, call, expected?, raises?

  OptimizationPlan (dict, produced by think_and_prep):
    - estimated_time_sec: float, estimated_memory_mb: float, steps: list[str]
    - num_lines: int, num_loops: int, criteria: dict
    - language?: str, function_metadata?: dict, test_cases?: list[dict], analysis_agent?: str

  ConvergenceStatus (dict):
    - should_continue: bool, reason: str, converged: bool

  OptimizationResult (dict, per-iteration and final):
    - optimized_code: str, iteration_number: int, metrics: dict (Metrics shape)
    - test_passed: bool, improvement_ratio: float, error?: str
    - Final result may also include: baseline_metrics, termination_reason, converged
"""

obj Metrics {
    has execution_time: float;
    has memory_usage: float;
    has cpu_usage: float | None = None;
    has code_complexity: int | None = None;
    has test_coverage: float | None = None;
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
