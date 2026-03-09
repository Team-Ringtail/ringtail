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


"""Build a pytest file using Hypothesis from_type() for strategy inference."""
def _generate_test_file(
    function_name: str,
    params: list,
    has_reference: bool,
    max_examples: int
) -> str {
    lines = [
        "from hypothesis import given, strategies as st, settings, assume",
        "from hypothesis.strategies import from_type",
        "import math",
        ""
    ];

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
        if ann is not None {
            strategy = "from_type(%s)" % ann;
        } else {
            strategy = "st.integers(min_value=-1000, max_value=1000)";
        }
        strategy_args.append("%s=%s" % (p["name"], strategy));
        param_names.append(p["name"]);
    }

    given_decorator = "@given(%s)" % ", ".join(strategy_args);
    settings_decorator = "@settings(max_examples=%d, deadline=None)" % max_examples;

    lines.append(settings_decorator);
    lines.append(given_decorator);
    lines.append("def test_no_crash(%s):" % ", ".join(param_names));
    if has_reference {
        lines.append("    optimized_fn(%s)" % ", ".join(param_names));
    } else {
        lines.append("    %s(%s)" % (function_name, ", ".join(param_names)));
    }
    lines.append("");

    if has_reference {
        lines.append(settings_decorator);
        lines.append(given_decorator);
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
    if not params {
        try {
            tree = ast.parse(code);
            for node in ast.walk(tree) {
                if isinstance(node, ast.FunctionDef) {
                    params = _extract_params(code, node.name);
                    if params {
                        function_name = node.name;
                        break;
                    }
                }
            }
        } except SyntaxError {
            ;
        }
    }

    if not params {
        empty_result["error"] = "Could not extract parameters from function";
        return empty_result;
    }

    has_reference = reference_code is not None;
    test_src = _generate_test_file(function_name, params, has_reference, max_examples);

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

    falsifying = re.search(r"Falsifying example:.*?\n(.*?)$", stdout, re.MULTILINE);
    if falsifying and failures {
        failures[-1]["falsifying_example"] = falsifying.group(1).strip();
    }

    return {
        "passed": failed_count == 0 and returncode == 0 and total > 0,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failures": failures,
        "error": error_msg,
        "examples_run": max_examples
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
