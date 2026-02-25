"""
Unit testing utilities.

Runs a pytest-compatible test file against submitted Python solution code
in an isolated subprocess. Returns structured pass/fail results as a dict.
Optionally measures line coverage via coverage.py.
"""

import subprocess;
import tempfile;
import os;
import re;
import json;
import sys;


glob _EMPTY_RESULT: dict = {
    "passed": False,
    "total": 0,
    "passed_count": 0,
    "failed_count": 0,
    "failures": [],
    "error": ""
};


def _make_fail(msg: str) -> dict {
    result = dict(_EMPTY_RESULT);
    result["failures"] = [];
    result["error"] = msg;
    return result;
}


"""Remove a directory tree without importing shutil."""
def _rmtree(path: str) -> None {
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


"""Parse pytest --tb=line -q --no-header output into a structured dict."""
def _parse_pytest_output(stdout: str, stderr: str, returncode: int) -> dict {
    failures: list = [];
    passed_count = 0;
    failed_count = 0;

    for line in stdout.splitlines() {
        fail_match = re.match(r"FAILED\s+\S+::(\S+)\s*-\s*(.*)", line);
        if fail_match {
            failures.append({
                "test": fail_match.group(1),
                "message": fail_match.group(2).strip()
            });
        }
    }

    summary_match = re.search(r"(\d+)\s+passed", stdout);
    if summary_match {
        passed_count = int(summary_match.group(1));
    }

    fail_summary = re.search(r"(\d+)\s+failed", stdout);
    if fail_summary {
        failed_count = int(fail_summary.group(1));
    }

    error_match = re.search(r"(\d+)\s+error", stdout);
    error_count = int(error_match.group(1)) if error_match else 0;

    total = passed_count + failed_count + error_count;

    if total == 0 and returncode != 0 {
        error_msg = stderr.strip() or stdout.strip();
        return _make_fail(error_msg);
    }

    error_msg = "";
    if error_count > 0 {
        error_lines = [
            line for line in stdout.splitlines()
            if line.startswith("E ") or "Error" in line
        ];
        if error_lines {
            error_msg = error_lines[-1].strip();
        } else {
            error_msg = f"{error_count} collection error(s)";
        }
    }

    return {
        "passed": failed_count == 0 and error_count == 0 and returncode == 0,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failures": failures,
        "error": error_msg
    };
}


"""Run pytest tests against a Python solution in an isolated subprocess.

    :param code: Python source code containing the solution.
    :param test_code: pytest-compatible test file content (should import from solution).
    :param timeout_seconds: Max wall-clock seconds before the subprocess is killed.
    :returns: dict with keys: passed (bool), total (int), passed_count (int),
              failed_count (int), failures (list of dicts), error (str).
"""
def run_tests(
    code: str,
    test_code: str,
    timeout_seconds: int = 60
) -> dict {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_test_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    test_path = os.path.join(tmp_dir, "test_solution.py");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }
        with open(test_path, "w") as f {
            f.write(test_code);
        }

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_solution.py",
             "--tb=line", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        return _parse_pytest_output(result.stdout, result.stderr, result.returncode);
    } except subprocess.TimeoutExpired {
        return _make_fail(f"Tests timed out after {timeout_seconds}s");
    } except Exception as e {
        return _make_fail(str(e));
    } finally {
        for fname in ["solution.py", "test_solution.py",
                       "__pycache__", ".pytest_cache"] {
            p = os.path.join(tmp_dir, fname);
            if os.path.isfile(p) {
                os.remove(p);
            } elif os.path.isdir(p) {
                _rmtree(p);
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}


"""Parse coverage.json produced by coverage.py for the solution file."""
def _parse_coverage_json(coverage_path: str) -> dict {
    try {
        with open(coverage_path, "r") as f {
            data = json.load(f);
        }
    } except (FileNotFoundError, json.JSONDecodeError) {
        return {"coverage_percent": 0.0, "covered_lines": [], "missing_lines": []};
    }

    files = data.get("files", {});
    # Find solution.py entry (key may be absolute or relative)
    sol_data = None;
    for key in files {
        if "solution.py" in key {
            sol_data = files[key];
            break;
        }
    }
    if sol_data is None {
        return {"coverage_percent": 0.0, "covered_lines": [], "missing_lines": []};
    }

    summary = sol_data.get("summary", {});
    pct = summary.get("percent_covered", 0.0);
    executed = sol_data.get("executed_lines", []);
    missing = sol_data.get("missing_lines", []);

    return {
        "coverage_percent": pct,
        "covered_lines": executed,
        "missing_lines": missing
    };
}


"""Run pytest tests with coverage measurement via pytest-cov.

    Single subprocess call: ``pytest --cov=. --cov-report=json:coverage.json``.

    :param code: Python source code containing the solution.
    :param test_code: pytest-compatible test file content (should import from solution).
    :param timeout_seconds: Max wall-clock seconds before the subprocess is killed.
    :returns: dict with test results plus coverage_percent, covered_lines, missing_lines.
"""
def run_tests_with_coverage(
    code: str,
    test_code: str,
    timeout_seconds: int = 60
) -> dict {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_covtest_");
    solution_path = os.path.join(tmp_dir, "solution.py");
    test_path = os.path.join(tmp_dir, "test_solution.py");
    coverage_json_path = os.path.join(tmp_dir, "coverage.json");

    try {
        with open(solution_path, "w") as f {
            f.write(code);
        }
        with open(test_path, "w") as f {
            f.write(test_code);
        }

        # Single subprocess: pytest-cov handles coverage + test execution
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_solution.py",
             "--cov=.", "--cov-report=json:coverage.json",
             "--cov-config=/dev/null",
             "--tb=line", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=tmp_dir
        );

        test_result = _parse_pytest_output(result.stdout, result.stderr, result.returncode);

        cov = _parse_coverage_json(coverage_json_path);
        test_result["coverage_percent"] = cov["coverage_percent"];
        test_result["covered_lines"] = cov["covered_lines"];
        test_result["missing_lines"] = cov["missing_lines"];

        return test_result;
    } except subprocess.TimeoutExpired {
        return {
            "passed": False, "total": 0, "passed_count": 0,
            "failed_count": 0, "failures": [],
            "error": f"Tests timed out after {timeout_seconds}s",
            "coverage_percent": 0.0, "covered_lines": [], "missing_lines": []
        };
    } except Exception as e {
        return {
            "passed": False, "total": 0, "passed_count": 0,
            "failed_count": 0, "failures": [],
            "error": str(e),
            "coverage_percent": 0.0, "covered_lines": [], "missing_lines": []
        };
    } finally {
        for fname in ["solution.py", "test_solution.py", "coverage.json",
                       ".coverage", "__pycache__", ".pytest_cache"] {
            p = os.path.join(tmp_dir, fname);
            if os.path.isfile(p) {
                os.remove(p);
            } elif os.path.isdir(p) {
                _rmtree(p);
            }
        }
        try {
            os.rmdir(tmp_dir);
        } except OSError {
            ;
        }
    }
}
