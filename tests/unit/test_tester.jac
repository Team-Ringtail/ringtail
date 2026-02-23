"""Unit tests for src/core/tester.jac — run_tests function."""

import from src.core.tester { run_tests }


glob GOOD_SOLUTION: str = "def add(a, b):\n    return a + b\n";

glob GOOD_TESTS: str = "from solution import add\n\ndef test_add_positive():\n    assert add(1, 2) == 3\n\ndef test_add_negative():\n    assert add(-1, -2) == -3\n\ndef test_add_zero():\n    assert add(0, 0) == 0\n";

glob BUGGY_SOLUTION: str = "def add(a, b):\n    return a * b\n";

glob PARTIAL_TESTS: str = "from solution import add\n\ndef test_add_works():\n    assert add(2, 3) == 5\n\ndef test_add_zero():\n    assert add(0, 5) == 5\n";


test "all tests pass with correct solution" {
    result = run_tests(GOOD_SOLUTION, GOOD_TESTS);

    assert result["passed"] is True;
    assert result["total"] == 3;
    assert result["passed_count"] == 3;
    assert result["failed_count"] == 0;
    assert result["failures"] == [];
    assert result["error"] == "";
}

test "single test passes" {
    test_code = "from solution import add\ndef test_one(): assert add(1, 1) == 2\n";
    result = run_tests(GOOD_SOLUTION, test_code);

    assert result["passed"] is True;
    assert result["total"] == 1;
    assert result["passed_count"] == 1;
}

test "buggy solution reports failures" {
    result = run_tests(BUGGY_SOLUTION, PARTIAL_TESTS);

    assert result["passed"] is False;
    assert result["failed_count"] > 0;
    assert len(result["failures"]) > 0;
    failure_names = [f["test"] for f in result["failures"]];
    assert any("test_add" in name for name in failure_names);
}

test "failure messages are populated" {
    result = run_tests(BUGGY_SOLUTION, PARTIAL_TESTS);

    for failure in result["failures"] {
        assert "test" in failure;
        assert "message" in failure;
        assert failure["message"] != "";
    }
}

test "syntax error in solution is caught" {
    bad_code = "def broken(:\n    return 1";
    test_code = "from solution import broken\ndef test_it(): broken()\n";
    result = run_tests(bad_code, test_code);

    assert result["passed"] is False;
    assert result["error"] != "";
}

test "timeout on hanging code" {
    hang_code = "import time\ndef slow(): time.sleep(120)";
    test_code = "from solution import slow\ndef test_it(): slow()\n";
    result = run_tests(hang_code, test_code, timeout_seconds=3);

    assert result["passed"] is False;
    assert "imed out" in result["error"];
}

test "import error in solution is caught" {
    bad_code = "import nonexistent_xyz\ndef f(): pass";
    test_code = "from solution import f\ndef test_it(): f()\n";
    result = run_tests(bad_code, test_code);

    assert result["passed"] is False;
    assert result["error"] != "";
}
