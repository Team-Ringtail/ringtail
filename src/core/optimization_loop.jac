"""
Core optimization loop implementation.

This walker orchestrates the optimization process by:
1. Parsing the input function
2. Computing baseline metrics (profile + complexity + coverage)
3. Iteratively calling optimizer_agent, profiler, and tester
4. Evaluating convergence with statistical significance checks
"""

import from config.optimization_criteria { OptimizationCriteria }
import from config.agent_config { AgentConfig, get_agent_config }
import from src.utils.code_parser { parse_function }
import from src.utils.metrics { compare_metrics, aggregate_metrics, calculate_score }
import from src.utils.complexity { compute_complexity }
import from src.models.types { FunctionInput, OptimizationResult, Metrics, OptimizationPlan, ConvergenceStatus }
import from src.core.tester { run_tests }
import from src.core.tester { run_tests_with_coverage }
import from src.core.profiler { profile_code }
import from src.core.property_tester { run_property_tests }
import from src.agents.optimizer_agent { think_and_prep, write_optimized_code, compare, enumerate_candidate_plans }

import importlib;
import from typing { Any }


# TODO: Port `src/utils/run_log.py` to Jac and remove this Python bridge.
def _maybe_create_run_log(function_input: dict, function_name: str) -> Any {
    try {
        enabled = function_input.get("enable_run_log", True);
        if enabled is None {
            enabled = True;
        }
        if not bool(enabled) {
            return None;
        }

        mod = importlib.import_module("src.utils.run_log");
        RunLog = getattr(mod, "RunLog", None);
        if RunLog is None {
            return None;
        }

        run_name = function_input.get("run_name", None);
        if run_name is None or str(run_name) == "" {
            if function_name is None or function_name == "" {
                run_name = "optimize";
            } else {
                run_name = "optimize-" + str(function_name);
            }
        }
        run_id = function_input.get("run_id", None);
        if run_id is not None and str(run_id) != "" {
            return RunLog(str(run_name), run_id=str(run_id));
        }
        return RunLog(str(run_name));
    } except Exception as e {
        print("[run_log] disabled (bridge failed): " + str(e));
        return None;
    }
}

def _safe_log(callable: Any) -> None {
    # Best-effort logging: never let logging failures affect optimization.
    # TODO: Once RunLog is ported to Jac, replace this with typed logging calls.
    try { callable(); } except Exception { ; }
}


def _with_run_metadata(result: dict, run_log: Any) -> dict {
    if run_log is None {
        return result;
    }
    result["run_id"] = getattr(run_log, "run_id", "");
    result["run_log_path"] = getattr(run_log, "log_path", "");
    return result;
}


"""Run the full optimization loop for a given function description.

Args:
    input: dict with at least:
        - source_code: str
        - function_name: str
        - function_call: str (expression used by the profiler)
        - test_cases: optional list of structured test case dicts
        - analysis_mode: optional str controlling agent behavior
          ("heuristic" | "llm"), forwarded to the optimizer agent
    criteria_name: optional named OptimizationCriteria profile (default: "default")
    config_name: optional named AgentConfig profile (default: "default")

Returns:
    A JSON-friendly dict shaped like OptimizationResult plus optional "error".
"""
def:pub run_optimization(
    input: dict,
    criteria_name: str | None = None,
    config_name: str | None = None
) -> dict {
    # Construct criteria/config nodes (profile selection via names)
    criteria = OptimizationCriteria();
    if criteria_name is not None {
        criteria.name = criteria_name;
    }

    config_profile_name = config_name;
    if config_profile_name is None {
        config_profile_name = "default";
    }
    config = get_agent_config(config_profile_name);
    requested_llm_model = input.get("llm_model", None);
    if requested_llm_model is not None and str(requested_llm_model) != "" {
        config.llm_model = str(requested_llm_model);
    }

    # Call core logic directly instead of going through a walker spawn.
    return _run_optimize(input, criteria, config);
}


