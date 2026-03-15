"""Unit tests for discovery helpers and CLI-facing file/function entrypoints."""

import os;
import tempfile;

import from src.core.discovery {
    build_function_input_from_file,
    discover_functions_in_file,
    build_function_input_from_replay_script,
    build_replay_inputs_from_script,
    build_replay_inputs_from_directory
}
import from interfaces.cli.cli {
    inspect_file_function,
    optimize_file_function,
    inspect_replay_function,
    optimize_replay_function,
    inspect_replay_session,
    optimize_best_replay_function,
    inspect_replay_repo,
    optimize_best_replay_in_repo
}


def _write(path: str, content: str) -> None {
    with open(path, "w") as f {
        f.write(content);
    }
}


test "build_function_input_from_file infers function call and test files" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_discovery_");
    try {
        src_dir = os.path.join(tmp_dir, "src");
        tests_dir = os.path.join(tmp_dir, "tests");
        os.mkdir(src_dir);
        os.mkdir(tests_dir);

        module_path = os.path.join(src_dir, "math_ops.py");
        test_path = os.path.join(tests_dir, "test_math_ops.py");

        _write(
            module_path,
            "def add(a: int, b: int = 2):\n    return a + b\n"
        );
        _write(
            test_path,
            "from math_ops import add\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        );

        input = build_function_input_from_file(module_path, "add", None, tests_dir, None);

        assert input["function_name"] == "add";
        assert input["function_call"] == "add(1, 2)";
        discovered = input["extra"]["discovered_test_files"];
        assert len(discovered) == 1;
        assert discovered[0] == os.path.abspath(test_path);
    } finally {
        for (dirpath, dirs, files) in os.walk(tmp_dir, topdown=False) {
            for f in files {
                os.remove(os.path.join(dirpath, f));
            }
            for d in dirs {
                os.rmdir(os.path.join(dirpath, d));
            }
        }
        os.rmdir(tmp_dir);
    }
}


