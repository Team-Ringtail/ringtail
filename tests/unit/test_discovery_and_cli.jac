"""Unit tests for discovery helpers and CLI-facing file/function entrypoints."""

import os;
import tempfile;

import from src.core.discovery {
    build_function_input_from_file,
    discover_functions_in_file
}
import from interfaces.cli.cli { inspect_file_function, optimize_file_function }


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
