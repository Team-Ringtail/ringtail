"""
Optimization request routing and helper API surface.
"""

import from src.core.discovery {
    build_function_input_from_file,
    discover_functions_in_file,
    build_function_input_from_replay_script,
    build_replay_inputs_from_script,
    build_replay_inputs_from_directory
}
import from src.core.optimization_loop { run_optimization }
import from src.core.ranker {
    rank_functions_in_file,
    rank_functions_in_directory,
    rank_replay_candidates_in_file,
    rank_replay_candidates_in_directory
}
import importlib;


walker optimize_function {
    # Reserved Jac entrypoint. The public helper functions below provide
    # the currently testable API-facing surface.
}


def:pub list_file_functions(file_path: str) -> list {
    return discover_functions_in_file(file_path);
}


def:pub inspect_file_function(
    file_path: str,
    function_name: str,
    function_call: str | None = None,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    return build_function_input_from_file(
        file_path,
        function_name,
        function_call,
        tests_root,
        analysis_mode
    );
}


def:pub optimize_file_function(
    file_path: str,
    function_name: str,
    function_call: str | None = None,
    tests_root: str = "tests",
    criteria_name: str | None = None,
    config_name: str | None = None,
    analysis_mode: str | None = None,
    llm_model: str | None = None
) -> dict {
    input = build_function_input_from_file(
        file_path,
        function_name,
        function_call,
        tests_root,
        analysis_mode
    );
    if "error" in input {
        return {
            "optimized_code": "",
            "iteration_number": 0,
            "metrics": {
                "execution_time": 0.0,
                "memory_usage": 0.0,
                "cpu_usage": None,
                "code_complexity": None,
                "test_coverage": None
            },
            "test_passed": False,
            "improvement_ratio": 0.0,
            "baseline_metrics": {
                "execution_time": 0.0,
                "memory_usage": 0.0,
                "cpu_usage": None,
                "code_complexity": None,
                "test_coverage": None
            },
            "termination_reason": input["error"],
            "converged": False,
            "error": input["error"]
        };
    }
    input = _with_runtime_overrides(input, analysis_mode, llm_model, None, None, None);
    return run_optimization(input, criteria_name, config_name);
}


def _error_result(message: str) -> dict {
    return {
        "optimized_code": "",
        "iteration_number": 0,
        "metrics": {
            "execution_time": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": None,
            "code_complexity": None,
            "test_coverage": None
        },
        "test_passed": False,
        "improvement_ratio": 0.0,
        "baseline_metrics": {
            "execution_time": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": None,
            "code_complexity": None,
            "test_coverage": None
        },
        "termination_reason": message,
        "converged": False,
        "error": message
    };
}


def _with_runtime_overrides(
    input: dict,
    analysis_mode: str | None = None,
    llm_model: str | None = None,
    run_id: str | None = None,
    run_name: str | None = None,
    enable_run_log: bool | None = None
) -> dict {
    if analysis_mode is not None and analysis_mode != "" {
        input["analysis_mode"] = analysis_mode;
    }
    if llm_model is not None and llm_model != "" {
        input["llm_model"] = llm_model;
    }
    if run_id is not None and run_id != "" {
        input["run_id"] = run_id;
    }
    if run_name is not None and run_name != "" {
        input["run_name"] = run_name;
    }
    if enable_run_log is not None {
        input["enable_run_log"] = bool(enable_run_log);
    }
    return input;
}


def _normalize_operation_request(request: dict) -> dict {
    mod = importlib.import_module("src.core.optimization_request_contract");
    normalize_defaults = getattr(mod, "normalize_request_defaults");
    return normalize_defaults(dict(request));
}


def _normalize_source_code_text(raw: str) -> str {
    text = str(raw).replace("\r\n", "\n").replace("\r", "\n");
    text_len = len(str(text));
    if "\n" not in text and "\\n" in text {
        decoded: list = [];
        i = 0;
        while i < text_len {
            ch = text[i];
            if ch == "\\" and i + 1 < text_len {
                nxt = text[i + 1];
                if nxt == "n" {
                    decoded.append("\n");
                    i = i + 2;
                    continue;
                }
                if nxt == "t" {
                    decoded.append("    ");
                    i = i + 2;
                    continue;
                }
                if nxt == "r" {
                    i = i + 2;
                    continue;
                }
            }
            decoded.append(ch);
            i = i + 1;
        }
        text = "".join(decoded);
    }
    return text;
}


def:pub get_optimization_operation_contract() -> dict {
    mod = importlib.import_module("src.core.optimization_request_contract");
    get_payload = getattr(mod, "get_contract_payload");
    return get_payload();
}