"""Development helper: run optimization on a trivial example function.

This is intended for manual testing and for future unit tests, and is not
used by production interfaces (CLI, web, decorators).
"""
def:pub dev_optimize_example -> dict {
    sample_code = """
def slow_sum(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i + j
    return total
""";

    input = {
        "source_code": sample_code,
        "function_name": "slow_sum",
        "function_call": "slow_sum(10)",
        "test_cases": []
    };

    return run_optimization(input);
}


def _run_optimize(
    function_input: dict,
    criteria: OptimizationCriteria | None,
    config: AgentConfig | None
) -> dict {
    # Derive loop policy from config with safe fallbacks
    max_iterations = 3;
    max_no_improvement_iters = 3;
    stop_on_test_failure = True;
    min_improvement_ratio = 1.0;
    candidate_count = 1;
    benchmark_min_rounds = 10;
    benchmark_warmup = True;
    property_test_max_examples = 50;
    enable_property_tests = True;

    if config is not None {
        if config.max_iterations is not None {
            max_iterations = int(config.max_iterations);
        }
        if config.max_no_improvement_iters is not None {
            max_no_improvement_iters = int(config.max_no_improvement_iters);
        }
        if config.benchmark_min_rounds is not None {
            benchmark_min_rounds = int(config.benchmark_min_rounds);
        }
        if config.benchmark_warmup is not None {
            benchmark_warmup = bool(config.benchmark_warmup);
        }
        if config.property_test_max_examples is not None {
            property_test_max_examples = int(config.property_test_max_examples);
        }
        if config.run_property_tests is not None {
            enable_property_tests = bool(config.run_property_tests);
        }
        if config.stop_on_test_failure is not None {
            stop_on_test_failure = bool(config.stop_on_test_failure);
        }
        if config.min_improvement_ratio is not None {
            min_improvement_ratio = float(config.min_improvement_ratio);
        }
        if config.candidate_count is not None {
            candidate_count = int(config.candidate_count);
        }
    }

    # Initialize: Parse input function and derive metadata
    source_code = function_input["source_code"];
    language = function_input.get("language", "python");
    parsed_info = parse_function(
        source_code,
        language,
        function_input.get("function_name", None)
    );
    function_name = parsed_info.get("function_name", function_input.get("function_name", ""));
    if function_name == "" {
        function_name = function_input.get("function_name", "");
    }

    run_log = _maybe_create_run_log(function_input, function_name);
    zero_metrics = {
        "execution_time": 0.0,
        "memory_usage": 0.0,
        "cpu_usage": None,
        "code_complexity": None,
        "test_coverage": None
    };
    baseline_metrics = zero_metrics;

    try {
        if run_log is not None {
            _safe_log(lambda: run_log.event(
                    "run_metadata",
                    function_name=function_name,
                    language=language,
                    criteria_name=(criteria.name if criteria is not None else None),
                    config_name=(config.name if config is not None else None),
                    analysis_mode=function_input.get("analysis_mode", None)
                ));
        }

        print("Starting optimization for function: " + function_name);

    # Validate required profiling input
    if "function_call" not in function_input or function_input["function_call"] is None {
        print("function_input must include 'function_call' for profiling.");
        if run_log is not None {
            _safe_log(lambda: run_log.error("Missing required 'function_call' for profiling"));
        }
        return _with_run_metadata({
            "optimized_code": source_code,
            "iteration_number": 0,
            "metrics": zero_metrics,
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": zero_metrics,
            "termination_reason": "Missing required 'function_call' for profiling",
            "converged": False,
            "error": "Missing required 'function_call' for profiling"
        }, run_log);
    }
    function_call: str = str(function_input["function_call"]);

    test_cases = function_input.get("test_cases", []);
    if test_cases is None {
        test_cases = [];
    }

    baseline_test_code = _pytest_from_test_cases(function_name, test_cases, function_call);
    baseline_test_results = run_tests_with_coverage(
        source_code,
        baseline_test_code
    );
    baseline_coverage_pct = -1.0;
    if baseline_test_results.get("passed", False) {
        baseline_coverage_pct = float(baseline_test_results.get("coverage_percent", -1.0));
    }

    # Baseline profiling on original code (before any optimization)
    baseline_profile = profile_code(
        source_code,
        function_call,
        benchmark_min_rounds,
        benchmark_warmup
    );
    if not baseline_profile.get("success", False) {
        print("Baseline profiling failed: " + str(baseline_profile.get("error", "")));
        if run_log is not None {
            _safe_log(lambda: run_log.error(
                    "Baseline profiling failed",
                    error=str(baseline_profile.get("error", "")),
                    median_ms=baseline_profile.get("median_ms", 0.0),
                    stdev_ms=baseline_profile.get("stdev_ms", 0.0)
                ));
        }
        return _with_run_metadata({
            "optimized_code": source_code,
            "iteration_number": 0,
            "metrics": zero_metrics,
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": zero_metrics,
            "termination_reason": "Baseline profiling failed",
            "converged": False,
            "error": "Baseline profiling failed: " + str(baseline_profile.get("error", ""))
        }, run_log);
    }

    # Complexity: cyclomatic + nesting depth
    baseline_complexity = compute_complexity(source_code);
    print(
        "Baseline complexity: CC=" + str(baseline_complexity.get("cyclomatic_complexity", "?"))
        + " depth=" + str(baseline_complexity.get("max_nesting_depth", "?"))
    );
    if run_log is not None {
        _safe_log(lambda: run_log.event(
                "baseline_metrics",
                median_ms=float(baseline_profile.get("median_ms", 0.0)),
                stdev_ms=float(baseline_profile.get("stdev_ms", 0.0)),
                peak_memory_kb=float(baseline_profile.get("peak_memory_kb", 0.0)),
                cyclomatic_complexity=baseline_complexity.get("cyclomatic_complexity", None),
                max_nesting_depth=baseline_complexity.get("max_nesting_depth", None)
            ));
    }

    # Stdev from baseline for significance testing later
    baseline_stdev_sec = float(baseline_profile.get("stdev_ms", 0.0)) / 1000.0;
    baseline_n = int(baseline_profile.get("rounds", 0));

    baseline_metrics_obj = _metrics_from_profile(
        baseline_profile,
        baseline_complexity,
        baseline_coverage_pct
    );
    baseline_metrics = _metrics_to_dict(baseline_metrics_obj);

    current_source_code = source_code;
    original_source_code = source_code;
    final_stop_reason = "";
    final_converged = False;
    iteration = 0;
    no_improvement_count = 0;
    results = [];
    best_passing_result = None;
    last_feedback = None;

    # Precompute criteria dict once
    criteria_dict = _criteria_to_dict(criteria);

    # Main optimization loop
    while iteration < max_iterations {
        iteration = iteration + 1;
        print("Iteration " + str(iteration) + " of " + str(max_iterations));
        if run_log is not None {
            _safe_log(lambda: run_log.event("iteration_start", iteration=iteration));
        }
        
        # Agent think/prep phase (dispatch by analysis_mode or config.llm_model)
        analysis_mode = function_input.get("analysis_mode", None);
        llm_model = None;
        if config is not None and config.llm_model is not None {
            llm_model = config.llm_model;
        }
        plan = think_and_prep(
            current_source_code,
            criteria_dict,
            function_call,
            test_cases,
            analysis_mode,
            llm_model,
            last_feedback,
            run_log
        );
        last_feedback = None;
        
        candidate_plans = enumerate_candidate_plans(plan, candidate_count);

        # Generate pytest from structured test cases (user + plan)
        merged_cases = _merge_test_cases(test_cases, plan);
        test_code = _pytest_from_test_cases(function_name, merged_cases, function_call);
        best_candidate_eval = None;
        candidate_failures: list = [];
        candidate_idx = 0;
        for candidate_plan in candidate_plans {
            candidate_label = str(candidate_plan.get("label", "candidate_" + str(candidate_idx)));
            candidate_idx = candidate_idx + 1;
            optimized_code = write_optimized_code(
                current_source_code,
                candidate_plan,
                llm_model,
                run_log
            );

            candidate_eval = _evaluate_candidate(
                iteration,
                candidate_label,
                optimized_code,
                candidate_plan,
                function_name,
                function_call,
                original_source_code,
                test_code,
                baseline_metrics,
                baseline_metrics_obj,
                baseline_stdev_sec,
                baseline_n,
                baseline_coverage_pct,
                benchmark_min_rounds,
                benchmark_warmup,
                property_test_max_examples,
                enable_property_tests,
                run_log
            );
            if run_log is not None {
                _safe_log(lambda: run_log.event(
                        "candidate_evaluation",
                        iteration=iteration,
                        candidate_label=candidate_label,
                        passed=bool(candidate_eval.get("passed", False)),
                        error=str(candidate_eval.get("result", {}).get("error", "")),
                        improvement_ratio=float(candidate_eval.get("comparison", {}).get("improvement_ratio", 0.0))
                    ));
            }

            if candidate_eval["passed"] {
                if _is_better_candidate_eval(candidate_eval, best_candidate_eval) {
                    best_candidate_eval = candidate_eval;
                }
            } else {
                candidate_failures.append(candidate_eval);
            }
        }

        if best_candidate_eval is None {
            failure_eval = _pick_best_failure(candidate_failures);
            result = failure_eval["result"];
            result["candidate_count_evaluated"] = len(candidate_plans);
            results = results + [result];

            if stop_on_test_failure {
                final_stop_reason = str(result.get("error", "Optimization iteration failed"));
                final_converged = False;
                break;
            } else {
                last_feedback = failure_eval.get("feedback", None);
                continue;
            }
        }

        optimized_code = best_candidate_eval["optimized_code"];
        current_metrics_obj = best_candidate_eval["metrics_obj"];
        current_metrics = best_candidate_eval["metrics"];
        comparison = best_candidate_eval["comparison"];
        signal = best_candidate_eval["signal"];
        reason = best_candidate_eval["reason"];

        convergence_status = {
            "should_continue": signal != "done",
            "reason": reason,
            "converged": signal == "done"
        };
        
        # Create result for this iteration
        result = {
            "optimized_code": optimized_code,
            "iteration_number": iteration,
            "metrics": current_metrics,
            "test_passed": True,
            "improvement_ratio": comparison["improvement_ratio"],
            "is_significant": comparison.get("is_significant", False),
            "confidence": comparison.get("confidence", 0.0),
            "candidate_label": best_candidate_eval.get("candidate_label", ""),
            "candidate_count_evaluated": len(candidate_plans),
            "coverage_delta": best_candidate_eval.get("coverage_delta", None)
        };
        results = results + [result];
        best_passing_result = result;
        if run_log is not None {
            _safe_log(lambda: run_log.event(
                    "candidate_selected",
                    iteration=iteration,
                    candidate_label=str(best_candidate_eval.get("candidate_label", "")),
                    candidate_count_evaluated=len(candidate_plans),
                    improvement_ratio=float(comparison.get("improvement_ratio", 0.0))
                ));
            _safe_log(lambda: run_log.optimization_step(
                    iteration=iteration,
                    improvement_ratio=float(comparison.get("improvement_ratio", 0.0)),
                    is_significant=bool(comparison.get("is_significant", False)),
                    confidence=float(comparison.get("confidence", 0.0)),
                    agent_signal=str(signal),
                    agent_reason=str(reason)
                ));
        }
        
        # Check termination conditions (driven by config and agent decision)
        should_stop = False;
        stop_reason = "";
        
        # Stop if max iterations reached
        if iteration >= max_iterations {
            should_stop = True;
            stop_reason = "Maximum iterations reached";
        }
        
        # Stop if convergence status says to stop
        if not convergence_status["should_continue"] {
            should_stop = True;
            stop_reason = convergence_status["reason"];
        }
        
        # Stop if no (significant) improvement for N consecutive iterations
        is_real_improvement = (
            comparison["improvement_ratio"] >= min_improvement_ratio
            and comparison.get("is_significant", False)
        );
        if not is_real_improvement {
            no_improvement_count = no_improvement_count + 1;
            if no_improvement_count >= max_no_improvement_iters {
                should_stop = True;
                stop_reason = "No significant improvement for " + str(no_improvement_count) + " consecutive iterations";
            }
        } else {
            no_improvement_count = 0;  # Reset counter on improvement
        }
        
        if should_stop {
            final_stop_reason = stop_reason;
            final_converged = convergence_status["converged"];
            print("Stopping optimization: " + stop_reason);
            break;
        }
        
        # Update function_input for next iteration
        function_input = {
            "source_code": optimized_code,
            "function_name": function_input["function_name"],
            "function_call": function_call,
            "language": language,
            "analysis_mode": function_input.get("analysis_mode", None),
            "test_cases": function_input.get("test_cases", None),
            "extra": function_input.get("extra", None)
        };
        current_source_code = optimized_code;
    }
    
    # Format and return final result
    if len(results) > 0 {
        final_result = dict(results[len(results) - 1]);
        if best_passing_result is not None {
            final_result = dict(best_passing_result);
        } elif current_source_code is not None and current_source_code != "" {
            # Prefer returning last known-good code when all iterations failed.
            final_result["optimized_code"] = current_source_code;
        }
        final_result["baseline_metrics"] = baseline_metrics;
        final_result["termination_reason"] = final_stop_reason;
        final_result["converged"] = final_converged;
        print("Optimization complete. Final improvement ratio: " + str(final_result["improvement_ratio"]));
        return _with_run_metadata(final_result, run_log);
    }

    print("No results generated");
    return _with_run_metadata({
        "optimized_code": source_code,
        "iteration_number": 0,
        "metrics": baseline_metrics,
        "test_passed": False,
        "improvement_ratio": 0.0,
        "baseline_metrics": baseline_metrics,
        "termination_reason": "No iterations completed",
        "converged": False,
        "error": "No iterations completed"
    }, run_log);
    } except Exception as e {
        if run_log is not None {
            _safe_log(lambda: run_log.error(
                    "Optimization failed",
                    phase="run_optimization",
                    error=str(e)
                ));
        }
        return _with_run_metadata({
            "optimized_code": source_code,
            "iteration_number": 0,
            "metrics": baseline_metrics,
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": baseline_metrics,
            "termination_reason": "Optimization failed",
            "converged": False,
            "error": str(e)
        }, run_log);
    } finally {
        if run_log is not None {
            _safe_log(lambda: run_log.close());
        }
    }
}


