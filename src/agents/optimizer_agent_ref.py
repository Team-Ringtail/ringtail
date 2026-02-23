"""
Optimizer Agent — Python reference implementation.

This module mirrors the logic in optimizer_agent.jac so the team can read and
reason about the agent in Python. The Jaseci version uses the same algorithms;
here we expose plain functions that match the walker interface:

  1. think_and_prep(source_code, criteria) -> plan dict
  2. write_optimized_code(source_code, plan) -> optimized code str
  3. compare(profiler_metrics, plan) -> {"signal": "continue"|"done", "reason": str}

No byllm — stubs and simple heuristics only.
"""

from __future__ import annotations


def _count_substring(s: str, sub: str) -> int:
    """Count non-overlapping occurrences of sub in s."""
    count = 0
    start = 0
    sub_len = len(sub)
    while start <= len(s) - sub_len:
        if s[start : start + sub_len] == sub:
            count += 1
            start += sub_len
        else:
            start += 1
    return count


def _analyze_and_plan(source_code: str, criteria: dict) -> dict:
    """
    Analyze code with simple heuristics; produce a plan with estimated targets.
    """
    lines = source_code.split("\n")
    num_lines = len(lines)
    code_lower = source_code.lower()

    # Count loops (crude heuristic for "complexity")
    num_for = _count_substring(code_lower, "for ")
    num_while = _count_substring(code_lower, "while ")
    num_loops = num_for + num_while

    # Stub: estimate target time (e.g. 0.05s base + 0.02s per loop, aim to cut by 20%)
    base_time = 0.05
    per_loop_time = 0.02
    raw_estimate = base_time + per_loop_time * num_loops
    estimated_time_sec = raw_estimate * 0.8  # target: 20% faster
    estimated_memory_mb = 10.0  # stub

    # Build steps list (stub suggestions)
    if num_loops > 0:
        steps = [
            "Reduce loop overhead",
            "Consider caching repeated work",
            "Avoid redundant iterations",
        ]
    else:
        steps = ["Code is simple; consider micro-optimizations or clarity improvements"]
    if num_lines > 50:
        steps.append("Consider splitting into smaller functions")

    return {
        "estimated_time_sec": estimated_time_sec,
        "estimated_memory_mb": estimated_memory_mb,
        "steps": steps,
        "num_lines": num_lines,
        "num_loops": num_loops,
        "criteria": criteria,
    }


def _apply_plan_to_code(source_code: str, plan: dict) -> str:
    """
    Apply plan to code (stub: minimal transformation so loop can test wiring).
    """
    steps = plan.get("steps", [])
    if len(steps) == 0:
        return source_code + "\n# [optimizer stub] no steps\n"
    header = "# [optimizer stub] plan steps: " + ", ".join(steps) + "\n"
    return header + source_code


def _evaluate_against_plan(profiler_metrics: dict, plan: dict) -> dict:
    """
    Compare profiler output to plan estimates; return continue or done with reason.
    """
    actual_time = float(profiler_metrics.get("execution_time_sec", 999_999.0))
    target_time = float(plan.get("estimated_time_sec", 0.0))
    tolerance = 1.1
    threshold = target_time * tolerance

    if target_time <= 0:
        return {"signal": "done", "reason": "no time target set"}
    if actual_time <= threshold:
        return {"signal": "done", "reason": "execution time within target"}
    return {"signal": "continue", "reason": "execution time above target; iterate"}


# --- Public interface (matches Jac walkers) ---


def think_and_prep(source_code: str, criteria: dict | None = None) -> dict:
    """
    Think/prep phase: analyze input function and produce an optimization plan.

    Args:
        source_code: Raw source code of the function to optimize.
        criteria: Optional dict (e.g. performance_weight, code_quality_weight).

    Returns:
        Plan dict with estimated_time_sec, estimated_memory_mb, steps, num_lines,
        num_loops, and criteria.
    """
    criteria = criteria or {}
    return _analyze_and_plan(source_code, criteria)


def write_optimized_code(source_code: str, plan: dict) -> str:
    """
    Write phase: apply or generate optimized code based on the plan.

    Args:
        source_code: Original source code.
        plan: Plan from think_and_prep.

    Returns:
        Optimized code string (stub: currently just adds a comment with plan steps).
    """
    return _apply_plan_to_code(source_code, plan)


def compare(profiler_metrics: dict, plan: dict) -> dict:
    """
    Compare phase: evaluate profiler output against the estimated target.

    Args:
        profiler_metrics: Dict with at least execution_time_sec (and optionally memory_mb).
        plan: Plan from think_and_prep (contains estimated_time_sec, etc.).

    Returns:
        {"signal": "continue" | "done", "reason": str}
    """
    return _evaluate_against_plan(profiler_metrics, plan)


if __name__ == "__main__":
    # Quick demo so you can run: python -m src.agents.optimizer_agent_ref
    sample = """
def slow_sum(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i + j
    return total
""".strip()

    print("1. think_and_prep(sample, {})")
    plan = think_and_prep(sample, {})
    for k, v in plan.items():
        print(f"   {k}: {v}")

    print("\n2. write_optimized_code(sample, plan) -> first 3 lines:")
    out = write_optimized_code(sample, plan)
    for line in out.split("\n")[:3]:
        print(f"   {line}")

    print("\n3. compare(profiler_metrics, plan)")
    # Simulate profiler saying it took 0.04s (under target)
    result = compare({"execution_time_sec": 0.04}, plan)
    print(f"   {result}")
    # Simulate profiler saying it took 1.0s (over target)
    result2 = compare({"execution_time_sec": 1.0}, plan)
    print(f"   (if time was 1.0s) {result2}")
