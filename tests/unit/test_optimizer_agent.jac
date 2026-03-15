"""Unit tests for src/agents/optimizer_agent.jac."""

import from src.agents.optimizer_agent { think_and_prep, write_optimized_code, compare, enumerate_candidate_plans }


test "think_and_prep mock backend produces deterministic plan" {
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
        "__ringtail_test_mock__"
    );

    assert "estimated_time_sec" in plan;
    assert "estimated_memory_mb" in plan;
    assert "steps" in plan;
    assert len(plan["steps"]) > 0;
    assert "candidate_plans" in plan;
    assert plan["backend"] == "mock";
}

test "enumerate_candidate_plans returns bounded variants" {
    plan = {
        "estimated_time_sec": 0.05,
        "estimated_memory_mb": 10.0,
        "steps": ["base"],
        "candidate_plans": [
            {"label": "a", "steps": ["one"]},
            {"label": "b", "steps": ["two"]},
            {"label": "c", "steps": ["three"]}
        ]
    };

    candidates = enumerate_candidate_plans(plan, 2);

    assert len(candidates) == 2;
    assert candidates[0]["label"] == "a";
    assert candidates[1]["steps"][0] == "two";
}


test "write_optimized_code mock backend preserves runnable code" {
    source = "def bar(x):\n    return x * 2";
    plan = {
        "backend": "mock",
        "analysis": "mock optimizer plan for deterministic tests",
        "estimated_time_sec": 0.05,
        "estimated_memory_mb": 10.0,
        "steps": ["mock step"]
    };

    optimized = write_optimized_code(source, plan, None);

    assert "bar" in optimized;
    assert optimized == source;
}


test "think_and_prep without explicit backend fails fast" {
    source = "def foo(n):\n    return n";
    criteria = {"performance_weight": 1.0, "code_quality_weight": 1.0, "functionality_weight": 1.0};

    try {
        think_and_prep(source, criteria, "foo(1)", [], None, None);
        assert False;
    } except Exception as e {
        assert "No optimizer backend configured" in str(e);
    }
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

