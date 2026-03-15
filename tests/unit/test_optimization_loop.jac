"""Integration tests for run_optimization — happy path and error paths."""

import from src.core.optimization_loop { run_optimization, _pick_best_failure, _pytest_from_test_cases }


test "happy path optimization on simple Python function" {
    sample_code = "def slow_sum(n):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            total += i + j\n    return total";
    input = {
        "source_code": sample_code,
        "function_name": "slow_sum",
        "function_call": "slow_sum(10)",
        "language": "python",
        "test_cases": [{"call": "slow_sum(3)", "expected": 18}]
    };
    result = run_optimization(input, None, "test-fast");

    assert result["optimized_code"] is not None;
    assert result["optimized_code"] != "";
    assert "slow_sum" in result["optimized_code"];
    assert result["iteration_number"] >= 0;
    assert result["iteration_number"] <= 3;
    assert result["metrics"]["execution_time"] >= 0.0;
    assert result["metrics"]["memory_usage"] >= 0.0;
    assert "test_passed" in result;
    assert type(result["test_passed"]) is bool;
    assert "improvement_ratio" in result;
    assert type(result["improvement_ratio"]) is float;
    err = result.get("error", "");
    assert err == "" or err is None;
    assert "baseline_metrics" in result;
    assert "termination_reason" in result;
    assert "converged" in result;
}

test "missing function_call triggers validation error" {
    input = {
        "source_code": "def add(a, b): return a + b",
        "function_name": "add"
    };
    result = run_optimization(input);

    assert result["error"] is not None;
    assert result["error"] != "";
    assert "function_call" in result["error"];
    assert result["iteration_number"] == 0;
    assert result["test_passed"] is False;
}

test "profiling failure propagates error" {
    code = "def boom(): raise RuntimeError('kaboom')";
    input = {
        "source_code": code,
        "function_name": "boom",
        "function_call": "boom()",
        "language": "python",
        "test_cases": []
    };
    result = run_optimization(input);

    assert result["error"] is not None;
    assert result["error"] != "";
    assert "profiling" in result["error"].lower() or "baseline" in result["error"].lower();
    assert result["iteration_number"] == 0;
}

test "candidate-search profile evaluates multiple candidates" {
    sample_code = "def slow_sum(n):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            total += i + j\n    return total";
    input = {
        "source_code": sample_code,
        "function_name": "slow_sum",
        "function_call": "slow_sum(8)",
        "language": "python",
        "test_cases": [{"call": "slow_sum(3)", "expected": 18}]
    };
    result = run_optimization(input, None, "test-fast-candidate-search");

    assert result["candidate_count_evaluated"] == 2;
    assert "candidate_label" in result;
}

test "pick_best_failure prefers profiling over weaker failures" {
    failures = [
        {
            "feedback": {"type": "unit_test_failure"},
            "result": {"error": "Tests failed"}
        },
        {
            "feedback": {"type": "profiling_failure"},
            "result": {"error": "Profiling failed"}
        }
    ];

    picked = _pick_best_failure(failures);

    assert picked["feedback"]["type"] == "profiling_failure";
}

test "pytest generation normalizes replay case names for collection" {
    test_code = _pytest_from_test_cases(
        "echo",
        [{"name": "replay_case_0", "call": "echo(1)", "expected": "1"}],
        "echo(1)"
    );

    assert "def test_replay_case_0():" in test_code;
}

test "run_optimization respects explicit function_name in multi-function source" {
    sample_code = (
        "def fast_add(a, b):\n    return a + b\n\n"
        + "def sum_up(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
    );
    input = {
        "source_code": sample_code,
        "function_name": "sum_up",
        "function_call": "sum_up(5)",
        "language": "python",
        "test_cases": [{"call": "sum_up(3)", "expected": 3}]
    };

    result = run_optimization(input, None, "test-fast");

    assert "sum_up" in result["optimized_code"];
    assert result["test_passed"] is True;
}
