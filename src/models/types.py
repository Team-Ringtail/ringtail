"""
Shared data models for the Ringtail optimization system.

These are Python dataclasses that can be used across the codebase.
Since Jac is a Python superset, these can be imported directly into Jac files.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class Metrics:
    """Performance and quality metrics for code execution."""
    execution_time: float  # Execution time in seconds
    memory_usage: float  # Memory usage in MB
    cpu_usage: Optional[float] = None  # CPU usage percentage (optional)
    code_complexity: Optional[int] = None  # Cyclomatic complexity score (optional)
    test_coverage: Optional[float] = None  # Test coverage percentage (optional)


@dataclass
class FunctionInput:
    """Represents input function to optimize."""
    source_code: str  # Raw function code as string
    function_name: str  # Name of the function
    language: str = "python"  # Programming language (default: "python")
    test_cases: Optional[List[Any]] = None  # Optional test cases for validation


@dataclass
class OptimizationPlan:
    """Agent's analysis and plan (from optimizer_agent)."""
    analysis: str  # Analysis of current code
    optimization_strategy: str  # Proposed optimization approach
    estimated_improvement: float  # Estimated performance improvement
    target_metrics: Optional[Metrics] = None  # Target metrics to achieve (optional)


@dataclass
class ConvergenceStatus:
    """Loop termination decision."""
    should_continue: bool  # Whether to continue iterating
    reason: str  # Reason for continue/stop decision
    converged: bool  # Whether optimization converged


@dataclass
class OptimizationResult:
    """Represents result of optimization iteration."""
    optimized_code: str  # Optimized function code
    iteration_number: int  # Current iteration count
    metrics: Metrics  # Performance and correctness metrics
    test_passed: bool  # Whether tests passed
    improvement_ratio: float  # Performance improvement vs baseline
