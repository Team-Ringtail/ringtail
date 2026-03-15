"""
Optimizer Agent — Jac implementation.

This module mirrors the Python reference in `optimizer_agent_ref.py` and
exposes a stable contract used by the optimization loop:

  - think_and_prep(source_code, criteria, function_call, test_cases, analysis_mode?, llm_model?, feedback?) -> dict
      Returns an optimization plan dict. Dispatches to heuristic or LLM based on
      analysis_mode (e.g. "heuristic" | "llm") or llm_model (non-empty = use LLM).

  - write_optimized_code(source_code: str, plan: dict, llm_model?: str) -> str
      Returns the new code string only (no side effects).

  - compare(profiler_metrics: dict, plan: dict) -> dict
      Returns {"signal": "continue" | "done", "reason": str} based on metrics
      vs. the plan (no hard dependency on loop policy).
"""

import os;
import sys;
import traceback;
import from typing { Any }
import from src.utils.llm_client { analyze_and_plan, generate_optimized_code }

def _safe_log(callable: Any) -> None {
    # Best-effort logging: never let logging failures affect optimization.
    # TODO: Once RunLog is ported to Jac, replace this with typed logging calls.
    try { callable(); } except Exception { ; }
}

glob _TEST_MOCK_MODEL = "__ringtail_test_mock__";


"""Deterministic test-only optimizer used by local/unit profiles."""
def _mock_analyze_and_plan(
    source_code: str,
    criteria: dict,
    feedback: dict | None = None
) -> dict {
    lines = source_code.split("\n");
    num_lines = len(lines);
    code_lower = source_code.lower();

    # Keep mock plans stable so tests exercise orchestration, not model quality.
    num_for = _count_substring(code_lower, "for ");
    num_while = _count_substring(code_lower, "while ");
    num_loops = num_for + num_while;
    base_time = 0.05;
    per_loop_time = 0.02;
    raw_estimate = base_time + per_loop_time * num_loops;
    estimated_time_sec = raw_estimate * 0.8;
    estimated_memory_mb = 10.0;

    steps = [];
    if num_loops > 0 {
        steps = ["mock reduce loop overhead", "mock cache repeated work", "mock avoid redundant iterations"];
    } else {
        steps = ["mock preserve behavior", "mock keep structure stable"];
    }
    if num_lines > 50 {
        steps.append("mock split large functions");
    }

    candidate_plans = [
        {
            "label": "loop-overhead",
            "steps": ["Reduce loop overhead", "Avoid redundant iterations"]
        },
        {
            "label": "cache-repeated-work",
            "steps": ["Consider caching repeated work", "Precompute reusable values"]
        },
        {
            "label": "clarity-preserving",
            "steps": list(steps)
        }
    ];

    return {
        "backend": "mock",
        "analysis": "mock optimizer plan for deterministic tests",
        "estimated_time_sec": estimated_time_sec,
        "estimated_memory_mb": estimated_memory_mb,
        "steps": steps,
        "num_lines": num_lines,
        "num_loops": num_loops,
        "criteria": criteria,
        "candidate_plans": candidate_plans
    };
}

def _mock_generate_optimized_code(source_code: str, plan: dict) -> str {
    return source_code;
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

"""LLM-backed analysis via Anthropic Claude (Jac client)."""
def _think_and_prep_llm(
    source_code: str,
    criteria: dict,
    function_call: str,
    test_cases: list,
    llm_model: str | None = None,
    feedback: dict | None = None,
    run_log: Any = None
) -> dict {
    try {
        kwargs = {};
        if llm_model is not None and llm_model != "" {
            kwargs["model"] = llm_model;
        }
        if feedback is not None {
            kwargs["feedback"] = feedback;
        }
        if run_log is not None {
            kwargs["run_log"] = run_log;
        }
        plan = analyze_and_plan(
            source_code,
            criteria,
            function_call,
            test_cases,
            **kwargs
        );
        return plan;
    } except Exception as e {
        print("[optimizer_agent] LLM plan failed: " + str(e));
        traceback.print_exc();
        if run_log is not None {
            _safe_log(lambda: run_log.error("LLM plan failed", phase="think_and_prep", error=str(e)));
        }
        raise e;
    }
}

"""Think/prep phase: analyze input function and produce an optimization plan/estimate."""
def:pub think_and_prep(
    source_code: str,
    criteria: dict,
    function_call: str,
    test_cases: list,
    analysis_mode: str | None = None,
    llm_model: str | None = None,
    feedback: dict | None = None,
    run_log: Any = None
) -> dict {
    if llm_model is not None and llm_model == _TEST_MOCK_MODEL {
        return _mock_analyze_and_plan(source_code, criteria, feedback);
    }
    if analysis_mode is not None and analysis_mode == "mock" {
        return _mock_analyze_and_plan(source_code, criteria, feedback);
    }
    use_llm = (llm_model is not None and llm_model != "") or (analysis_mode is not None and analysis_mode == "llm");
    if use_llm {
        return _think_and_prep_llm(
            source_code,
            criteria,
            function_call,
            test_cases,
            llm_model,
            feedback,
            run_log
        );
    }
    raise ValueError("No optimizer backend configured. Use an LLM-backed profile or the explicit test mock backend.");
}


def:pub enumerate_candidate_plans(
    plan: dict,
    max_candidates: int = 1
) -> list {
    candidates = [];
    nested = plan.get("candidate_plans", []);

    if nested is not None and len(nested) > 0 {
        i = 0;
        while i < len(nested) and len(candidates) < max_candidates {
            candidate = dict(plan);
            nested_plan = nested[i];
            candidate["candidate_plans"] = [];
            candidate["label"] = nested_plan.get("label", "candidate_" + str(i));
            candidate["steps"] = nested_plan.get("steps", plan.get("steps", []));
            candidates.append(candidate);
            i = i + 1;
        }
    }

    if len(candidates) == 0 {
        fallback = dict(plan);
        fallback["label"] = str(plan.get("label", "candidate_0"));
        candidates.append(fallback);
    }

    return candidates;
}

"""Write phase: apply or generate the optimized code based on the plan.

Uses the Anthropic LLM for production plans and an explicit mock backend for
deterministic test profiles.
"""
def write_optimized_code(
    source_code: str,
    plan: dict,
    llm_model: str | None = None,
    run_log: Any = None
) -> str {
    if plan.get("backend", "") == "mock" {
        return _mock_generate_optimized_code(source_code, plan);
    }

    has_llm_plan = plan.get("analysis", None) is not None;
    if not has_llm_plan {
        raise ValueError("Refusing to generate code from a non-LLM, non-mock plan.");
    }

    try {
        kwargs = {};
        if llm_model is not None and llm_model != "" {
            kwargs["model"] = llm_model;
        }
        if run_log is not None {
            kwargs["run_log"] = run_log;
        }
        return generate_optimized_code(source_code, plan, **kwargs);
    } except Exception as e {
        print("[optimizer_agent] LLM code gen failed: " + str(e));
        traceback.print_exc();
        if run_log is not None {
            _safe_log(lambda: run_log.error("LLM code gen failed", phase="write_optimized_code", error=str(e)));
        }
        raise e;
    }
}

"""Compare phase: evaluate profiler output against the estimated target, return continue/done signal."""
def compare(
    profiler_metrics: dict,
    plan: dict
) -> dict {
    return _evaluate_against_plan(profiler_metrics, plan);
}
