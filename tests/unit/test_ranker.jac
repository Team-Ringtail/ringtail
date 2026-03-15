"""Unit tests for lightweight function ranking."""

import os;
import tempfile;

import from src.core.ranker {
    rank_functions_in_file,
    rank_replay_candidates_in_file,
    rank_replay_candidates_in_directory
}
import from interfaces.cli.cli {
    discover_and_rank_file,
    discover_and_rank_replay_file,
    discover_and_rank_replay_repo
}


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


test "rank_replay_candidates_in_file prioritizes replay-backed hot function" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_ranker_");
    try {
        module_path = os.path.join(tmp_dir, "replay_rank.py");
        script_path = os.path.join(tmp_dir, "drive_replay_rank.py");
        _write(
            module_path,
            "def fast_add(a: int, b: int):\n    return a + b\n\n"
            + "def slow_sum(n: int = 80):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            total += i + j\n    return total\n"
        );
        _write(
            script_path,
            "from replay_rank import fast_add, slow_sum\n\nfast_add(1, 2)\nslow_sum(6)\nslow_sum(8)\n"
        );

        ranked = rank_replay_candidates_in_file(module_path, script_path, os.path.join(tmp_dir, "tests"), 5);

        assert len(ranked) == 2;
        assert ranked[0]["function_name"] == "slow_sum";
        assert ranked[0]["replay_trace_count"] == 2;
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "discover_and_rank_replay_file exposes replay-aware CLI ranking" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_rank_cli_");
    try {
        module_path = os.path.join(tmp_dir, "replay_cli_rank.py");
        script_path = os.path.join(tmp_dir, "drive_replay_cli_rank.py");
        _write(
            module_path,
            "def alpha(x: int):\n    return x + 1\n\n"
            + "def beta(x: int):\n    return x * 2\n"
        );
        _write(
            script_path,
            "from replay_cli_rank import alpha, beta\n\nalpha(1)\nbeta(2)\nbeta(3)\n"
        );

        ranked = discover_and_rank_replay_file(module_path, script_path, os.path.join(tmp_dir, "tests"), 5);

        assert len(ranked) == 2;
        assert ranked[0]["function_name"] == "beta";
        assert ranked[0]["replay_trace_count"] == 2;
        assert ranked[1]["function_name"] == "alpha";
    } finally {
        os.remove(script_path);
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "rank_replay_candidates_in_directory prioritizes hottest repo candidate" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_ranker_");
    try {
        pkg_dir = os.path.join(tmp_dir, "pkg");
        os.mkdir(pkg_dir);
        module_a = os.path.join(pkg_dir, "fast_math.py");
        module_b = os.path.join(pkg_dir, "slow_math.py");
        script_path = os.path.join(tmp_dir, "drive_repo_rank.py");
        _write(module_a, "def fast_add(a: int, b: int):\n    return a + b\n");
        _write(
            module_b,
            "def slow_sum(n: int = 40):\n    total = 0\n    for i in range(n):\n        for j in range(n):\n            total += i + j\n    return total\n"
        );
        _write(
            script_path,
            "from pkg.fast_math import fast_add\nfrom pkg.slow_math import slow_sum\n\nfast_add(1, 2)\nslow_sum(5)\nslow_sum(7)\n"
        );

        ranked = rank_replay_candidates_in_directory(tmp_dir, script_path, os.path.join(tmp_dir, "tests"), 5);

        assert len(ranked) == 2;
        assert ranked[0]["function_name"] == "slow_sum";
        assert ranked[0]["replay_trace_count"] == 2;
        assert "slow_math.py" in ranked[0]["source_file"];
    } finally {
        os.remove(script_path);
        os.remove(module_a);
        os.remove(module_b);
        os.rmdir(pkg_dir);
        os.rmdir(tmp_dir);
    }
}


test "discover_and_rank_replay_repo exposes repo replay ranking" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_replay_repo_rank_cli_");
    try {
        pkg_dir = os.path.join(tmp_dir, "pkg");
        os.mkdir(pkg_dir);
        module_a = os.path.join(pkg_dir, "alpha_mod.py");
        module_b = os.path.join(pkg_dir, "beta_mod.py");
        script_path = os.path.join(tmp_dir, "drive_repo_cli_rank.py");
        _write(module_a, "def alpha(x: int):\n    return x + 1\n");
        _write(module_b, "def beta(x: int):\n    return x * 2\n");
        _write(
            script_path,
            "from pkg.alpha_mod import alpha\nfrom pkg.beta_mod import beta\n\nalpha(1)\nbeta(2)\nbeta(3)\n"
        );

        ranked = discover_and_rank_replay_repo(tmp_dir, script_path, os.path.join(tmp_dir, "tests"), 5);

        assert len(ranked) == 2;
        assert ranked[0]["function_name"] == "beta";
        assert ranked[0]["replay_trace_count"] == 2;
        assert "beta_mod.py" in ranked[0]["source_file"];
    } finally {
        os.remove(script_path);
        os.remove(module_a);
        os.remove(module_b);
        os.rmdir(pkg_dir);
        os.rmdir(tmp_dir);
    }
}
