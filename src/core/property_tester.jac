"""Automated property-based testing via Hypothesis.

Uses hypothesis.strategies.from_type() for automatic strategy inference
from type annotations. Generates a pytest file, runs it in a subprocess,
and parses results. When a reference implementation is supplied, asserts
functional equivalence across all generated inputs.
"""

import ast;
import os;
import re;
import subprocess;
import sys;
import tempfile;
import from typing { Any, Dict, List, Optional }


"""Parse a function's parameters and type annotations from source."""
def _extract_params(source_code: str, function_name: str) -> list {
    try {
        tree = ast.parse(source_code);
    } except SyntaxError {
        return [];
    }

    for node in ast.walk(tree) {
        if isinstance(node, ast.FunctionDef) and node.name == function_name {
            params = [];
            for arg in node.args.args {
                if arg.arg == "self" {
                    continue;
                }
                annotation = None;
                if arg.annotation and hasattr(ast, "unparse") {
                    annotation = ast.unparse(arg.annotation);
                }
                params.append({"name": arg.arg, "annotation": annotation});
            }
            return params;
        }
    }

    return [];
}


def _extract_import_lines(source_code: str) -> list {
    try {
        tree = ast.parse(source_code);
    } except SyntaxError {
        return [];
    }

    imports = [];
    for node in tree.body {
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom) {
            if hasattr(ast, "unparse") {
                import_line = ast.unparse(node);
                if not import_line.startswith("from __future__") {
                    imports.append(import_line);
                }
            }
        }
    }
    return imports;
}


def _has_function_definition(source_code: str, function_name: str) -> bool {
    try {
        tree = ast.parse(source_code);
    } except SyntaxError {
        return False;
    }

    for node in ast.walk(tree) {
        if isinstance(node, ast.FunctionDef) and node.name == function_name {
            return True;
        }
    }
    return False;
}


"""Build a pytest file using Hypothesis from_type() for strategy inference."""
def _generate_test_file(
    function_name: str,
    params: list,
    import_lines: list,
    has_reference: bool,
    max_examples: int
) -> str {
    lines = [
        "from hypothesis import given, strategies as st, settings",
        "from hypothesis.strategies import from_type",
        "from typing import *",
        "import typing",
        "import math",
        ""
    ];

    for import_line in import_lines {
        if import_line != "" {
            lines.append(import_line);
        }
    }
    if len(import_lines) > 0 {
        lines.append("");
    }

    lines.append("def _fallback_strategy():");
    lines.append("    return st.integers(min_value=-1000, max_value=1000)");
    lines.append("");
    lines.append("def _normalized_annotation(annotation_text):");
    lines.append("    if annotation_text is None:");
    lines.append("        return ''");
    lines.append("    return str(annotation_text).replace('typing.', '').strip()");
    lines.append("");
    lines.append("def _safe_strategy(annotation_text):");
    lines.append("    normalized = _normalized_annotation(annotation_text)");
    lines.append("    if normalized == '':");
    lines.append("        return _fallback_strategy()");
    lines.append("    if normalized == 'int':");
    lines.append("        return st.integers(min_value=-20, max_value=20)");
    lines.append("    if normalized == 'float':");
    lines.append("        return st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)");
    lines.append("    if normalized == 'bool':");
    lines.append("        return st.booleans()");
    lines.append("    if normalized == 'str':");
    lines.append("        return st.text(max_size=20)");
    lines.append("    if normalized.startswith('Optional[') and normalized.endswith(']'):");
    lines.append("        inner = normalized[len('Optional['):-1]");
    lines.append("        return st.one_of(st.none(), _safe_strategy(inner))");
    lines.append("    if normalized.startswith('list[') and normalized.endswith(']'):");
    lines.append("        inner = normalized[len('list['):-1]");
    lines.append("        return st.lists(_safe_strategy(inner), max_size=8)");
    lines.append("    if normalized.startswith('List[') and normalized.endswith(']'):");
    lines.append("        inner = normalized[len('List['):-1]");
    lines.append("        return st.lists(_safe_strategy(inner), max_size=8)");
    lines.append("    if normalized.startswith('set[') and normalized.endswith(']'):");
    lines.append("        inner = normalized[len('set['):-1]");
    lines.append("        return st.sets(_safe_strategy(inner), max_size=8)");
    lines.append("    if normalized.startswith('Set[') and normalized.endswith(']'):");
    lines.append("        inner = normalized[len('Set['):-1]");
    lines.append("        return st.sets(_safe_strategy(inner), max_size=8)");
    lines.append("    try:");
    lines.append("        return from_type(eval(annotation_text, globals(), locals()))");
    lines.append("    except Exception:");
    lines.append("        return _fallback_strategy()");
    lines.append("");

    if has_reference {
        lines.append("from solution import %s as optimized_fn" % function_name);
        lines.append("from reference import %s as reference_fn" % function_name);
    } else {
        lines.append("from solution import %s" % function_name);
    }

    lines.append("");

    strategy_args = [];
    param_names = [];
    for p in params {
        ann = p["annotation"];
        strategy = "_safe_strategy(%r)" % ann;
        strategy_args.append("%s=%s" % (p["name"], strategy));
        param_names.append(p["name"]);
    }

    settings_decorator = "@settings(max_examples=%d, deadline=None)" % max_examples;

    if len(strategy_args) > 0 {
        given_decorator = "@given(%s)" % ", ".join(strategy_args);
        lines.append(settings_decorator);
        lines.append(given_decorator);
    }
    lines.append("def test_no_crash(%s):" % ", ".join(param_names));
    if has_reference {
        lines.append("    optimized_fn(%s)" % ", ".join(param_names));
    } else {
        lines.append("    %s(%s)" % (function_name, ", ".join(param_names)));
    }
    lines.append("");

    if has_reference {
        if len(strategy_args) > 0 {
            given_decorator = "@given(%s)" % ", ".join(strategy_args);
            lines.append(settings_decorator);
            lines.append(given_decorator);
        }
        lines.append("def test_matches_reference(%s):" % ", ".join(param_names));
        lines.append("    result_opt = optimized_fn(%s)" % ", ".join(param_names));
        lines.append("    result_ref = reference_fn(%s)" % ", ".join(param_names));
        lines.append("    if isinstance(result_ref, float) and isinstance(result_opt, float):");
        lines.append("        if math.isnan(result_ref):");
        lines.append("            assert math.isnan(result_opt)");
        lines.append("        else:");
        lines.append("            assert abs(result_opt - result_ref) < 1e-9 or result_opt == result_ref");
        lines.append("    else:");
        lines.append("        assert result_opt == result_ref");
        lines.append("");
    }

    return "\n".join(lines);
}

