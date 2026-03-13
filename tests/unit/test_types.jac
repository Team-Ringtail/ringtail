"""Unit tests for src/models/types.jac — Metrics obj."""

import from src.models.types { Metrics }


test "Metrics basic init" {
    m = Metrics(execution_time=1.0, memory_usage=10.0);

    assert m.execution_time == 1.0;
    assert m.memory_usage == 10.0;
    assert m.cpu_usage is None;
    assert m.code_complexity is None;
    assert m.test_coverage is None;
}

test "Metrics with optional fields" {
    m = Metrics(execution_time=0.5, memory_usage=3.0, cpu_usage=50.0, code_complexity=5, test_coverage=80.0);

    assert m.execution_time == 0.5;
    assert m.memory_usage == 3.0;
    assert m.cpu_usage == 50.0;
    assert m.code_complexity == 5;
    assert m.test_coverage == 80.0;
}