def _criteria_to_dict(criteria: OptimizationCriteria | None) -> dict {
    if criteria is None {
        return {};
    }
    return {
        "performance_weight": criteria.performance_weight,
        "code_quality_weight": criteria.code_quality_weight,
        "functionality_weight": criteria.functionality_weight
    };
}


def _metrics_from_profile(profile: dict, complexity: dict = {}, coverage_pct: float = -1.0) -> Metrics {
    exec_ms = float(profile.get("median_ms", 0.0));
    mem_kb = float(profile.get("peak_memory_kb", 0.0));
    exec_sec = exec_ms / 1000.0;
    mem_mb = mem_kb / 1024.0;

    cc = None;
    if complexity and complexity.get("cyclomatic_complexity", 0) > 0 {
        cc = complexity.get("cyclomatic_complexity", None);
    }

    tc = None;
    if coverage_pct >= 0 {
        tc = coverage_pct;
    }

    return Metrics(
        execution_time=exec_sec,
        memory_usage=mem_mb,
        code_complexity=cc,
        test_coverage=tc
    );
}


def _metrics_to_dict(metrics: Metrics) -> dict {
    return {
        "execution_time": metrics.execution_time,
        "memory_usage": metrics.memory_usage,
        "cpu_usage": metrics.cpu_usage,
        "code_complexity": metrics.code_complexity,
        "test_coverage": metrics.test_coverage
    };
}


