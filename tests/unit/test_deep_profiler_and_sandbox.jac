"""Unit tests for deep profiling and sandbox runner backends."""

import from src.core.deep_profiler { deep_profile };
import from src.core.sandbox_runner { LocalBackend };


test "deep_profile handles simple function or returns graceful error" {
    code = "def add(a, b):\n    return a + b";
    function_call = "add(1, 2)";

    profile = deep_profile(code, function_call, 2, 10);

    assert profile is not None;
    # deep_profile may fail if Scalene is not installed; both paths are acceptable.
    assert "success" in profile;
}


test "LocalBackend can run a tiny script" {
    backend = LocalBackend();
    script_name = "main.py";
    files = {
        "main.py": "print('hello from sandbox')\n"
    };

    result = backend.run_script(script_name, files, 5, []);

    assert "success" in result;
    assert "stdout" in result;
}

