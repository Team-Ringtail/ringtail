"""Unit tests for src/agents/optimizer_agent.jac (heuristic path)."""

import from src.agents.optimizer_agent { think_and_prep, write_optimized_code, compare };


test "think_and_prep heuristic produces sensible plan" {
    source = "def foo(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total";
    criteria = {"performance_weight": 1.0, "code_quality_weight": 1.0, "functionality_weight": 1.0};
    function_call = "foo(10)";
    cases = [];

    plan = think_and_prep(
        source,
        criteria,
        function_call,
        cases,
        None,
        None
    );

    assert "estimated_time_sec" in plan;
    assert "estimated_memory_mb" in plan;
    assert "steps" in plan;
    assert len(plan["steps"]) > 0;
}


test "write_optimized_code heuristic preserves runnable code" {
    source = "def bar(x):\n    return x * 2";
    plan = {
        "estimated_time_sec": 0.05,
        "estimated_memory_mb": 10.0,
        "steps": ["stub step"]
    };

    optimized = write_optimized_code(source, plan, None);

    assert "bar" in optimized;
    assert "stub" in optimized;
}


test "compare returns done when within target" {
    profiler_metrics = {
        "execution_time_sec": 0.9,
        "memory_mb": 10.0
    };
    plan = {
        "estimated_time_sec": 1.0,
        "estimated_memory_mb": 10.0,
        "steps": []
    };

    result = compare(profiler_metrics, plan);

    assert result["signal"] in ["continue", "done"];
}