test "discover_functions_in_file lists top level functions" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_functions_");
    try {
        module_path = os.path.join(tmp_dir, "sample.py");
        _write(
            module_path,
            "def first():\n    return 1\n\ndef second(name: str):\n    return name\n"
        );

        functions = discover_functions_in_file(module_path);

        assert len(functions) == 2;
        assert functions[0]["function_name"] == "first";
        assert functions[1]["function_name"] == "second";
    } finally {
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "inspect_file_function exposes normalized input details" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_inspect_");
    try {
        module_path = os.path.join(tmp_dir, "greet.py");
        _write(module_path, "def greet(name: str):\n    return 'hi ' + name\n");

        result = inspect_file_function(module_path, "greet");

        assert result["function_name"] == "greet";
        assert result["function_call"] == "greet('sample')";
        assert "extra" in result;
    } finally {
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "optimize_file_function can optimize directly from file path" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_cli_opt_");
    try {
        module_path = os.path.join(tmp_dir, "sum_up.py");
        _write(
            module_path,
            "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );

        result = optimize_file_function(module_path, "sum_up", "sum_up(10)");

        assert "optimized_code" in result;
        assert "sum_up" in result["optimized_code"];
        assert result["iteration_number"] >= 0;
        assert "baseline_metrics" in result;
    } finally {
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "build_function_input_from_replay_script captures replay cases" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_input_");
    try {
        module_path = os.path.join(tmp_dir, "math_ops.py");
        script_path = os.path.join(tmp_dir, "drive_math_ops.py");
        _write(
            module_path,
            "def add(a: int, b: int):\n    return a + b\n"
        );
        _write(
            script_path,
            "from math_ops import add\n\nadd(1, 2)\nadd(4, 5)\n"
        );

        result = build_function_input_from_replay_script(module_path, "add", script_path, os.path.join(tmp_dir, "tests"), None);

        assert result["function_name"] == "add";
        assert len(result["test_cases"]) == 2;
        assert result["test_cases"][0]["call"] == "add(1, 2)";
        assert result["test_cases"][0]["expected"] == "3";
        assert result["extra"]["replay_trace"]["trace_count"] == 2;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "inspect_replay_function exposes replay-derived input" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_cli_");
    try {
        module_path = os.path.join(tmp_dir, "echoer.py");
        script_path = os.path.join(tmp_dir, "drive_echoer.py");
        _write(
            module_path,
            "def echo(x: int):\n    return x\n"
        );
        _write(
            script_path,
            "from echoer import echo\n\necho(7)\n"
        );

        result = inspect_replay_function(module_path, "echo", script_path);

        assert result["function_call"] == "echo(7)";
        assert len(result["test_cases"]) == 1;
        assert result["test_cases"][0]["expected"] == "7";
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "replay trace records raised exceptions as test cases" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_raise_");
    try {
        module_path = os.path.join(tmp_dir, "raiser.py");
        script_path = os.path.join(tmp_dir, "drive_raiser.py");
        _write(
            module_path,
            "def fail_if_zero(x: int):\n    if x == 0:\n        raise ValueError('zero')\n    return x\n"
        );
        _write(
            script_path,
            "from raiser import fail_if_zero\n\ntry:\n    fail_if_zero(0)\nexcept ValueError:\n    pass\n"
        );

        result = inspect_replay_function(module_path, "fail_if_zero", script_path);

        assert len(result["test_cases"]) == 1;
        assert result["test_cases"][0]["raises"] == "ValueError";
        assert result["extra"]["replay_trace"]["trace_count"] == 1;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "replay trace preserves partial success when script later fails" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_partial_");
    try {
        module_path = os.path.join(tmp_dir, "partial.py");
        script_path = os.path.join(tmp_dir, "drive_partial.py");
        _write(
            module_path,
            "def echo(x: int):\n    return x\n"
        );
        _write(
            script_path,
            "from partial import echo\n\necho(3)\nraise RuntimeError('after call')\n"
        );

        result = inspect_replay_function(module_path, "echo", script_path);

        assert len(result["test_cases"]) == 1;
        assert result["extra"]["replay_trace"]["partial_success"] is True;
        assert "RuntimeError" in result["extra"]["replay_trace"]["run_error"];
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "optimize_replay_function runs optimization from replay-derived tests" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_opt_");
    try {
        module_path = os.path.join(tmp_dir, "sum_up.py");
        script_path = os.path.join(tmp_dir, "drive_sum_up.py");
        _write(
            module_path,
            "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );
        _write(
            script_path,
            "from sum_up import sum_up\n\nsum_up(3)\nsum_up(10)\n"
        );

        result = optimize_replay_function(module_path, "sum_up", script_path);

        assert "optimized_code" in result;
        assert "sum_up" in result["optimized_code"];
        assert result["iteration_number"] >= 0;
        assert "baseline_metrics" in result;
        assert result["test_passed"] is True;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "build_replay_inputs_from_script captures multiple observed functions" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_session_");
    try {
        module_path = os.path.join(tmp_dir, "math_ops.py");
        script_path = os.path.join(tmp_dir, "drive_math_ops.py");
        _write(
            module_path,
            "def add(a: int, b: int):\n    return a + b\n\n"
            + "def mul(a: int, b: int):\n    return a * b\n\n"
            + "def unused(x: int):\n    return x - 1\n"
        );
        _write(
            script_path,
            "from math_ops import add, mul\n\nadd(1, 2)\nmul(3, 4)\nadd(5, 6)\n"
        );

        result = build_replay_inputs_from_script(module_path, script_path, os.path.join(tmp_dir, "tests"), None, None);

        assert result["candidate_count"] == 2;
        assert "add" in result["observed_function_names"];
        assert "mul" in result["observed_function_names"];
        assert result["replay_trace"]["total_trace_count"] == 3;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "inspect_replay_session summarizes replay-backed candidates" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_session_cli_");
    try {
        module_path = os.path.join(tmp_dir, "session_mod.py");
        script_path = os.path.join(tmp_dir, "drive_session_mod.py");
        _write(
            module_path,
            "def alpha(n: int):\n    return n + 1\n\n"
            + "def beta(n: int):\n    return n * 2\n"
        );
        _write(
            script_path,
            "from session_mod import alpha, beta\n\nalpha(2)\nbeta(3)\nbeta(4)\n"
        );

        result = inspect_replay_session(module_path, script_path);

        assert result["candidate_count"] == 2;
        assert len(result["candidates"]) == 2;
        assert "beta" in result["observed_function_names"];
        assert result["replay_trace"]["total_trace_count"] == 3;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "optimize_best_replay_function selects a replay-backed target" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_best_replay_opt_");
    try {
        module_path = os.path.join(tmp_dir, "best_replay.py");
        script_path = os.path.join(tmp_dir, "drive_best_replay.py");
        _write(
            module_path,
            "def fast_add(a: int, b: int):\n    return a + b\n\n"
            + "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );
        _write(
            script_path,
            "from best_replay import fast_add, sum_up\n\nfast_add(1, 2)\nsum_up(3)\nsum_up(10)\n"
        );

        result = optimize_best_replay_function(module_path, script_path);

        assert result["selected_function"] == "sum_up";
        assert result["test_passed"] is True;
        assert result["replay_trace_count"] >= 2;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "build_replay_inputs_from_directory captures observed functions across files" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_inputs_");
    try {
        pkg_dir = os.path.join(tmp_dir, "pkg");
        os.mkdir(pkg_dir);
        module_a = os.path.join(pkg_dir, "math_a.py");
        module_b = os.path.join(pkg_dir, "math_b.py");
        script_path = os.path.join(tmp_dir, "drive_repo.py");
        _write(module_a, "def add(a: int, b: int):\n    return a + b\n");
        _write(module_b, "def mul(a: int, b: int):\n    return a * b\n");
        _write(
            script_path,
            "from pkg.math_a import add\nfrom pkg.math_b import mul\n\nadd(1, 2)\nmul(3, 4)\nmul(5, 6)\n"
        );

        result = build_replay_inputs_from_directory(tmp_dir, script_path, os.path.join(tmp_dir, "tests"), None);

        assert result["candidate_count"] == 2;
        assert len(result["observed_source_files"]) == 2;
        assert "pkg/math_a.py" in str(result["replay_trace"]["captured_records"][0]["source_rel_path"]);
        assert result["replay_trace"]["total_trace_count"] == 3;
    } finally {
        os.remove(script_path);
        os.remove(module_a);
        os.remove(module_b);
        os.rmdir(pkg_dir);
        os.rmdir(tmp_dir);
    }
}


test "inspect_replay_repo summarizes replay-backed repo candidates" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_cli_");
    try {
        pkg_dir = os.path.join(tmp_dir, "pkg");
        os.mkdir(pkg_dir);
        module_a = os.path.join(pkg_dir, "alpha_mod.py");
        module_b = os.path.join(pkg_dir, "beta_mod.py");
        script_path = os.path.join(tmp_dir, "drive_repo_cli.py");
        _write(module_a, "def alpha(x: int):\n    return x + 1\n");
        _write(module_b, "def beta(x: int):\n    return x * 2\n");
        _write(
            script_path,
            "from pkg.alpha_mod import alpha\nfrom pkg.beta_mod import beta\n\nalpha(1)\nbeta(2)\nbeta(3)\n"
        );

        result = inspect_replay_repo(tmp_dir, script_path);

        assert result["candidate_count"] == 2;
        assert len(result["observed_source_files"]) == 2;
        assert len(result["candidates"]) == 2;
        assert result["replay_trace"]["total_trace_count"] == 3;
    } finally {
        os.remove(script_path);
        os.remove(module_a);
        os.remove(module_b);
        os.rmdir(pkg_dir);
        os.rmdir(tmp_dir);
    }
}


test "optimize_best_replay_in_repo selects best replay-backed repo target" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_opt_");
    try {
        pkg_dir = os.path.join(tmp_dir, "pkg");
        os.mkdir(pkg_dir);
        module_a = os.path.join(pkg_dir, "fast_math.py");
        module_b = os.path.join(pkg_dir, "slow_math.py");
        script_path = os.path.join(tmp_dir, "drive_repo_opt.py");
        _write(module_a, "def fast_add(a: int, b: int):\n    return a + b\n");
        _write(
            module_b,
            "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );
        _write(
            script_path,
            "from pkg.fast_math import fast_add\nfrom pkg.slow_math import sum_up\n\nfast_add(1, 2)\nsum_up(3)\nsum_up(10)\n"
        );

        result = optimize_best_replay_in_repo(tmp_dir, script_path);

        assert result["selected_function"] == "sum_up";
        assert "slow_math.py" in result["selected_source_file"];
        assert result["test_passed"] is True;
        assert result["replay_trace_count"] >= 2;
    } finally {
        os.remove(script_path);
        os.remove(module_a);
        os.remove(module_b);
        os.rmdir(pkg_dir);
        os.rmdir(tmp_dir);
    }
}
