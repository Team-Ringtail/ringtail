"""
Core optimization loop implementation.

This walker orchestrates the optimization process by:
1. Parsing the input function
2. Iteratively calling optimizer_agent, profiler, and tester
3. Evaluating convergence and terminating when appropriate
"""

import from config.optimization_criteria { OptimizationCriteria };
import from config.agent_config { AgentConfig };
import from src.utils.code_parser { parse_function };
import from src.utils.metrics { compare_metrics, aggregate_metrics, calculate_score };
import from src.models.types { Metrics };
import from src.core.tester { run_tests };
import from src.core.profiler { profile_code };
import from src.agents.optimizer_agent { think_and_prep, write_optimized_code, compare };


"""Run the full optimization loop for a given function description.

Args:
    input: dict with at least:
        - source_code: str
        - function_name: str
        - function_call: str (expression used by the profiler)
        - test_cases: optional list of structured test case dicts
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
    # Construct default criteria/config nodes (future: load named profiles)
    criteria = OptimizationCriteria();
    config = AgentConfig();
    if criteria_name is not None {
        criteria.name = criteria_name;
    }
    if config_name is not None {
        config.name = config_name;
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

    if config is not None {
        if config.max_iterations is not None {
            max_iterations = int(config.max_iterations);
        }
        if config.max_no_improvement_iters is not None {
            max_no_improvement_iters = int(config.max_no_improvement_iters);
        }
        if config.stop_on_test_failure is not None {
            stop_on_test_failure = bool(config.stop_on_test_failure);
        }
        if config.min_improvement_ratio is not None {
            min_improvement_ratio = float(config.min_improvement_ratio);
        }
    }

    # Initialize: Parse input function and derive metadata
    source_code = function_input["source_code"];
    language = function_input.get("language", "python");
    parsed_info = parse_function(source_code, language);
    function_name = parsed_info.get("function_name", function_input.get("function_name", ""));
    if function_name == "" {
        function_name = function_input.get("function_name", "");
    }

    print("Starting optimization for function: " + function_name);

    # Validate required profiling input
    if "function_call" not in function_input or function_input["function_call"] is None {
        print("function_input must include 'function_call' for profiling.");
        zero_metrics = {
            "execution_time": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": None,
            "code_complexity": None,
            "test_coverage": None
        };
        return {
            "optimized_code": source_code,
            "iteration_number": 0,
            "metrics": zero_metrics,
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": zero_metrics,
            "termination_reason": "Missing required 'function_call' for profiling",
            "converged": False,
            "error": "Missing required 'function_call' for profiling"
        };
    }
    function_call: str = str(function_input["function_call"]);

    test_cases = function_input.get("test_cases", []);
    if test_cases is None {
        test_cases = [];
    }

    # Baseline profiling on original code (before any optimization)
    baseline_profile = profile_code(
        source_code,
        function_call
    );
    if not baseline_profile.get("success", False) {
        print("Baseline profiling failed: " + str(baseline_profile.get("error", "")));
        zero_metrics = {
            "execution_time": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": None,
            "code_complexity": None,
            "test_coverage": None
        };
        return {
            "optimized_code": source_code,
            "iteration_number": 0,
            "metrics": zero_metrics,
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": zero_metrics,
            "termination_reason": "Baseline profiling failed",
            "converged": False,
            "error": "Baseline profiling failed: " + str(baseline_profile.get("error", ""))
        };
    }

    baseline_metrics_obj = _metrics_from_profile(baseline_profile);
    baseline_metrics = _metrics_to_dict(baseline_metrics_obj);

    current_source_code = source_code;
    final_stop_reason = "";
    final_converged = False;
    iteration = 0;
    no_improvement_count = 0;
    results = [];

    # Precompute criteria dict once
    criteria_dict = _criteria_to_dict(criteria);

    # Main optimization loop
    while iteration < max_iterations {
        iteration = iteration + 1;
        print("Iteration " + str(iteration) + " of " + str(max_iterations));
        
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
            llm_model
        );
        
        # Agent write phase
        optimized_code = write_optimized_code(
            current_source_code,
            plan
        );
        
        # Generate pytest from structured test cases (user + plan)
        merged_cases = _merge_test_cases(test_cases, plan);
        test_code = _pytest_from_test_cases(function_name, merged_cases, function_call);

        # Run tests on optimized code
        test_results = run_tests(
            optimized_code,
            test_code
        );
        
        # If tests fail, stop iteration (but don't break immediately - let termination logic handle it)
        if not test_results["passed"] {
            print("Tests failed: " + str(test_results.get("error", "")));
            # Create result for this failed iteration
            result = {
                "optimized_code": optimized_code,
                "iteration_number": iteration,
                "metrics": baseline_metrics,
                "test_passed": False,
                "improvement_ratio": 0.0
            };
            results = results + [result];

            if stop_on_test_failure {
                final_stop_reason = "Tests failed: " + str(test_results.get("error", ""));
                final_converged = False;
                break;
            } else {
                # Continue to next iteration without updating baseline or current_source_code
                continue;
            }
        }
        
        # Profile optimized code
        profile = profile_code(
            optimized_code,
            function_call
        );
        if not profile.get("success", False) {
            print("Profiling failed on iteration " + str(iteration) + ": " + str(profile.get("error", "")));
            # Treat as no improvement and stop
            result = {
                "optimized_code": optimized_code,
                "iteration_number": iteration,
                "metrics": baseline_metrics,
                "test_passed": True,
                "improvement_ratio": 0.0,
                "error": "Profiling failed: " + str(profile.get("error", ""))
            };
            results = results + [result];
            final_stop_reason = "Profiling failed: " + str(profile.get("error", ""));
            final_converged = False;
            break;
        }

        current_metrics_obj = _metrics_from_profile(profile);
        current_metrics = _metrics_to_dict(current_metrics_obj);

        # Compare metrics using Python utility
        comparison = compare_metrics(
            baseline_metrics_obj,
            current_metrics_obj
        );
        
        # Ask optimizer agent whether to continue based on profiler metrics vs plan
        agent_compare_input = {
            "execution_time_sec": current_metrics_obj.execution_time,
            "memory_mb": current_metrics_obj.memory_usage
        };
        agent_decision = compare(agent_compare_input, plan);
        signal = agent_decision.get("signal", "continue");
        reason = agent_decision.get("reason", "optimizer decision");

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
            "improvement_ratio": comparison["improvement_ratio"]
        };
        results = results + [result];
        
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
        
        # Stop if no improvement for N consecutive iterations
        if comparison["improvement_ratio"] < min_improvement_ratio {
            no_improvement_count = no_improvement_count + 1;
            if no_improvement_count >= max_no_improvement_iters {
                should_stop = True;
                stop_reason = "No improvement for " + str(no_improvement_count) + " consecutive iterations";
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
    }
    
    # Format and return final result
    if len(results) > 0 {
        final_result = dict(results[len(results) - 1]);
        final_result["baseline_metrics"] = baseline_metrics;
        final_result["termination_reason"] = final_stop_reason;
        final_result["converged"] = final_converged;
        print("Optimization complete. Final improvement ratio: " + str(final_result["improvement_ratio"]));
        return final_result;
    }

    print("No results generated");
    return {
        "optimized_code": source_code,
        "iteration_number": 0,
        "metrics": baseline_metrics,
        "test_passed": False,
        "improvement_ratio": 0.0,
        "baseline_metrics": baseline_metrics,
        "termination_reason": "No iterations completed",
        "converged": False,
        "error": "No iterations completed"
    };
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


def _metrics_from_profile(profile: dict) -> Metrics {
    exec_ms = float(profile.get("median_ms", 0.0));
    mem_kb = float(profile.get("peak_memory_kb", 0.0));
    exec_sec = exec_ms / 1000.0;
    mem_mb = mem_kb / 1024.0;
    return Metrics(
        execution_time=exec_sec,
        memory_usage=mem_mb
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
