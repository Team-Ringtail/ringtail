"""
Command-line interface for Ringtail
"""

import from src.core.discovery {
    build_function_input_from_file,
    discover_functions_in_file
}
import from src.core.optimization_loop { run_optimization }
import from src.core.ranker { rank_functions_in_file }


walker optimize_function {
    # Reserved Jac entrypoint. The public helper functions below provide
    # the currently testable CLI-facing surface.
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
    analysis_mode: str | None = None
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
    return run_optimization(input, criteria_name, config_name);
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