"""Run Hypothesis property-based tests on a Python function.

Uses from_type() to auto-infer strategies from type annotations.
When reference_code is provided, asserts the optimized version
produces identical output for all generated inputs.
"""
def run_property_tests(
    code: str,
    function_name: str,
    reference_code: str = None,
    max_examples: int = 100,
    timeout_seconds: int = 60
) -> dict {
    empty_result = {
        "passed": False,
        "total": 0,
        "passed_count": 0,
        "failed_count": 0,
        "failures": [],
        "error": "",
        "examples_run": max_examples
    };

    params = _extract_params(code, function_name);
    function_found = _has_function_definition(code, function_name);
    if not function_found {
        try {
            tree = ast.parse(code);
            for node in ast.walk(tree) {
                if isinstance(node, ast.FunctionDef) {
                    params = _extract_params(code, node.name);
                    if _has_function_definition(code, node.name) {
                        function_name = node.name;
                        function_found = True;
                        break;
                    }
                }
            }
        } except SyntaxError {
            ;
        }
    }

    if not function_found {
        empty_result["error"] = "Could not extract parameters from function";
        return empty_result;
    }

    has_reference = reference_code is not None;
    import_lines = _extract_import_lines(code);
    test_src = _generate_test_file(function_name, params, import_lines, has_reference, max_examples);

    tmp_dir = tempfile.mkdtemp(prefix="ringtail_proptest_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    test_path = os.path.join(tmp_dir, "test_property.py");
    reference_path = os.path.join(tmp_dir, "reference.py");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }
        with open(test_path, "w") as f {
            f.write(test_src);
        }
        if has_reference {
            with open(reference_path, "w") as f {
                f.write(reference_code);
            }
        }

        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", "test_property.py",
                "--tb=short", "-q", "--no-header"
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        return _parse_output(result.stdout, result.stderr, result.returncode, max_examples);

    } except subprocess.TimeoutExpired as e {
        # Include captured output in the error message to aid debugging.
        # TimeoutExpired on subprocess.run exposes `output` and `stderr` attributes.
        out = getattr(e, "output", "") or "";
        err = getattr(e, "stderr", "") or "";
        empty_result["error"] = (
            "Property tests timed out after %ds; stdout=%r stderr=%r"
            % (timeout_seconds, out, err)
        );
        return empty_result;
    } except Exception as e {
        # Surface full exception string for easier diagnosis.
        empty_result["error"] = str(e);
        return empty_result;
    } finally {
        for fname in os.listdir(tmp_dir) {
            fpath = os.path.join(tmp_dir, fname);
            if os.path.isfile(fpath) {
                os.remove(fpath);
            } elif os.path.isdir(fpath) {
                _rmtree_safe(fpath);
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}

"""Parse pytest output from property test run."""
def _parse_output(stdout: str, stderr: str, returncode: int, max_examples: int) -> dict {
    failures = [];
    passed_count = 0;
    failed_count = 0;
    falsifying_example = "";

    for line in stdout.splitlines() {
        fail_match = re.match(r"FAILED\s+\S+::(\S+)", line);
        if fail_match {
            failures.append({
                "test": fail_match.group(1),
                "message": line.strip()
            });
        }
    }

    summary_pass = re.search(r"(\d+)\s+passed", stdout);
    if summary_pass {
        passed_count = int(summary_pass.group(1));
    }

    summary_fail = re.search(r"(\d+)\s+failed", stdout);
    if summary_fail {
        failed_count = int(summary_fail.group(1));
    }

    total = passed_count + failed_count;
    error_msg = "";

    if total == 0 and returncode != 0 {
        error_msg = stderr.strip() or stdout.strip();
    }

    falsifying_match = re.search(r"Falsifying example:(.*?)(?:\n=+|\Z)", stdout, re.DOTALL);
    if falsifying_match {
        falsifying_example = falsifying_match.group(1).strip();
    }
    if falsifying_example != "" and len(failures) > 0 {
        failures[-1]["falsifying_example"] = falsifying_example;
    }

    return {
        "passed": failed_count == 0 and returncode == 0 and total > 0,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failures": failures,
        "error": error_msg,
        "examples_run": max_examples,
        "falsifying_example": falsifying_example,
        "stdout": stdout,
        "stderr": stderr
    };
}


"""Remove directory tree without shutil."""
def _rmtree_safe(path: str) -> None {
    for (dirpath, dirs, files) in os.walk(path, topdown=False) {
        for f in files {
            os.remove(os.path.join(dirpath, f));
        }
        for d in dirs {
            os.rmdir(os.path.join(dirpath, d));
        }
    }
    os.rmdir(path);
}
