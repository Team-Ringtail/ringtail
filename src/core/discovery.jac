"""
Helpers for building Ringtail inputs from normal Python files.

This is intentionally lightweight: single-file function discovery, simple
call inference, and heuristic pytest-style test file discovery.
"""

import os;
import re;
import importlib;
import from src.utils.code_parser { list_functions, parse_function }


def _read_file(path: str) -> str {
    with open(path, "r") as f {
        return f.read();
    }
}


def:pub discover_functions_in_file(file_path: str) -> list {
    source_code = _read_file(file_path);
    return list_functions(source_code, "python");
}


def:pub discover_python_files(root_dir: str) -> list {
    matches: list = [];
    abs_root = os.path.abspath(root_dir);
    for (dirpath, dirs, files) in os.walk(abs_root) {
        next_dirs: list = [];
        for dname in dirs {
            lower_name = dname.lower();
            if (
                lower_name == "__pycache__"
                or lower_name == ".git"
                or lower_name == ".venv"
                or lower_name == "venv"
                or lower_name == "node_modules"
                or lower_name == "tests"
            ) {
                continue;
            }
            next_dirs.append(dname);
        }
        dirs[:] = next_dirs;

        for fname in files {
            if not fname.endswith(".py") {
                continue;
            }
            if fname.startswith("test_") {
                continue;
            }
            matches.append(os.path.abspath(os.path.join(dirpath, fname)));
        }
    }
    return matches;
}


def _module_to_file_candidates(source_root: str, module_name: str) -> list {
    candidates: list = [];
    module_path = module_name.replace(".", os.sep);
    file_candidate = os.path.abspath(os.path.join(source_root, module_path + ".py"));
    package_candidate = os.path.abspath(os.path.join(source_root, module_path, "__init__.py"));
    if os.path.exists(file_candidate) {
        candidates.append(file_candidate);
    }
    if os.path.exists(package_candidate) and package_candidate not in candidates {
        candidates.append(package_candidate);
    }
    return candidates;
}


def:pub infer_replay_source_files(source_root: str, script_path: str) -> list {
    abs_root = os.path.abspath(source_root);
    content = _read_file(script_path);
    inferred: list = [];

    import_matches = re.findall(r"(?m)^\s*import\s+([A-Za-z0-9_.,\s]+)", content);
    for match in import_matches {
        for raw_module in str(match).split(",") {
            module_name = str(raw_module).strip();
            if " as " in module_name {
                module_name = module_name.split(" as ")[0].strip();
            }
            if module_name == "" {
                continue;
            }
            for candidate in _module_to_file_candidates(abs_root, module_name) {
                inferred = _maybe_add_match(inferred, candidate);
            }
        }
    }

    from_matches = re.findall(r"(?m)^\s*from\s+([A-Za-z0-9_.]+)\s+import\s+", content);
    for module_name in from_matches {
        if str(module_name).startswith(".") {
            continue;
        }
        for candidate in _module_to_file_candidates(abs_root, str(module_name)) {
            inferred = _maybe_add_match(inferred, candidate);
        }
    }

    return inferred;
}


def _render_literal(value: any) -> str {
    if value is None {
        return "None";
    }
    if type(value) is str {
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'";
    }
    return str(value);
}


def _sample_value_for_type(type_name: str | None) -> str {
    if type_name is None or type_name == "" {
        return "1";
    }

    lower = type_name.lower();
    if "int" in lower {
        return "1";
    }
    if "float" in lower {
        return "1.0";
    }
    if "bool" in lower {
        return "True";
    }
    if "str" in lower {
        return "'sample'";
    }
    if "list" in lower or "sequence" in lower or "iterable" in lower {
        return "[]";
    }
    if "dict" in lower or "mapping" in lower {
        return "{}";
    }
    if "set" in lower {
        return "set()";
    }
    if "tuple" in lower {
        return "()";
    }
    if "optional" in lower {
        return "None";
    }
    return "1";
}


def:pub infer_function_call(function_info: dict) -> str {
    function_name = function_info.get("function_name", "");
    params = function_info.get("parameters", []);
    args: list = [];

    for param in params {
        kind = str(param.get("kind", "positional"));
        if kind == "vararg" or kind == "kwargs" {
            continue;
        }

        default_value = param.get("default", None);
        if default_value is not None {
            rendered = _render_literal(default_value);
        } else {
            rendered = _sample_value_for_type(param.get("type", None));
        }

        if kind == "kwonly" {
            args.append(str(param.get("name", "")) + "=" + rendered);
        } else {
            args.append(rendered);
        }
    }

    return function_name + "(" + ", ".join(args) + ")";
}


