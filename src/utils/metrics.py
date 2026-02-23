"""
Metrics aggregation and comparison utilities.

Pure Python functions for comparing and aggregating performance metrics.
"""

from typing import List, Dict, Any
from src.models.types import Metrics


def aggregate_metrics(metrics_list: List[Metrics]) -> Metrics:
    """
    Aggregate a list of Metrics instances into a single Metrics with averages/statistics.
    
    Args:
        metrics_list: List of Metrics dataclass instances
    
    Returns:
        Aggregated Metrics with averages/statistics
    """
    if not metrics_list:
        # Return default metrics if empty list
        return Metrics(execution_time=0.0, memory_usage=0.0)
    
    # Calculate averages for required fields
    avg_execution_time = sum(m.execution_time for m in metrics_list) / len(metrics_list)
    avg_memory_usage = sum(m.memory_usage for m in metrics_list) / len(metrics_list)
    
    # Calculate averages for optional fields (only if present)
    cpu_usages = [m.cpu_usage for m in metrics_list if m.cpu_usage is not None]
    avg_cpu_usage = sum(cpu_usages) / len(cpu_usages) if cpu_usages else None
    
    complexities = [m.code_complexity for m in metrics_list if m.code_complexity is not None]
    avg_complexity = int(sum(complexities) / len(complexities)) if complexities else None
    
    coverages = [m.test_coverage for m in metrics_list if m.test_coverage is not None]
    avg_coverage = sum(coverages) / len(coverages) if coverages else None
    
    return Metrics(
        execution_time=avg_execution_time,
        memory_usage=avg_memory_usage,
        cpu_usage=avg_cpu_usage,
        code_complexity=avg_complexity,
        test_coverage=avg_coverage
    )


def compare_metrics(baseline: Metrics, current: Metrics) -> Dict[str, Any]:
    """
    Compare two Metrics instances to determine improvement.
    
    Args:
        baseline: Baseline Metrics (original/previous version)
        current: Current Metrics (optimized version)
    
    Returns:
        Dictionary with:
        - improvement_ratio: float - Performance improvement (1.0 = no change, >1.0 = faster)
        - time_improvement: float - Time improvement percentage
        - memory_improvement: float - Memory improvement percentage
        - is_better: bool - Overall improvement indicator
    """
    # Calculate time improvement ratio (higher is better/faster)
    if baseline.execution_time > 0:
        improvement_ratio = baseline.execution_time / current.execution_time
        time_improvement = ((baseline.execution_time - current.execution_time) / baseline.execution_time) * 100
    else:
        improvement_ratio = 1.0
        time_improvement = 0.0
    
    # Calculate memory improvement (lower is better)
    if baseline.memory_usage > 0:
        memory_improvement = ((baseline.memory_usage - current.memory_usage) / baseline.memory_usage) * 100
    else:
        memory_improvement = 0.0
    
    # Overall improvement: better if faster AND using less/equal memory
    is_better = improvement_ratio > 1.0 and current.memory_usage <= baseline.memory_usage
    
    return {
        "improvement_ratio": improvement_ratio,
        "time_improvement": time_improvement,
        "memory_improvement": memory_improvement,
        "is_better": is_better
    }


def calculate_score(metrics: Metrics, criteria: Dict[str, Any]) -> float:
    """
    Calculate weighted score based on metrics and optimization criteria.
    
    Args:
        metrics: Metrics dataclass instance
        criteria: Dictionary with weights (from OptimizationCriteria node)
            Expected keys: performance_weight, code_quality_weight, functionality_weight
    
    Returns:
        Weighted score (float)
    """
    # Normalize weights (ensure they sum to 1.0)
    total_weight = (
        criteria.get("performance_weight", 0.0) +
        criteria.get("code_quality_weight", 0.0) +
        criteria.get("functionality_weight", 0.0)
    )
    
    if total_weight == 0:
        # Default equal weights if not specified
        perf_weight = code_weight = func_weight = 1.0 / 3.0
    else:
        perf_weight = criteria.get("performance_weight", 0.0) / total_weight
        code_weight = criteria.get("code_quality_weight", 0.0) / total_weight
        func_weight = criteria.get("functionality_weight", 0.0) / total_weight
    
    # Performance score (inverse of execution time - lower is better)
    # Normalize to 0-1 scale (assuming reasonable max time)
    max_time = 10.0  # Assume max 10 seconds for normalization
    perf_score = max(0.0, 1.0 - (metrics.execution_time / max_time))
    
    # Code quality score (inverse of complexity - lower is better)
    # Normalize complexity (assuming max complexity of 50)
    max_complexity = 50.0
    if metrics.code_complexity is not None:
        quality_score = max(0.0, 1.0 - (metrics.code_complexity / max_complexity))
    else:
        quality_score = 0.5  # Neutral if not measured
    
    # Functionality score (test coverage if available, otherwise neutral)
    if metrics.test_coverage is not None:
        func_score = metrics.test_coverage / 100.0  # Convert percentage to 0-1
    else:
        func_score = 0.5  # Neutral if not measured
    
    # Weighted sum
    weighted_score = (
        perf_weight * perf_score +
        code_weight * quality_score +
        func_weight * func_score
    )
    
    return weighted_score
