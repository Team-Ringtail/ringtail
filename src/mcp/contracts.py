from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class McpError:
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


@dataclass(frozen=True)
class RecommendedTarget:
    id: str
    function: str
    file: str
    reason: str


@dataclass(frozen=True)
class HotspotSummary:
    id: str
    rank: int
    module: str
    function: str
    file: str
    line: int
    tottime: float
    cumtime: float
    ncalls: int
    hotness_pct: float
    ownership: str
    editable: bool
    worth_optimizing: bool
    skip_reason: str
    callers: list[str]
    callees: list[str]
    recommendation: str


@dataclass(frozen=True)
class ProfileReport:
    repo_path: str
    entry_point: str
    threshold_pct: float
    total_time: float
    functions_analyzed: int
    hot_function_count: int
    dag_levels: int
    editable_hotspot_count: int
    recommended_targets: list[RecommendedTarget]
    hotspots: list[HotspotSummary]
    message: str
    next_action: str
    kind: str = "profile_report"
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OptimizationAttemptSummary:
    attempt: int
    test_passed: bool
    error: str
    failure_count: int


@dataclass(frozen=True)
class ValidationSummary:
    accepted: bool
    tests_passed: bool
    post_profile_completed: bool
    attempt_count: int
    min_speedup_required: float
    acceptance_reasons: list[str]


@dataclass(frozen=True)
class OptimizationMetrics:
    baseline_function_time: float
    optimized_function_time: float | None
    function_speedup: float | None
    baseline_program_time: float | None
    optimized_program_time: float | None
    program_speedup: float | None


@dataclass(frozen=True)
class PatchArtifact:
    original_code: str
    optimized_code: str
    diff: str


@dataclass(frozen=True)
class OptimizationTarget:
    id: str
    module: str
    function: str
    file: str
    line: int
    tottime: float
    hotness_pct: float


@dataclass(frozen=True)
class HotspotOptimizationReport:
    repo_path: str
    entry_point: str
    hotspot_id: str
    target: OptimizationTarget
    validation: ValidationSummary
    metrics: OptimizationMetrics
    attempts: list[OptimizationAttemptSummary]
    patch: PatchArtifact
    message: str
    error: dict[str, str] | None = None
    kind: str = "hotspot_optimization"
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