def _maybe_add_match(matches: list, path: str) -> list {
    if path not in matches {
        matches.append(path);
    }
    return matches;
}


def:pub discover_tests_for_function(
    source_file_path: str,
    function_name: str,
    tests_root: str = "tests"
) -> list {
    matches: list = [];
    abs_tests_root = os.path.abspath(tests_root);
    if not os.path.exists(abs_tests_root) {
        return matches;
    }

    module_name = os.path.splitext(os.path.basename(source_file_path))[0];
    call_pattern = function_name + "(";
    import_pattern = "import " + function_name;
    module_import_pattern = "from " + module_name + " import " + function_name;

    for (dirpath, dirs, files) in os.walk(abs_tests_root) {
        for fname in files {
            if not fname.endswith(".py") {
                continue;
            }

            test_path = os.path.join(dirpath, fname);
            matched = False;
            lower_name = fname.lower();
            if function_name.lower() in lower_name or module_name.lower() in lower_name {
                matched = True;
            } else {
                try {
                    content = _read_file(test_path);
                    if (
                        call_pattern in content
                        or import_pattern in content
                        or module_import_pattern in content
                    ) {
                        matched = True;
                    }
                } except Exception {
                    matched = False;
                }
            }

            if matched {
                matches = _maybe_add_match(matches, os.path.abspath(test_path));
            }
        }
    }

    return matches;
}


def:pub build_function_input_from_file(
    file_path: str,
    function_name: str,
    function_call: str | None = None,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    abs_path = os.path.abspath(file_path);
    source_code = _read_file(abs_path);
    function_info = parse_function(source_code, "python", function_name);

    resolved_name = function_info.get("function_name", "");
    if resolved_name == "" {
        return {
            "error": "Could not find function '" + function_name + "' in " + abs_path
        };
    }

    call_expr = function_call;
    if call_expr is None or call_expr == "" {
        call_expr = infer_function_call(function_info);
    }

    discovered_tests = discover_tests_for_function(abs_path, resolved_name, tests_root);

    return {
        "source_code": source_code,
        "function_name": resolved_name,
        "function_call": call_expr,
        "language": "python",
        "test_cases": [],
        "analysis_mode": analysis_mode,
        "extra": {
            "source_file": abs_path,
            "discovered_test_files": discovered_tests,
            "discovered_function": function_info
        }
    };
}


def:pub build_function_input_from_replay_script(
    file_path: str,
    function_name: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    session = build_replay_inputs_from_script(
        file_path,
        script_path,
        tests_root,
        analysis_mode,
        [function_name]
    );
    candidates = session.get("candidate_inputs", []);
    if len(candidates) > 0 {
        return candidates[0];
    }

    input = build_function_input_from_file(file_path, function_name, None, tests_root, analysis_mode);
    if "error" in input {
        return input;
    }

    trace_result = session.get("replay_trace", {}).get("functions", {}).get(
        function_name,
        session.get("replay_trace", {})
    );
    input["extra"]["replay_trace"] = trace_result;
    input["extra"]["replay_trace_session"] = session.get("replay_trace", {});
    input["extra"]["replay_script"] = os.path.abspath(script_path);
    input["extra"]["replay_partial_success"] = bool(trace_result.get("partial_success", False));
    return input;
}


def:pub build_replay_inputs_from_script(
    file_path: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None,
    function_names: list | None = None
) -> dict {
    discovered = discover_functions_in_file(file_path);
    selected_names: list = [];

    if function_names is None or len(function_names) == 0 {
        for fn in discovered {
            name = str(fn.get("function_name", ""));
            if name != "" {
                selected_names.append(name);
            }
        }
    } else {
        for name in function_names {
            selected_names.append(str(name));
        }
    }

    mod = importlib.import_module("src.core.replay_tracer");
    trace_fn = getattr(mod, "trace_replay_session_from_script");
    trace_result = trace_fn(file_path, selected_names, script_path);

    candidate_inputs: list = [];
    observed_names: list = [];
    traces = trace_result.get("functions", {});
    for function_info in discovered {
        function_name = str(function_info.get("function_name", ""));
        if function_name == "" or function_name not in traces {
            continue;
        }

        fn_trace = traces.get(function_name, {});
        if int(fn_trace.get("trace_count", 0)) <= 0 {
            continue;
        }

        observed_names.append(function_name);
        input = build_function_input_from_file(file_path, function_name, None, tests_root, analysis_mode);
        if "error" in input {
            continue;
        }

        replay_cases = fn_trace.get("test_cases", []);
        input["test_cases"] = replay_cases;
        if len(replay_cases) > 0 {
            input["function_call"] = replay_cases[0]["call"];
        }
        input["extra"]["replay_trace"] = fn_trace;
        input["extra"]["replay_trace_session"] = trace_result;
        input["extra"]["replay_script"] = os.path.abspath(script_path);
        input["extra"]["replay_partial_success"] = bool(fn_trace.get("partial_success", False));
        candidate_inputs.append(input);
    }

    return {
        "source_file": os.path.abspath(file_path),
        "replay_script": os.path.abspath(script_path),
        "replay_trace": trace_result,
        "candidate_inputs": candidate_inputs,
        "candidate_count": len(candidate_inputs),
        "traced_function_names": selected_names,
        "observed_function_names": observed_names
    };
}


