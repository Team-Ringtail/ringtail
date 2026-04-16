from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceDecision:
    accepted: bool
    reasons: list[str]


def evaluate_hotspot_acceptance(
    *,
    tests_passed: bool,
    speedup: float | None,
    post_profile_completed: bool,
    min_speedup: float,
) -> AcceptanceDecision:
    reasons: list[str] = []
    if not tests_passed:
        reasons.append("snapshot or repo validation did not pass")
    if not post_profile_completed:
        reasons.append("post-optimization profiling did not complete")
    if speedup is None:
        reasons.append("no measured speedup was produced")
    elif speedup < min_speedup:
        reasons.append(
            f"measured speedup {speedup:.2f}x is below required {min_speedup:.2f}x threshold"
        )
    return AcceptanceDecision(accepted=not reasons, reasons=reasons)