def:pub discover_and_describe(
    file_path: str,
    function_name: str,
    tests_root: str = "tests"
) -> dict {
    input = build_function_input_from_file(file_path, function_name, None, tests_root, None);
    if "error" in input {
        return input;
    }
    return {
        "function_name": input.get("function_name", ""),
        "function_call": input.get("function_call", ""),
        "discovered_test_files": input.get("extra", {}).get("discovered_test_files", []),
        "functions_in_file": discover_functions_in_file(file_path)
    };
}


def:pub discover_and_rank_file(
    file_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    return rank_functions_in_file(file_path, tests_root, limit);
}


def:pub discover_and_rank_directory(
    source_root: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    return rank_functions_in_directory(source_root, tests_root, limit);
}


def:pub inspect_replay_function(
    file_path: str,
    function_name: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    return build_function_input_from_replay_script(
        file_path,
        function_name,
        script_path,
        tests_root,
        analysis_mode
    );
}


def:pub inspect_replay_session(
    file_path: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    session = build_replay_inputs_from_script(
        file_path,
        script_path,
        tests_root,
        analysis_mode,
        None
    );
    candidates = [];
    for input in session.get("candidate_inputs", []) {
        candidates.append({
            "function_name": input.get("function_name", ""),
            "function_call": input.get("function_call", ""),
            "replay_trace_count": input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0),
            "discovered_test_count": len(input.get("extra", {}).get("discovered_test_files", []))
        });
    }
    return {
        "source_file": session.get("source_file", file_path),
        "replay_script": session.get("replay_script", script_path),
        "traced_function_names": session.get("traced_function_names", []),
        "observed_function_names": session.get("observed_function_names", []),
        "candidate_count": session.get("candidate_count", 0),
        "candidates": candidates,
        "replay_trace": session.get("replay_trace", {})
    };
}


def:pub discover_and_rank_replay_file(
    file_path: str,
    script_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    return rank_replay_candidates_in_file(file_path, script_path, tests_root, limit);
}


def:pub inspect_replay_repo(
    source_root: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    session = build_replay_inputs_from_directory(
        source_root,
        script_path,
        tests_root,
        analysis_mode
    );
    candidates = [];
    for input in session.get("candidate_inputs", []) {
        candidates.append({
            "source_file": input.get("extra", {}).get("source_file", ""),
            "function_name": input.get("function_name", ""),
            "function_call": input.get("function_call", ""),
            "replay_trace_count": input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0),
            "discovered_test_count": len(input.get("extra", {}).get("discovered_test_files", []))
        });
    }
    return {
        "source_files": session.get("source_files", []),
        "inferred_source_files": session.get("inferred_source_files", []),
        "source_selection_mode": session.get("source_selection_mode", ""),
        "replay_script": session.get("replay_script", script_path),
        "observed_source_files": session.get("observed_source_files", []),
        "observed_function_keys": session.get("observed_function_keys", []),
        "candidate_count": session.get("candidate_count", 0),
        "candidates": candidates,
        "replay_trace": session.get("replay_trace", {})
    };
}


def:pub discover_and_rank_replay_repo(
    source_root: str,
    script_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    return rank_replay_candidates_in_directory(source_root, script_path, tests_root, limit);
}


def:pub optimize_replay_function(
    file_path: str,
    function_name: str,
    script_path: str,
    tests_root: str = "tests",
    criteria_name: str | None = None,
    config_name: str | None = None,
    analysis_mode: str | None = None,
    llm_model: str | None = None
) -> dict {
    input = build_function_input_from_replay_script(
        file_path,
        function_name,
        script_path,
        tests_root,
        analysis_mode
    );
    if "error" in input {
        return _error_result(input["error"]);
    }

    trace_result = input.get("extra", {}).get("replay_trace", {});
    if not trace_result.get("success", False) {
        return _error_result("Replay trace failed: " + str(trace_result.get("error", "")));
    }
    if len(input.get("test_cases", [])) == 0 {
        return _error_result("Replay trace captured no test cases");
    }

    input = _with_runtime_overrides(input, analysis_mode, llm_model, None, None, None);
    return run_optimization(input, criteria_name, config_name);
}


