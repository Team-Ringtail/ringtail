"""
Lightweight function ranking using existing discovery, profiling, and complexity
signals. This is intentionally single-file and Python-focused.
"""

import from src.core.discovery { build_function_input_from_file, discover_functions_in_file }
import from src.core.discovery { build_replay_inputs_from_script }
import from src.core.discovery { build_replay_inputs_from_directory }
import from src.core.profiler { profile_code }
import from src.utils.complexity { compute_complexity }


def _ranking_score(entry: dict) -> float {
    runtime_component = float(entry.get("median_ms", 0.0));
    complexity_component = float(entry.get("cyclomatic_complexity", 0));
    test_bonus = float(entry.get("discovered_test_count", 0)) * 100.0;
    return runtime_component * 1000.0 + complexity_component + test_bonus;
}


def _insert_ranked(entries: list, entry: dict) -> list {
    if len(entries) == 0 {
        return [entry];
    }

    result: list = [];
    inserted = False;
    entry_score = _ranking_score(entry);

    for existing in entries {
        if not inserted and entry_score > _ranking_score(existing) {
            result.append(entry);
            inserted = True;
        }
        result.append(existing);
    }

    if not inserted {
        result.append(entry);
    }

    return result;
}


def _replay_ranking_score(entry: dict) -> float {
    replay_component = float(entry.get("replay_trace_count", 0)) * 10000.0;
    unique_call_component = float(entry.get("replay_unique_call_count", 0)) * 1000.0;
    runtime_component = float(entry.get("median_ms", 0.0)) * 1000.0;
    complexity_component = float(entry.get("cyclomatic_complexity", 0));
    test_bonus = float(entry.get("discovered_test_count", 0)) * 100.0;
    return replay_component + unique_call_component + runtime_component + complexity_component + test_bonus;
}


def _insert_replay_ranked(entries: list, entry: dict) -> list {
    if len(entries) == 0 {
        return [entry];
    }

    result: list = [];
    inserted = False;
    entry_score = _replay_ranking_score(entry);

    for existing in entries {
        if not inserted and entry_score > _replay_ranking_score(existing) {
            result.append(entry);
            inserted = True;
        }
        result.append(existing);
    }

    if not inserted {
        result.append(entry);
    }

    return result;
}


def:pub rank_functions_in_file(
    file_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    functions = discover_functions_in_file(file_path);
    ranked: list = [];

    for function_info in functions {
        function_name = function_info.get("function_name", "");
        input = build_function_input_from_file(file_path, function_name, None, tests_root, None);
        if "error" in input {
            continue;
        }

        profile = profile_code(
            input["source_code"],
            input["function_call"]
        );
        if not profile.get("success", False) {
            continue;
        }

        source_segment = function_info.get("source_segment", input["source_code"]);
        complexity = compute_complexity(source_segment);

        entry = {
            "function_name": function_name,
            "function_call": input["function_call"],
            "median_ms": float(profile.get("median_ms", 0.0)),
            "peak_memory_kb": float(profile.get("peak_memory_kb", 0.0)),
            "cyclomatic_complexity": int(complexity.get("cyclomatic_complexity", 0)),
            "discovered_test_files": input.get("extra", {}).get("discovered_test_files", []),
            "discovered_test_count": len(input.get("extra", {}).get("discovered_test_files", [])),
            "source_file": input.get("extra", {}).get("source_file", file_path)
        };
        ranked = _insert_ranked(ranked, entry);
    }

    if len(ranked) <= limit {
        return ranked;
    }
    return ranked[:limit];
}


def:pub rank_replay_candidates_in_file(
    file_path: str,
    script_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    replay_inputs = build_replay_inputs_from_script(file_path, script_path, tests_root, None, None);
    candidates = replay_inputs.get("candidate_inputs", []);
    ranked: list = [];

    for input in candidates {
        function_name = input.get("function_name", "");
        profile = profile_code(
            input["source_code"],
            input["function_call"]
        );
        if not profile.get("success", False) {
            continue;
        }

        source_segment = input.get("extra", {}).get("discovered_function", {}).get(
            "source_segment",
            input["source_code"]
        );
        complexity = compute_complexity(source_segment);
        replay_trace = input.get("extra", {}).get("replay_trace", {});
        test_cases = input.get("test_cases", []);
        unique_calls: list = [];
        for case in test_cases {
            call_expr = case.get("call", None);
            if call_expr is not None and call_expr not in unique_calls {
                unique_calls.append(call_expr);
            }
        }

        entry = {
            "function_name": function_name,
            "function_call": input["function_call"],
            "median_ms": float(profile.get("median_ms", 0.0)),
            "peak_memory_kb": float(profile.get("peak_memory_kb", 0.0)),
            "cyclomatic_complexity": int(complexity.get("cyclomatic_complexity", 0)),
            "discovered_test_files": input.get("extra", {}).get("discovered_test_files", []),
            "discovered_test_count": len(input.get("extra", {}).get("discovered_test_files", [])),
            "source_file": input.get("extra", {}).get("source_file", file_path),
            "replay_trace_count": int(replay_trace.get("trace_count", 0)),
            "replay_unique_call_count": len(unique_calls),
            "replay_partial_success": bool(replay_trace.get("partial_success", False)),
            "replay_script": replay_inputs.get("replay_script", script_path)
        };
        entry["selection_score"] = _replay_ranking_score(entry);
        ranked = _insert_replay_ranked(ranked, entry);
    }

    if len(ranked) <= limit {
        return ranked;
    }
    return ranked[:limit];
}


def:pub rank_replay_candidates_in_directory(
    source_root: str,
    script_path: str,
    tests_root: str = "tests",
    limit: int = 10
) -> list {
    replay_inputs = build_replay_inputs_from_directory(source_root, script_path, tests_root, None);
    candidates = replay_inputs.get("candidate_inputs", []);
    ranked: list = [];

    for input in candidates {
        function_name = input.get("function_name", "");
        profile = profile_code(
            input["source_code"],
            input["function_call"]
        );
        if not profile.get("success", False) {
            continue;
        }

        source_segment = input.get("extra", {}).get("discovered_function", {}).get(
            "source_segment",
            input["source_code"]
        );
        complexity = compute_complexity(source_segment);
        replay_trace = input.get("extra", {}).get("replay_trace", {});
        test_cases = input.get("test_cases", []);
        unique_calls: list = [];
        for case in test_cases {
            call_expr = case.get("call", None);
            if call_expr is not None and call_expr not in unique_calls {
                unique_calls.append(call_expr);
            }
        }

        entry = {
            "function_name": function_name,
            "function_call": input["function_call"],
            "median_ms": float(profile.get("median_ms", 0.0)),
            "peak_memory_kb": float(profile.get("peak_memory_kb", 0.0)),
            "cyclomatic_complexity": int(complexity.get("cyclomatic_complexity", 0)),
            "discovered_test_files": input.get("extra", {}).get("discovered_test_files", []),
            "discovered_test_count": len(input.get("extra", {}).get("discovered_test_files", [])),
            "source_file": input.get("extra", {}).get("source_file", source_root),
            "replay_trace_count": int(replay_trace.get("trace_count", 0)),
            "replay_unique_call_count": len(unique_calls),
            "replay_partial_success": bool(replay_trace.get("partial_success", False)),
            "replay_script": replay_inputs.get("replay_script", script_path)
        };
        entry["selection_score"] = _replay_ranking_score(entry);
        ranked = _insert_replay_ranked(ranked, entry);
    }

    if len(ranked) <= limit {
        return ranked;
    }
    return ranked[:limit];
}
