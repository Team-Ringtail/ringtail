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
    input = build_function_input_from_file(file_path, function_name, None, tests_root, analysis_mode);
    if "error" in input {
        return input;
    }

    mod = importlib.import_module("src.core.replay_tracer");
    trace_fn = getattr(mod, "trace_replay_cases_from_script");
    trace_result = trace_fn(file_path, function_name, script_path);
    if not trace_result.get("success", False) {
        input["extra"]["replay_trace"] = trace_result;
        return input;
    }

    replay_cases = trace_result.get("test_cases", []);
    input["test_cases"] = replay_cases;
    if len(replay_cases) > 0 {
        input["function_call"] = replay_cases[0]["call"];
    }
    input["extra"]["replay_trace"] = trace_result;
    input["extra"]["replay_script"] = os.path.abspath(script_path);
    return input;
}
