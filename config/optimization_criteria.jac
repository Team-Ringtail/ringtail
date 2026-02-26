"""
Default optimization criteria configuration
"""

node OptimizationCriteria {
    has name: str = "default";
    has performance_weight: float = 1.0;
    has code_quality_weight: float = 1.0;
    has functionality_weight: float = 1.0;
}
