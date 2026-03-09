"""Optional LLM-backed smoke tests for optimizer agent and optimization loop.

These tests are intended to be run manually by developers when an Anthropic
API key and client library are available. They are not part of the default
`jac test tests/unit/` suite.
"""

import from src.agents.optimizer_agent { think_and_prep, write_optimized_code };
import from src.core.optimization_loop { run_optimization };


test "think_and_prep llm mode returns plan dict" {
    source = "def slow_square(n):\n    total = 0\n    for i in range(n):\n        total += i * i\n    return total";
    criteria = {"performance_weight": 1.0, "code_quality_weight": 1.0, "functionality_weight": 1.0};
    function_call = "slow_square(10)";
    cases = [{"call": "slow_square(3)", "expected": 5}];

    plan = think_and_prep(
        source,
        criteria,
        function_call,
        cases,
        "llm",
        "claude-sonnet-4-20250514"
    );

    print("plan: " + str(plan));
    assert "estimated_time_sec" in plan;
    assert "estimated_memory_mb" in plan;
    assert "steps" in plan;
}


test "write_optimized_code llm mode returns non-empty code" {
    source = "def triple(x):\n    return x * 3";
    plan = {
        "estimated_time_sec": 0.05,
        "estimated_memory_mb": 10.0,
        "steps": ["try to optimize triple"],
        "analysis": "simple function, minimal optimization"
    };

    optimized = write_optimized_code(
        source,
        plan,
        "claude-sonnet-4-20250514"
    );

    print("optimized: " + optimized);
    assert optimized is not None;
    assert optimized != "";
}


test "run_optimization with llm profile completes end-to-end" {
    source = "def slow_add(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total";
    input = {
        "source_code": source,
        "function_name": "slow_add",
        "function_call": "slow_add(10)",
        "language": "python",
        "test_cases": [{"call": "slow_add(3)", "expected": 3}],
        "analysis_mode": "llm"
    };

    result = run_optimization(input, None, "anthropic-sonnet");

    print("result: " + str(result));
    assert result["optimized_code"] is not None;
    assert result["optimized_code"] != "";
    assert "slow_add" in result["optimized_code"];
    # assert "error" in result;
}

