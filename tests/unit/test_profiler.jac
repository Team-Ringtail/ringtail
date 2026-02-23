"""Unit tests for src/core/profiler.jac — profile_code function."""

import from src.core.profiler { profile_code }


test "simple function returns success" {
    code = "def add(a, b): return a + b";
    result = profile_code(code, "add(1, 2)");

    assert result["success"] is True;
    assert result["error"] == "";
    assert result["median_ms"] > 0;
    assert result["min_ms"] > 0;
    assert result["max_ms"] >= result["min_ms"];
    assert result["median_ms"] >= result["min_ms"];
    assert result["median_ms"] <= result["max_ms"];
    assert result["peak_memory_kb"] >= 0;
    assert result["iterations"] >= 1;
}

test "iterations count is respected" {
    code = "def noop(): pass";
    result = profile_code(code, "noop()", num_iterations=3);

    assert result["success"] is True;
    assert result["iterations"] == 3;
}

test "memory scales with allocation size" {
    small_code = "def alloc(): return [0] * 100";
    big_code = "def alloc(): return [0] * 1_000_000";

    small = profile_code(small_code, "alloc()", num_iterations=1);
    big = profile_code(big_code, "alloc()", num_iterations=1);

    assert small["success"] is True;
    assert big["success"] is True;
    assert big["peak_memory_kb"] > small["peak_memory_kb"];
}

test "syntax error returns failure" {
    code = "def broken(:\n    return 1";
    result = profile_code(code, "broken()");

    assert result["success"] is False;
    assert result["error"] != "";
}

test "runtime error returns failure" {
    code = "def boom(): raise ValueError('kaboom')";
    result = profile_code(code, "boom()");

    assert result["success"] is False;
    assert "kaboom" in result["error"] or "ValueError" in result["error"];
}

test "timeout returns failure" {
    code = "import time\ndef slow(): time.sleep(60)";
    result = profile_code(code, "slow()", timeout_seconds=2, num_iterations=1);

    assert result["success"] is False;
    assert "imed out" in result["error"];
}

test "import error returns failure" {
    code = "import nonexistent_module_xyz\ndef f(): pass";
    result = profile_code(code, "f()");

    assert result["success"] is False;
    assert result["error"] != "";
}