def:pub optimize_best_replay_function(
    file_path: str,
    script_path: str,
    tests_root: str = "tests",
    criteria_name: str | None = None,
    config_name: str | None = None,
    analysis_mode: str | None = None,
    llm_model: str | None = None
) -> dict {
    session = build_replay_inputs_from_script(
        file_path,
        script_path,
        tests_root,
        analysis_mode,
        None
    );
    candidates = session.get("candidate_inputs", []);
    if len(candidates) == 0 {
        return _error_result("Replay trace captured no replay-backed function candidates");
    }

    selected_input = candidates[0];
    selected_name = selected_input.get("function_name", "");
    selected_trace_count = int(selected_input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0));
    for input in candidates {
        trace_count = int(input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0));
        if trace_count > selected_trace_count {
            selected_input = input;
            selected_name = input.get("function_name", "");
            selected_trace_count = trace_count;
        }
    }

    selected_input = _with_runtime_overrides(selected_input, analysis_mode, llm_model, None, None, None);
    result = run_optimization(selected_input, criteria_name, config_name);
    result["selected_function"] = selected_name;
    result["replay_trace_count"] = selected_trace_count;
    return result;
}


def:pub optimize_best_replay_in_repo(
    source_root: str,
    script_path: str,
    tests_root: str = "tests",
    criteria_name: str | None = None,
    config_name: str | None = None,
    analysis_mode: str | None = None,
    llm_model: str | None = None
) -> dict {
    ranked = rank_replay_candidates_in_directory(source_root, script_path, tests_root, 1);
    if len(ranked) == 0 {
        return _error_result("Replay trace captured no replay-backed repo candidates");
    }

    top_entry = ranked[0];
    target_source = str(top_entry.get("source_file", ""));
    target_function = str(top_entry.get("function_name", ""));

    session = build_replay_inputs_from_directory(
        source_root,
        script_path,
        tests_root,
        analysis_mode
    );
    candidates = session.get("candidate_inputs", []);
    selected_input = candidates[0];
    for input in candidates {
        if (
            str(input.get("function_name", "")) == target_function
            and str(input.get("extra", {}).get("source_file", "")) == target_source
        ) {
            selected_input = input;
            break;
        }
    }

    selected_input = _with_runtime_overrides(selected_input, analysis_mode, llm_model, None, None, None);
    result = run_optimization(selected_input, criteria_name, config_name);
    result["selected_function"] = target_function;
    result["selected_source_file"] = target_source;
    result["replay_trace_count"] = int(top_entry.get("replay_trace_count", 0));
    result["selection_score"] = float(top_entry.get("selection_score", 0.0));
    return result;
}