def _exception_mismatch_from_text(text: str) -> bool {
    lower = text.lower();
    return (
        "did not raise" in lower
        or "raises" in lower
        or "exception" in lower
        or "traceback" in lower
    );
}


def _extract_exception_mismatch(failures: list, error: str = "") -> bool {
    if _exception_mismatch_from_text(error) {
        return True;
    }
    for failure in failures {
        if _exception_mismatch_from_text(str(failure.get("message", ""))) {
            return True;
        }
    }
    return False;
}


def _extract_falsifying_example(prop_results: dict) -> str {
    failures = prop_results.get("failures", []);
    for failure in failures {
        example = failure.get("falsifying_example", None);
        if example is not None and example != "" {
            return str(example);
        }
    }
    return "";
}


def _coverage_delta(current_pct: float, baseline_pct: float) -> float | None {
    if current_pct < 0 or baseline_pct < 0 {
        return None;
    }
    return current_pct - baseline_pct;
}


def _build_failure_feedback(
    kind: str,
    iteration: int,
    candidate_label: str,
    function_name: str,
    optimized_code: str,
    error: str = "",
    failures: list = [],
    coverage_percent: float = -1.0,
    baseline_coverage_percent: float = -1.0,
    falsifying_example: str = ""
) -> dict {
    return {
        "type": kind,
        "iteration": iteration,
        "candidate_label": candidate_label,
        "function_name": function_name,
        "error": error,
        "failures": failures,
        "coverage_percent": coverage_percent,
        "coverage_delta": _coverage_delta(coverage_percent, baseline_coverage_percent),
        "falsifying_example": falsifying_example,
        "exception_mismatch": _extract_exception_mismatch(failures, error),
        "previous_code": optimized_code
    };
}


