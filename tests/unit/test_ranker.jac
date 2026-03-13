"""Unit tests for lightweight function ranking."""

import os;
import tempfile;

import from src.core.ranker { rank_functions_in_file }
import from interfaces.cli.cli { discover_and_rank_file }


def _write(path: str, content: str) -> None {
    with open(path, "w") as f {
        f.write(content);
    }
}


test "rank_functions_in_file puts slower function first" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_ranker_");
    try {
        module_path = os.path.join(tmp_dir, "sample_rank.py");
        _write(
            module_path,
            "def fast_add(a: int = 1, b: int = 2):\n    return a + b\n\n"
            + "def slow_sum(n: int = 80):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            total += i + j\n    return total\n"
        );

        ranked = rank_functions_in_file(module_path, os.path.join(tmp_dir, "tests"), 5);

        assert len(ranked) >= 2;
        assert ranked[0]["function_name"] == "slow_sum";
        assert ranked[1]["function_name"] == "fast_add";
    } finally {
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "discover_and_rank_file exposes CLI-facing ranking" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_rank_cli_");
    try {
        tests_dir = os.path.join(tmp_dir, "tests");
        os.mkdir(tests_dir);
        module_path = os.path.join(tmp_dir, "sample_cli_rank.py");
        test_path = os.path.join(tests_dir, "test_sample_cli_rank.py");
        _write(
            module_path,
            "def a(n: int = 50):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );
        _write(
            test_path,
            "from sample_cli_rank import a\n\ndef test_a():\n    assert a(3) == 3\n"
        );

        ranked = discover_and_rank_file(module_path, tests_dir, 3);

        assert len(ranked) == 1;
        assert ranked[0]["function_name"] == "a";
        assert "median_ms" in ranked[0];
        assert "discovered_test_count" in ranked[0];
        assert ranked[0]["discovered_test_count"] == 1;
    } finally {
        os.remove(test_path);
        os.rmdir(tests_dir);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}
