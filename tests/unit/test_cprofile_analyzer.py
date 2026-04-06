from __future__ import annotations

import os
import sys
import tempfile

from src.core import cprofile_analyzer as analyzer
from src.core.cprofile_analyzer import FunctionProfile, ProfileAnalysis


def test_is_user_code_accepts_private_tmp_realpath_alias() -> None:
    with tempfile.TemporaryDirectory(prefix="ringtail_cprofile_repo_", dir="/tmp") as repo_dir:
        source_path = os.path.join(repo_dir, "runner.py")
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write("print('hello')\n")

        repo_alias = repo_dir
        profiler_path = os.path.realpath(source_path)

        assert profiler_path.startswith("/private/tmp/")
        assert repo_alias.startswith("/tmp/")
        assert analyzer._is_user_code(profiler_path, repo_alias) is True


def test_is_user_code_accepts_relative_profile_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="ringtail_cprofile_repo_", dir="/tmp") as repo_dir:
        os.makedirs(os.path.join(repo_dir, "algorithms"), exist_ok=True)
        with open(os.path.join(repo_dir, "algorithms", "algo.py"), "w", encoding="utf-8") as handle:
            handle.write("def run():\n    return 1\n")

        assert analyzer._is_user_code("algorithms/algo.py", repo_dir) is True


def test_build_call_dag_returns_merged_cycle_nodes() -> None:
    repo_dir = "/tmp/ringtail_cycle_repo"
    foo_key = os.path.join(repo_dir, "mod.py") + ":1:foo"
    bar_key = os.path.join(repo_dir, "mod.py") + ":5:bar"
    foo_profile = FunctionProfile(
        module="mod",
        name="foo",
        file_path=os.path.join(repo_dir, "mod.py"),
        lineno=1,
        tottime=1.0,
        cumtime=1.0,
        ncalls=1,
        callers=[bar_key],
        callees=[bar_key],
    )
    bar_profile = FunctionProfile(
        module="mod",
        name="bar",
        file_path=os.path.join(repo_dir, "mod.py"),
        lineno=5,
        tottime=0.5,
        cumtime=0.5,
        ncalls=1,
        callers=[foo_key],
        callees=[foo_key],
    )
    analysis = ProfileAnalysis(
        functions={foo_key: foo_profile, bar_key: bar_profile},
        call_graph={foo_key: [bar_key], bar_key: [foo_key]},
        total_time=1.5,
        entry_point="python mod.py",
        repo_path=repo_dir,
    )

    dag = analyzer.build_call_dag(analysis, {foo_key, bar_key})

    assert dag.levels == [[min(foo_key, bar_key)]]
    assert set(dag.nodes.keys()) == {min(foo_key, bar_key)}
    assert dag.edges == {}


def test_resolve_python_falls_back_to_current_interpreter(tmp_path) -> None:
    assert analyzer._resolve_python(str(tmp_path)) == sys.executable
