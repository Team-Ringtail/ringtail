"""
Lightweight function ranking using existing discovery, profiling, and complexity
signals. This is intentionally single-file and Python-focused.
"""

import from src.core.discovery { build_function_input_from_file, discover_functions_in_file }
import from src.core.profiler { profile_code }
import from src.utils.complexity { compute_complexity }


def _ranking_score(entry: dict) -> float {
    runtime_component = float(entry.get("median_ms", 0.0));
    complexity_component = float(entry.get("cyclomatic_complexity", 0));
    return runtime_component * 1000.0 + complexity_component;
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
            "source_file": input.get("extra", {}).get("source_file", file_path)
        };
        ranked = _insert_ranked(ranked, entry);
    }

    if len(ranked) <= limit {
        return ranked;
    }
    return ranked[:limit];
}