def _is_better_candidate_eval(candidate_eval: dict, best_candidate_eval: dict | None) -> bool {
    if best_candidate_eval is None {
        return True;
    }

    candidate_improvement = float(candidate_eval.get("comparison", {}).get("improvement_ratio", 0.0));
    best_improvement = float(best_candidate_eval.get("comparison", {}).get("improvement_ratio", 0.0));
    candidate_significant = bool(candidate_eval.get("comparison", {}).get("is_significant", False));
    best_significant = bool(best_candidate_eval.get("comparison", {}).get("is_significant", False));

    if candidate_significant and not best_significant {
        return True;
    }
    if candidate_significant == best_significant and candidate_improvement > best_improvement {
        return True;
    }
    return False;
}


def _pick_best_failure(candidate_failures: list) -> dict {
    if len(candidate_failures) == 0 {
        return {
            "passed": False,
            "result": {
                "optimized_code": "",
                "iteration_number": 0,
                "metrics": {},
                "test_passed": False,
                "improvement_ratio": 0.0,
                "error": "No candidate evaluations were produced"
            },
            "feedback": {
                "type": "iteration_failure",
                "error": "No candidate evaluations were produced"
            }
        };
    }

    priority = {
        "profiling_failure": 0,
        "property_test_failure": 1,
        "unit_test_failure": 2
    };

    best = candidate_failures[0];
    best_kind = str(best.get("feedback", {}).get("type", ""));
    best_priority = priority.get(best_kind, 99);

    idx = 1;
    while idx < len(candidate_failures) {
        current = candidate_failures[idx];
        current_kind = str(current.get("feedback", {}).get("type", ""));
        current_priority = priority.get(current_kind, 99);
        if current_priority < best_priority {
            best = current;
            best_priority = current_priority;
        }
        idx = idx + 1;
    }

    return best;
}