def:pub run_optimization_request(request: dict) -> dict | list {
    normalized = _normalize_operation_request(request);
    operation = str(normalized.get("operation", "optimize_input"));
    criteria_name = normalized.get("criteria_name", None);
    config_name = normalized.get("config_name", None);
    analysis_mode = normalized.get("analysis_mode", None);
    llm_model = normalized.get("llm_model", None);
    run_id = normalized.get("run_id", None);
    run_name = normalized.get("run_name", None);
    enable_run_log = normalized.get("enable_run_log", None);

    if operation == "optimize_input" {
        input = normalized.get("input", None);
        if input is None {
            return _error_result("optimize_input request must include input");
        }
        input["source_code"] = _normalize_source_code_text(str(input.get("source_code", "")));
        input = _with_runtime_overrides(
            dict(input),
            analysis_mode,
            llm_model,
            run_id,
            run_name,
            enable_run_log
        );
        return run_optimization(input, criteria_name, config_name);
    }

    if operation == "discover_and_rank_directory" {
        return discover_and_rank_directory(
            str(normalized.get("source_root", "")),
            str(normalized.get("tests_root", "tests")),
            int(normalized.get("limit", 10))
        );
    }

    if operation == "get_ranked_demo_suite_catalog" {
        mod = importlib.import_module("src.core.ranked_demo_suite");
        func = getattr(mod, "get_demo_suite_catalog");
        return func(normalized.get("benchmark_id", None));
    }

    if operation == "get_ranked_demo_benchmarks" {
        mod = importlib.import_module("src.core.ranked_demo_suite");
        func = getattr(mod, "get_demo_benchmarks");
        return func();
    }

    if operation == "get_latest_ranked_demo_suite" {
        mod = importlib.import_module("src.core.ranked_demo_suite");
        func = getattr(mod, "get_latest_demo_suite_result");
        return func();
    }

    if operation == "get_ranked_demo_job_progress" {
        mod = importlib.import_module("src.core.ranked_demo_suite");
        func = getattr(mod, "get_demo_job_progress");
        return func(str(normalized.get("job_id", "")));
    }

    if operation == "run_ranked_demo_suite" {
        mod = importlib.import_module("src.core.ranked_demo_suite");
        func = getattr(mod, "run_demo_suite");
        return func(
            server_url=str(normalized.get("server_url", "http://127.0.0.1:8000")),
            job_id=normalized.get("job_id", None),
            benchmark_id=normalized.get("benchmark_id", None),
            top_k=int(normalized.get("top_k", 3)),
            per_file_k=int(normalized.get("per_file_k", 1))
        );
    }

    if operation == "discover_and_rank_replay_repo" {
        return discover_and_rank_replay_repo(
            str(normalized.get("source_root", "")),
            str(normalized.get("script_path", "")),
            str(normalized.get("tests_root", "tests")),
            int(normalized.get("limit", 10))
        );
    }

    if operation == "optimize_file_function" {
        input = build_function_input_from_file(
            str(normalized.get("file_path", "")),
            str(normalized.get("function_name", "")),
            normalized.get("function_call", None),
            str(normalized.get("tests_root", "tests")),
            analysis_mode
        );
        if "error" in input {
            return _error_result(str(input["error"]));
        }
        input = _with_runtime_overrides(input, analysis_mode, llm_model, run_id, run_name, enable_run_log);
        return run_optimization(input, criteria_name, config_name);
    }

    if operation == "optimize_replay_function" {
        input = build_function_input_from_replay_script(
            str(normalized.get("file_path", "")),
            str(normalized.get("function_name", "")),
            str(normalized.get("script_path", "")),
            str(normalized.get("tests_root", "tests")),
            analysis_mode
        );
        if "error" in input {
            return _error_result(str(input["error"]));
        }
        trace_result = input.get("extra", {}).get("replay_trace", {});
        if not trace_result.get("success", False) {
            return _error_result("Replay trace failed: " + str(trace_result.get("error", "")));
        }
        if len(input.get("test_cases", [])) == 0 {
            return _error_result("Replay trace captured no test cases");
        }
        input = _with_runtime_overrides(input, analysis_mode, llm_model, run_id, run_name, enable_run_log);
        return run_optimization(input, criteria_name, config_name);
    }

    if operation == "optimize_best_replay_function" {
        session = build_replay_inputs_from_script(
            str(normalized.get("file_path", "")),
            str(normalized.get("script_path", "")),
            str(normalized.get("tests_root", "tests")),
            analysis_mode,
            None
        );
        candidates = session.get("candidate_inputs", []);
        if len(candidates) == 0 {
            return _error_result("Replay trace captured no replay-backed function candidates");
        }

        selected_input = candidates[0];
        selected_name = selected_input.get("function_name", "");
        selected_trace_count = int(selected_input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0));
        for input in candidates {
            trace_count = int(input.get("extra", {}).get("replay_trace", {}).get("trace_count", 0));
            if trace_count > selected_trace_count {
                selected_input = input;
                selected_name = input.get("function_name", "");
                selected_trace_count = trace_count;
            }
        }

        selected_input = _with_runtime_overrides(selected_input, analysis_mode, llm_model, run_id, run_name, enable_run_log);
        result = run_optimization(selected_input, criteria_name, config_name);
        result["selected_function"] = selected_name;
        result["replay_trace_count"] = selected_trace_count;
        return result;
    }

    if operation == "optimize_best_replay_in_repo" {
        ranked = rank_replay_candidates_in_directory(
            str(normalized.get("source_root", "")),
            str(normalized.get("script_path", "")),
            str(normalized.get("tests_root", "tests")),
            1
        );
        if len(ranked) == 0 {
            return _error_result("Replay trace captured no replay-backed repo candidates");
        }

        top_entry = ranked[0];
        target_source = str(top_entry.get("source_file", ""));
        target_function = str(top_entry.get("function_name", ""));
        session = build_replay_inputs_from_directory(
            str(normalized.get("source_root", "")),
            str(normalized.get("script_path", "")),
            str(normalized.get("tests_root", "tests")),
            analysis_mode
        );
        candidates = session.get("candidate_inputs", []);
        selected_input = candidates[0];
        for input in candidates {
            if (
                str(input.get("function_name", "")) == target_function
                and str(input.get("extra", {}).get("source_file", "")) == target_source
            ) {
                selected_input = input;
                break;
            }
        }

        selected_input = _with_runtime_overrides(selected_input, analysis_mode, llm_model, run_id, run_name, enable_run_log);
        result = run_optimization(selected_input, criteria_name, config_name);
        result["selected_function"] = target_function;
        result["selected_source_file"] = target_source;
        result["replay_trace_count"] = int(top_entry.get("replay_trace_count", 0));
        result["selection_score"] = float(top_entry.get("selection_score", 0.0));
        return result;
    }

    if operation == "run_repo_agent_job" {
        mod = importlib.import_module("src.core.repo_agent");
        run_job = getattr(mod, "run_repo_agent_job");
        return run_job(normalized);
    }

    return _error_result("Unsupported optimization operation: " + operation);
}
