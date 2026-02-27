"""
Optimizer Agent — Jac implementation.

This module mirrors the Python reference in `optimizer_agent_ref.py` and
exposes a stable contract used by the optimization loop:

  - think_and_prep(source_code, criteria, function_call, test_cases, analysis_mode?, llm_model?) -> dict
      Returns an optimization plan dict. Dispatches to heuristic or LLM based on
      analysis_mode (e.g. "heuristic" | "llm") or llm_model (non-empty = use LLM).

  - write_optimized_code(source_code: str, plan: dict) -> str
      Returns the new code string only (no side effects).

  - compare(profiler_metrics: dict, plan: dict) -> dict
      Returns {"signal": "continue" | "done", "reason": str} based on metrics
      vs. the plan (no hard dependency on loop policy).
"""

import os;
import sys;
import traceback;

"""Analyze code with simple heuristics; produce a plan with estimated targets."""


def _analyze_and_plan(source_code: str, criteria: dict) -> dict {
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

"""Apply plan to code (stub: minimal transformation so loop can test wiring)."""
def _apply_plan_to_code(source_code: str, plan: dict) -> str {
    steps = plan.get("steps", []);
    if len(steps) == 0 {
        return source_code + "\n# [optimizer stub] no steps\n";
    }
    # Stub: prepend a comment summarizing the plan; no real code change yet
    header = "# [optimizer stub] plan steps: " + ", ".join(steps) + "\n";
    return header + source_code;
}

"""
Compare profiler output to plan estimates; return continue or done with reason.
"""
def _evaluate_against_plan(profiler_metrics: dict, plan: dict) -> dict {
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

"""Count non-overlapping occurrences of sub in s."""
def _count_substring(s: str, sub: str) -> int {
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

"""LLM-backed analysis via Anthropic Claude. Falls back to heuristic on error."""
def _think_and_prep_llm(source_code: str, criteria: dict, function_call: str, test_cases: list) -> dict {
    api_key = os.environ.get("RINGTAIL_ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "");
    if not api_key {
        print("[optimizer_agent] RINGTAIL_ANTHROPIC_API_KEY not set — falling back to heuristic");
        return _analyze_and_plan(source_code, criteria);
    }

    try {
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));
        if repo_root not in sys.path {
            sys.path.insert(0, repo_root);
        }
        import importlib;
        llm_mod = importlib.import_module("src.utils.llm_client");
        plan = llm_mod.analyze_and_plan(
            source_code,
            criteria,
            function_call,
            test_cases
        );
        return plan;
    } except Exception as e {
        print("[optimizer_agent] LLM call failed, falling back to heuristic: " + str(e));
        traceback.print_exc();
        return _analyze_and_plan(source_code, criteria);
    }
}

"""Think/prep phase: analyze input function and produce an optimization plan/estimate."""
def think_and_prep(
    source_code: str,
    criteria: dict,
    function_call: str,
    test_cases: list,
    analysis_mode: str | None = None,
    llm_model: str | None = None
) -> dict {
    use_llm = (llm_model is not None and llm_model != "") or (analysis_mode is not None and analysis_mode == "llm");
    if use_llm {
        return _think_and_prep_llm(source_code, criteria, function_call, test_cases);
    }
    return _analyze_and_plan(source_code, criteria);
}

"""Write phase: apply or generate the optimized code based on the plan.

Uses the Anthropic LLM if the plan came from an LLM analysis (detected by
the presence of an 'analysis' key). Falls back to heuristic stub otherwise.
"""
def write_optimized_code(
    source_code: str,
    plan: dict
) -> str {
    has_llm_plan = plan.get("analysis", None) is not None;
    api_key = os.environ.get("RINGTAIL_ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "");

    if has_llm_plan and api_key {
        try {
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));
            if repo_root not in sys.path {
                sys.path.insert(0, repo_root);
            }
            import importlib;
            llm_mod = importlib.import_module("src.utils.llm_client");
            return llm_mod.generate_optimized_code(source_code, plan);
        } except Exception as e {
            print("[optimizer_agent] LLM code gen failed, falling back to heuristic: " + str(e));
            traceback.print_exc();
        }
    }
    return _apply_plan_to_code(source_code, plan);
}

"""Compare phase: evaluate profiler output against the estimated target, return continue/done signal."""
def compare(
    profiler_metrics: dict,
    plan: dict
) -> dict {
    return _evaluate_against_plan(profiler_metrics, plan);
}