def _evaluate_candidate(
    iteration: int,
    candidate_label: str,
    optimized_code: str,
    candidate_plan: dict,
    function_name: str,
    function_call: str,
    original_source_code: str,
    test_code: str,
    baseline_metrics: dict,
    baseline_metrics_obj: Metrics,
    baseline_stdev_sec: float,
    baseline_n: int,
    baseline_coverage_pct: float,
    benchmark_min_rounds: int = 10,
    benchmark_warmup: bool = True,
    property_test_max_examples: int = 50,
    enable_property_tests: bool = True,
    run_log: Any = None
) -> dict {
    test_results = run_tests_with_coverage(
        optimized_code,
        test_code
    );
    coverage_pct = float(test_results.get("coverage_percent", -1.0));

    if run_log is not None {
        _safe_log(lambda: run_log.event(
                "tests",
                iteration=iteration,
                candidate_label=candidate_label,
                passed=bool(test_results.get("passed", False)),
                total=int(test_results.get("total", 0)),
                passed_count=int(test_results.get("passed_count", 0)),
                failed_count=int(test_results.get("failed_count", 0)),
                coverage_percent=coverage_pct
            ));
    }

    if not test_results.get("passed", False) {
        feedback = _build_failure_feedback(
            "unit_test_failure",
            iteration,
            candidate_label,
            function_name,
            optimized_code,
            str(test_results.get("error", "")),
            test_results.get("failures", []),
            coverage_pct,
            baseline_coverage_pct
        );
        return {
            "passed": False,
            "optimized_code": optimized_code,
            "feedback": feedback,
            "result": {
                "optimized_code": optimized_code,
                "iteration_number": iteration,
                "metrics": baseline_metrics,
                "test_passed": False,
                "improvement_ratio": 0.0,
                "candidate_label": candidate_label,
                "coverage_delta": feedback.get("coverage_delta", None),
                "error": "Tests failed: " + str(test_results.get("error", ""))
            }
        };
    }

    if enable_property_tests {
        prop_results = run_property_tests(
            optimized_code,
            function_name,
            reference_code=original_source_code,
            max_examples=property_test_max_examples
        );
        if run_log is not None {
            _safe_log(lambda: run_log.event(
                    "property_tests",
                    iteration=iteration,
                    candidate_label=candidate_label,
                    passed=bool(prop_results.get("passed", False)),
                    total=int(prop_results.get("total", 0)),
                    passed_count=int(prop_results.get("passed_count", 0)),
                    failed_count=int(prop_results.get("failed_count", 0)),
                    examples_run=int(prop_results.get("examples_run", 0)),
                    falsifying_example=str(prop_results.get("falsifying_example", "")),
                    error=str(prop_results.get("error", ""))
                ));
        }
        if not prop_results.get("passed", True) {
            falsifying_example = _extract_falsifying_example(prop_results);
            feedback = _build_failure_feedback(
                "property_test_failure",
                iteration,
                candidate_label,
                function_name,
                optimized_code,
                str(prop_results.get("error", "")),
                prop_results.get("failures", []),
                coverage_pct,
                baseline_coverage_pct,
                falsifying_example
            );
            return {
                "passed": False,
                "optimized_code": optimized_code,
                "feedback": feedback,
                "result": {
                    "optimized_code": optimized_code,
                    "iteration_number": iteration,
                    "metrics": baseline_metrics,
                    "test_passed": False,
                    "improvement_ratio": 0.0,
                    "candidate_label": candidate_label,
                    "coverage_delta": feedback.get("coverage_delta", None),
                    "error": "Property-based test failure"
                }
            };
        }
    } else {
        if run_log is not None {
            _safe_log(lambda: run_log.event(
                    "property_tests",
                    iteration=iteration,
                    candidate_label=candidate_label,
                    passed=True,
                    total=0,
                    passed_count=0,
                    failed_count=0,
                    examples_run=0,
                    falsifying_example="",
                    error="skipped"
                ));
        }
    }

    profile = profile_code(
        optimized_code,
        function_call,
        benchmark_min_rounds,
        benchmark_warmup
    );
    if run_log is not None {
        _safe_log(lambda: run_log.event(
                "profile",
                iteration=iteration,
                candidate_label=candidate_label,
                success=bool(profile.get("success", False)),
                median_ms=float(profile.get("median_ms", 0.0)),
                stdev_ms=float(profile.get("stdev_ms", 0.0)),
                peak_memory_kb=float(profile.get("peak_memory_kb", 0.0)),
                error=str(profile.get("error", ""))
            ));
    }
    if not profile.get("success", False) {
        feedback = _build_failure_feedback(
            "profiling_failure",
            iteration,
            candidate_label,
            function_name,
            optimized_code,
            "Profiling failed: " + str(profile.get("error", "")),
            [],
            coverage_pct,
            baseline_coverage_pct
        );
        return {
            "passed": False,
            "optimized_code": optimized_code,
            "feedback": feedback,
            "result": {
                "optimized_code": optimized_code,
                "iteration_number": iteration,
                "metrics": baseline_metrics,
                "test_passed": True,
                "improvement_ratio": 0.0,
                "candidate_label": candidate_label,
                "coverage_delta": feedback.get("coverage_delta", None),
                "error": "Profiling failed: " + str(profile.get("error", ""))
            }
        };
    }

    iter_complexity = compute_complexity(optimized_code);
    current_stdev_sec = float(profile.get("stdev_ms", 0.0)) / 1000.0;
    current_n = int(profile.get("rounds", 0));

    current_metrics_obj = _metrics_from_profile(
        profile,
        iter_complexity,
        coverage_pct
    );
    current_metrics = _metrics_to_dict(current_metrics_obj);
    comparison = compare_metrics(
        baseline_metrics_obj,
        current_metrics_obj,
        baseline_stdev_sec,
        current_stdev_sec,
        baseline_n,
        current_n
    );

    agent_compare_input = {
        "execution_time_sec": current_metrics_obj.execution_time,
        "memory_mb": current_metrics_obj.memory_usage
    };
    agent_decision = compare(agent_compare_input, candidate_plan);
    signal = agent_decision.get("signal", "continue");
    reason = agent_decision.get("reason", "optimizer decision");

    return {
        "passed": True,
        "optimized_code": optimized_code,
        "candidate_label": candidate_label,
        "metrics_obj": current_metrics_obj,
        "metrics": current_metrics,
        "comparison": comparison,
        "signal": signal,
        "reason": reason,
        "coverage_delta": _coverage_delta(coverage_pct, baseline_coverage_pct)
    };
}