def:pub build_replay_inputs_from_files(
    file_paths: list,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    abs_files: list = [];
    file_functions: dict = {};
    for file_path in file_paths {
        abs_path = os.path.abspath(str(file_path));
        if abs_path == os.path.abspath(script_path) {
            continue;
        }
        discovered = discover_functions_in_file(abs_path);
        file_functions[abs_path] = discovered;
        abs_files.append(abs_path);
    }

    function_names_by_source: dict = {};
    for abs_path in abs_files {
        selected_names: list = [];
        for fn in file_functions.get(abs_path, []) {
            name = str(fn.get("function_name", ""));
            if name != "" {
                selected_names.append(name);
            }
        }
        function_names_by_source[abs_path] = selected_names;
    }

    mod = importlib.import_module("src.core.replay_tracer");
    trace_fn = getattr(mod, "trace_replay_repo_session_from_script");
    trace_result = trace_fn(abs_files, script_path, function_names_by_source);

    candidate_inputs: list = [];
    observed_names: list = [];
    observed_files: list = [];
    source_results = trace_result.get("sources", {});
    for abs_path in abs_files {
        source_trace = source_results.get(abs_path, {});
        if int(source_trace.get("trace_count", 0)) <= 0 {
            continue;
        }
        observed_files.append(abs_path);
        for function_info in file_functions.get(abs_path, []) {
            function_name = str(function_info.get("function_name", ""));
            if function_name == "" {
                continue;
            }
            fn_trace = source_trace.get("functions", {}).get(function_name, {});
            if int(fn_trace.get("trace_count", 0)) <= 0 {
                continue;
            }

            observed_names.append(abs_path + "::" + function_name);
            input = build_function_input_from_file(abs_path, function_name, None, tests_root, analysis_mode);
            if "error" in input {
                continue;
            }

            replay_cases = fn_trace.get("test_cases", []);
            input["test_cases"] = replay_cases;
            if len(replay_cases) > 0 {
                input["function_call"] = replay_cases[0]["call"];
            }
            input["extra"]["replay_trace"] = fn_trace;
            input["extra"]["replay_trace_source"] = source_trace;
            input["extra"]["replay_trace_session"] = trace_result;
            input["extra"]["replay_script"] = os.path.abspath(script_path);
            input["extra"]["replay_partial_success"] = bool(fn_trace.get("partial_success", False));
            candidate_inputs.append(input);
        }
    }

    return {
        "source_files": abs_files,
        "replay_script": os.path.abspath(script_path),
        "replay_trace": trace_result,
        "candidate_inputs": candidate_inputs,
        "candidate_count": len(candidate_inputs),
        "traced_source_files": abs_files,
        "observed_source_files": observed_files,
        "observed_function_keys": observed_names
    };
}


def:pub build_replay_inputs_from_directory(
    source_root: str,
    script_path: str,
    tests_root: str = "tests",
    analysis_mode: str | None = None
) -> dict {
    inferred_source_files = infer_replay_source_files(source_root, script_path);
    source_files = inferred_source_files;
    selection_mode = "inferred_imports";
    if len(source_files) == 0 {
        source_files = discover_python_files(source_root);
        selection_mode = "directory_scan";
    }

    result = build_replay_inputs_from_files(
        source_files,
        script_path,
        tests_root,
        analysis_mode
    );
    result["inferred_source_files"] = inferred_source_files;
    result["source_selection_mode"] = selection_mode;
    return result;
}
