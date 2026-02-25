"""
Core optimization loop implementation.

This walker orchestrates the optimization process by:
1. Parsing the input function
2. Computing baseline metrics (profile + complexity + coverage)
3. Iteratively calling optimizer_agent, profiler, and tester
4. Evaluating convergence with statistical significance checks
"""

import from config.optimization_criteria { OptimizationCriteria };
import from config.agent_config { AgentConfig };
import from src.utils.code_parser { parse_function };
import from src.utils.metrics { compare_metrics, aggregate_metrics, calculate_score };
import from src.utils.complexity { compute_complexity };
import from src.models.types { FunctionInput, OptimizationResult, Metrics, OptimizationPlan, ConvergenceStatus };
import from src.core.tester { run_tests };
import from src.core.tester { run_tests_with_coverage };
import from src.core.profiler { profile_code };
import from src.core.property_tester { run_property_tests };
import from src.agents.optimizer_agent { think_and_prep, write_optimized_code, compare };


def _criteria_to_dict(criteria: OptimizationCriteria) -> dict {
    if criteria is null {
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

    cc = null;
    if complexity and complexity.get("cyclomatic_complexity", 0) > 0 {
        cc = complexity.get("cyclomatic_complexity", null);
    }

    tc = null;
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


def _merge_test_cases(base_cases: list, plan: dict) -> list {
    merged = [];
    if base_cases is not null {
        merged = base_cases;
    }
    if plan is not null {
        extra = plan.get("test_cases", null);
        if extra is not null and len(extra) > 0 {
            merged = merged + extra;
        }
    }
    return merged;
}


def _pytest_from_test_cases(function_name: str, cases: list, function_call: str) -> str {
    test_cases = cases or [];

    if len(test_cases) == 0 and function_call is not null {
        test_cases = [{"call": function_call}];
    }

    has_raises = false;
    for c in test_cases {
        if "raises" in c and c["raises"] is not null {
            has_raises = true;
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
        call_expr = c.get("call", null);
        expected = c.get("expected", null);
        raises = c.get("raises", null);
        name = c.get("name", null);
        if name is null {
            name = "test_case_" + str(idx);
        }

        if call_expr is null {
            continue;
        }

        lines.append("");
        lines.append("def " + name + "():");

        if raises is not null {
            lines.append("    with pytest.raises(" + str(raises) + "):");
            lines.append("        " + call_expr);
        } elif expected is not null {
            lines.append("    assert " + call_expr + " == " + str(expected));
        } else {
            lines.append("    " + call_expr);
        }

        idx = idx + 1;
    }

    return "\n".join(lines);
}

walker optimize {
    has function_input: dict;
    has criteria: OptimizationCriteria;
    has config: AgentConfig;

    has baseline_metrics: dict = {};
    has iteration: int = 0;
    has no_improvement_count: int = 0;
    has results: list = [];

    can with entry {
        source_code = function_input["source_code"];
        parsed_info = parse_function(source_code);
        function_name = parsed_info.get("function_name", function_input.get("function_name", ""));
        if function_name == "" {
            function_name = function_input.get("function_name", "");
        }

        std.out("Starting optimization for function: " + function_name);

        criteria_dict = _criteria_to_dict(criteria);
        function_call = function_input.get("function_call", null);
        if function_call is null {
            std.err("function_input must include 'function_call' for profiling.");
            report {
                "optimized_code": source_code,
                "iteration_number": 0,
                "metrics": {
                    "execution_time": 0.0, "memory_usage": 0.0,
                    "cpu_usage": null, "code_complexity": null, "test_coverage": null
                },
                "test_passed": false,
                "improvement_ratio": 0.0,
                "error": "Missing required 'function_call' for profiling"
            };
        }

        test_cases = function_input.get("test_cases", []);
        if test_cases is null {
            test_cases = [];
        }

        # --- Baseline measurements ---

        # Profile: timing + memory with statistical rigor
        baseline_profile = profile_code(source_code, function_call);
        if not baseline_profile.get("success", false) {
            std.err("Baseline profiling failed: " + str(baseline_profile.get("error", "")));
            report {
                "optimized_code": source_code,
                "iteration_number": 0,
                "metrics": {
                    "execution_time": 0.0, "memory_usage": 0.0,
                    "cpu_usage": null, "code_complexity": null, "test_coverage": null
                },
                "test_passed": false,
                "improvement_ratio": 0.0,
                "error": "Baseline profiling failed: " + str(baseline_profile.get("error", ""))
            };
        }

        # Complexity: cyclomatic + nesting depth
        baseline_complexity = compute_complexity(source_code);
        std.out("Baseline complexity: CC=" + str(baseline_complexity.get("cyclomatic_complexity", "?"))
                + " depth=" + str(baseline_complexity.get("max_nesting_depth", "?")));

        # Stdev from baseline for significance testing later
        baseline_stdev_sec = float(baseline_profile.get("stdev_ms", 0.0)) / 1000.0;
        baseline_n = int(baseline_profile.get("rounds", 0));

        baseline_metrics_obj = _metrics_from_profile(baseline_profile, baseline_complexity);
        baseline_metrics = _metrics_to_dict(baseline_metrics_obj);

        current_source_code = source_code;
        original_source_code = source_code;

        # --- Main optimization loop ---

        while iteration < config.max_iterations {
            iteration = iteration + 1;
            std.out("Iteration " + str(iteration) + " of " + str(config.max_iterations));

            # Agent think/prep phase
            plan = think_and_prep(
                current_source_code,
                criteria_dict,
                function_call,
                test_cases
            );

            # Agent write phase
            optimized_code = write_optimized_code(current_source_code, plan);

            # --- Correctness gate: fixed tests + coverage ---
            merged_cases = _merge_test_cases(test_cases, plan);
            test_code = _pytest_from_test_cases(function_name, merged_cases, function_call);

            test_results = run_tests_with_coverage(optimized_code, test_code);

            if not test_results["passed"] {
                std.out("Tests failed: " + str(test_results.get("error", "")));
                result = {
                    "optimized_code": optimized_code,
                    "iteration_number": iteration,
                    "metrics": baseline_metrics,
                    "test_passed": false,
                    "improvement_ratio": 0.0
                };
                results = results + [result];
                break;
            }

            coverage_pct = float(test_results.get("coverage_percent", -1.0));

            # Property-based correctness: compare against original implementation
            prop_results = run_property_tests(
                optimized_code,
                function_name,
                reference_code=original_source_code,
                max_examples=50
            );
            if not prop_results.get("passed", true) {
                std.out("Property tests failed: " + str(prop_results.get("failures", [])));
                result = {
                    "optimized_code": optimized_code,
                    "iteration_number": iteration,
                    "metrics": baseline_metrics,
                    "test_passed": false,
                    "improvement_ratio": 0.0,
                    "error": "Property-based test failure"
                };
                results = results + [result];
                break;
            }

            # --- Performance measurement ---
            profile = profile_code(optimized_code, function_call);
            if not profile.get("success", false) {
                std.err("Profiling failed on iteration " + str(iteration));
                result = {
                    "optimized_code": optimized_code,
                    "iteration_number": iteration,
                    "metrics": baseline_metrics,
                    "test_passed": true,
                    "improvement_ratio": 0.0,
                    "error": "Profiling failed: " + str(profile.get("error", ""))
                };
                results = results + [result];
                break;
            }

            iter_complexity = compute_complexity(optimized_code);
            current_stdev_sec = float(profile.get("stdev_ms", 0.0)) / 1000.0;
            current_n = int(profile.get("rounds", 0));

            current_metrics_obj = _metrics_from_profile(profile, iter_complexity, coverage_pct);
            current_metrics = _metrics_to_dict(current_metrics_obj);

            # Compare with statistical significance
            comparison = compare_metrics(
                baseline_metrics_obj,
                current_metrics_obj,
                baseline_stdev=baseline_stdev_sec,
                current_stdev=current_stdev_sec,
                baseline_n=baseline_n,
                current_n=current_n
            );

            # Agent convergence decision
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

            result = {
                "optimized_code": optimized_code,
                "iteration_number": iteration,
                "metrics": current_metrics,
                "test_passed": true,
                "improvement_ratio": comparison["improvement_ratio"],
                "is_significant": comparison.get("is_significant", false),
                "confidence": comparison.get("confidence", 0.0)
            };
            results = results + [result];

            # --- Termination checks ---
            should_stop = false;
            stop_reason = "";

            if iteration >= config.max_iterations {
                should_stop = true;
                stop_reason = "Maximum iterations reached";
            }

            if not convergence_status["should_continue"] {
                should_stop = true;
                stop_reason = convergence_status["reason"];
            }

            # Only count as improvement if statistically significant
            is_real_improvement = (
                comparison["improvement_ratio"] > 1.0
                and comparison.get("is_significant", false)
            );

            if not is_real_improvement {
                no_improvement_count = no_improvement_count + 1;
                if no_improvement_count >= 3 {
                    should_stop = true;
                    stop_reason = "No significant improvement for " + str(no_improvement_count) + " consecutive iterations";
                }
            } else {
                no_improvement_count = 0;
            }

            if should_stop {
                std.out("Stopping optimization: " + stop_reason);
                break;
            }

            function_input = {
                "source_code": optimized_code,
                "function_name": function_input["function_name"],
                "test_cases": function_input.get("test_cases", null)
            };
            current_source_code = optimized_code;
        }

        # Return best result
        if results.length > 0 {
            final_result = results[results.length - 1];
            std.out("Optimization complete. Final improvement ratio: " + str(final_result["improvement_ratio"]));
            report final_result;
        } else {
            std.err("No results generated");
            report {
                "optimized_code": function_input["source_code"],
                "iteration_number": 0,
                "metrics": baseline_metrics,
                "test_passed": false,
                "improvement_ratio": 0.0,
                "error": "No iterations completed"
            };
        }
    }
}
