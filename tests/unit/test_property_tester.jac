"""Unit tests for property-based testing helpers."""

import from src.core.property_tester { run_property_tests }
import from src.agents.optimizer_agent { write_optimized_code }


test "property tests pass for equivalent annotated function" {
    code = "def add_one(x: int) -> int:\n    return x + 1\n";
    result = run_property_tests(code, "add_one", code, 10, 20);

    assert result["passed"] is True;
    assert result["failed_count"] == 0;
    assert result["total"] >= 1;
}


test "property tests support zero argument functions" {
    code = "def constant() -> int:\n    return 7\n";
    result = run_property_tests(code, "constant", code, 5, 20);

    assert result["passed"] is True;
    assert result["failed_count"] == 0;
}


test "property tests support typing annotations with safe fallback" {
    code = "from typing import Optional\n\ndef normalize(x: Optional[int]) -> int:\n    if x is None:\n        return 0\n    return x\n";
    result = run_property_tests(code, "normalize", code, 10, 20);

    assert result["passed"] is True;
    assert result["failed_count"] == 0;
}


test "property tests catch behavioral mismatch and expose falsifying example" {
    optimized = "def add_one(x: int) -> int:\n    return x + 2\n";
    reference = "def add_one(x: int) -> int:\n    return x + 1\n";
    result = run_property_tests(optimized, "add_one", reference, 10, 20);

    assert result["passed"] is False;
    assert result["failed_count"] >= 1;
    assert "falsifying_example" in result;
}


test "property tests pass on mock rewritten code" {
    original = "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n";
    plan = {
        "backend": "mock",
        "estimated_time_sec": 0.05,
        "estimated_memory_mb": 10.0,
        "steps": ["Reduce loop overhead"],
        "label": "loop-overhead"
    };
    rewritten = write_optimized_code(original, plan, None);
    result = run_property_tests(rewritten, "sum_up", original, 10, 20);

    assert result["passed"] is True;
}
