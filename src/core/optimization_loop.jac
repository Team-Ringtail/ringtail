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
import from src.models.types { FunctionInput, OptimizationResult, Metrics, OptimizationPlan, ConvergenceStatus };
import from src.core.tester { run_tests };
import from src.core.profiler { profile_code };
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

    # Ensure at least one smoke test exists
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
    has function_input: dict;  # FunctionInput as dict (from Python dataclass)
    has criteria: OptimizationCriteria;  # Optimization criteria node
    has config: AgentConfig;  # Agent configuration node
    
    has baseline_metrics: dict = {};  # Baseline metrics for comparison (dict form)
    has iteration: int = 0;  # Current iteration count
    has no_improvement_count: int = 0;  # Consecutive iterations with no improvement
    has results: list = [];  # List of OptimizationResult dicts
    
    can with entry {
        # Initialize: Parse input function and derive metadata
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
                    "execution_time": 0.0,
                    "memory_usage": 0.0,
                    "cpu_usage": null,
                    "code_complexity": null,
                    "test_coverage": null
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

        # Baseline profiling on original code (before any optimization)
        baseline_profile = profile_code(
            source_code,
            function_call
        );
        if not baseline_profile.get("success", false) {
            std.err("Baseline profiling failed: " + str(baseline_profile.get("error", "")));
            report {
                "optimized_code": source_code,
                "iteration_number": 0,
                "metrics": {
                    "execution_time": 0.0,
                    "memory_usage": 0.0,
                    "cpu_usage": null,
                    "code_complexity": null,
                    "test_coverage": null
                },
                "test_passed": false,
                "improvement_ratio": 0.0,
                "error": "Baseline profiling failed: " + str(baseline_profile.get("error", ""))
            };
        }

        baseline_metrics_obj = _metrics_from_profile(baseline_profile);
        baseline_metrics = _metrics_to_dict(baseline_metrics_obj);

        current_source_code = source_code;
        
        # Main optimization loop
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
                std.out("Tests failed: " + str(test_results.get("error", "")));
                # Create result for this failed iteration
                result = {
                    "optimized_code": optimized_code,
                    "iteration_number": iteration,
                    "metrics": baseline_metrics,
                    "test_passed": false,
                    "improvement_ratio": 0.0
                };
                results = results + [result];
                
                # Stop if tests fail and cannot be fixed
                # (In real implementation, might want to retry or continue, but for now stop)
                break;
                # Stop if tests fail and cannot be fixed
                break;
            }
            
            # Profile optimized code
            profile = profile_code(
                optimized_code,
                function_call
            );
            if not profile.get("success", false) {
                std.err("Profiling failed on iteration " + str(iteration) + ": " + str(profile.get("error", "")));
                # Treat as no improvement and stop
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
                "test_passed": true,
                "improvement_ratio": comparison["improvement_ratio"]
            };
            results = results + [result];
            
            # Check termination conditions (Lance - implement fully)
            should_stop = false;
            stop_reason = "";
            
            # Stop if max iterations reached
            if iteration >= config.max_iterations {
                should_stop = true;
                stop_reason = "Maximum iterations reached";
            }
            
            # Stop if convergence status says to stop
            if not convergence_status["should_continue"] {
                should_stop = true;
                stop_reason = convergence_status["reason"];
            }
            
            # Stop if no improvement for N consecutive iterations
            if comparison["improvement_ratio"] <= 1.0 {
                no_improvement_count = no_improvement_count + 1;
                if no_improvement_count >= 3 {  # Configurable threshold
                    should_stop = true;
                    stop_reason = "No improvement for " + str(no_improvement_count) + " consecutive iterations";
                }
            } else {
                no_improvement_count = 0;  # Reset counter on improvement
            }
            
            if should_stop {
                std.out("Stopping optimization: " + stop_reason);
                break;
            }
            
            # Update function_input for next iteration
            function_input = {
                "source_code": optimized_code,
                "function_name": function_input["function_name"],
                "test_cases": function_input.get("test_cases", null)
            };
        }
        
        # Format and return final result
        if results.length > 0 {
            final_result = results[results.length - 1];  # Last iteration result
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