def _merge_test_cases(base_cases: list, plan: dict) -> list {
    merged = [];
    if base_cases is not None {
        merged = base_cases;
    }
    if plan is not None {
        extra = plan.get("test_cases", None);
        if extra is not None and len(extra) > 0 {
            merged = merged + extra;
        }
    }
    return merged;
}


def _pytest_from_test_cases(function_name: str, cases: list, function_call: str) -> str {
    test_cases = cases or [];

    # Ensure at least one smoke test exists
    if len(test_cases) == 0 and function_call is not None {
        test_cases = [{"call": function_call}];
    }

    has_raises = False;
    for c in test_cases {
        if "raises" in c and c["raises"] is not None {
            has_raises = True;
            break;
        }
    }

    lines = [];
    if has_raises {
        lines.append("import pytest");
    }
    lines.append("from solution import " + function_name);

    idx = 0;
    for c in test_cases {
        call_expr = c.get("call", None);
        expected = c.get("expected", None);
        raises = c.get("raises", None);
        name = c.get("name", None);
        if name is None {
            name = "test_case_" + str(idx);
        }
        name = str(name);
        if not name.startswith("test_") {
            name = "test_" + name;
        }

        if call_expr is None {
            continue;
        }
        call_expr = str(call_expr);

        lines.append("");
        lines.append("def " + str(name) + "():");

        if raises is not None {
            lines.append("    with pytest.raises(" + str(raises) + "):");
            lines.append("        " + str(call_expr));
        } elif expected is not None {
            lines.append("    assert " + str(call_expr) + " == " + str(expected));
        } else {
            lines.append("    " + str(call_expr));
        }

        idx = idx + 1;
    }

    return "\n".join(lines);
}
