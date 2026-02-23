"""
Optimizer Agent — analysis and transformation pipeline (no byllm; stubs/heuristics).

Interface for optimization_loop.jac (spawn walker with has-params; read report for result):

  1. think_and_prep
     - Inputs: source_code: str, criteria: dict (optional, e.g. performance_weight, ...)
     - Report: plan dict with keys:
       - estimated_time_sec: float
       - estimated_memory_mb: float
       - steps: list[str]
       - num_lines, num_loops: int
       - criteria: dict (echo)

  2. write_optimized_code
     - Inputs: source_code: str, plan: dict (from think_and_prep)
     - Report: optimized code string

  3. compare
     - Inputs: profiler_metrics: dict (e.g. execution_time_sec, memory_mb), plan: dict
     - Report: { "signal": "continue" | "done", "reason": str }
"""

# ---- Think/Prep: analyze input function and produce an optimization plan ----
walker think_and_prep {
    has source_code: str;
    has criteria: dict = {};  # e.g. performance_weight, code_quality_weight, functionality_weight

    with entry {
        # Heuristic analysis (no LLM): infer structure and estimate targets
        plan = _analyze_and_plan(source_code, criteria);
        report plan;
    }
}

# ---- Write: apply or generate optimized code based on the plan ----
walker write_optimized_code {
    has source_code: str;
    has plan: dict;

    with entry {
        optimized = _apply_plan_to_code(source_code, plan);
        report optimized;
    }
}

# ---- Compare: evaluate profiler output vs estimated target; return continue/done ----
walker compare {
    has profiler_metrics: dict;  # e.g. { "execution_time_sec": float, "memory_mb": float }
    has plan: dict;             # from think_and_prep (has estimated_time_sec, estimated_memory_mb, etc.)

    with entry {
        result = _evaluate_against_plan(profiler_metrics, plan);
        report result;
    }
}

# ---- Stub/heuristic helpers (private) ----

def _analyze_and_plan(source_code: str, criteria: dict) -> dict {
    """
    Analyze code with simple heuristics; produce a plan with estimated targets.
    """
    lines = source_code.split("\n");
    num_lines = len(lines);
    code_lower = source_code.lower();

    # Count loops (crude heuristic for "complexity")
    num_for = _count_substring(code_lower, "for ");
    num_while = _count_substring(code_lower, "while ");
    num_loops = num_for + num_while;

    # Stub: estimate target time (e.g. 0.05s base + 0.02s per loop, aim to cut by 20%)
    base_time = 0.05;
    per_loop_time = 0.02;
    raw_estimate = base_time + per_loop_time * num_loops;
    estimated_time_sec = raw_estimate * 0.8;  # target: 20% faster
    estimated_memory_mb = 10.0;  # stub

    # Build steps list (stub suggestions)
    steps = [];
    if num_loops > 0 {
        steps = ["Reduce loop overhead", "Consider caching repeated work", "Avoid redundant iterations"];
    } else {
        steps = ["Code is simple; consider micro-optimizations or clarity improvements"];
    }
    if num_lines > 50 {
        steps.append("Consider splitting into smaller functions");
    }

    return {
        "estimated_time_sec": estimated_time_sec,
        "estimated_memory_mb": estimated_memory_mb,
        "steps": steps,
        "num_lines": num_lines,
        "num_loops": num_loops,
        "criteria": criteria
    };
}

def _apply_plan_to_code(source_code: str, plan: dict) -> str {
    """
    Apply plan to code (stub: minimal transformation so loop can test wiring).
    """
    steps = plan.get("steps", []);
    if len(steps) == 0 {
        return source_code + "\n# [optimizer stub] no steps\n";
    }
    # Stub: prepend a comment summarizing the plan; no real code change yet
    header = "# [optimizer stub] plan steps: " + ", ".join(steps) + "\n";
    return header + source_code;
}

def _evaluate_against_plan(profiler_metrics: dict, plan: dict) -> dict {
    """
    Compare profiler output to plan estimates; return continue or done with reason.
    """
    actual_time = float(profiler_metrics.get("execution_time_sec", 999999.0));
    target_time = float(plan.get("estimated_time_sec", 0.0));
    # Allow 10% slack: done if within 1.1x of target
    tolerance = 1.1;
    threshold = target_time * tolerance;

    if target_time <= 0 {
        return {"signal": "done", "reason": "no time target set"};
    } elif actual_time <= threshold {
        return {"signal": "done", "reason": "execution time within target"};
    } else {
        return {"signal": "continue", "reason": "execution time above target; iterate"};
    }
}

def _count_substring(s: str, sub: str) -> int {
    """Count non-overlapping occurrences of sub in s."""
    count = 0;
    start = 0;
    sub_len = len(sub);
    while start <= len(s) - sub_len {
        if s[start:start+sub_len] == sub {
            count = count + 1;
            start = start + sub_len;
        } else {
            start = start + 1;
        }
    }
    return count;
}
