"""Focused tests for the CLI-first repo agent workflow."""

import os;
import subprocess;
import tempfile;
import time;
import importlib;

import from main { run_repo_agent_sync, submit_repo_agent_job, get_repo_agent_job }


def _write(path: str, content: str) -> None {
    parent = os.path.dirname(path);
    if parent != "" and not os.path.exists(parent) {
        os.makedirs(parent, exist_ok=True);
    }
    with open(path, "w") as f {
        f.write(content);
    }
}


def _git_env -> dict {
    env = dict(os.environ);
    env["GIT_AUTHOR_NAME"] = "Ringtail Test";
    env["GIT_AUTHOR_EMAIL"] = "ringtail-test@example.com";
    env["GIT_COMMITTER_NAME"] = "Ringtail Test";
    env["GIT_COMMITTER_EMAIL"] = "ringtail-test@example.com";
    return env;
}


def _create_local_repo(root_dir: str) -> str {
    repo_dir = os.path.join(root_dir, "sample_repo");
    os.makedirs(repo_dir, exist_ok=True);
    _write(
        os.path.join(repo_dir, "slow_math.py"),
        "def slow_sum(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
    );
    _write(
        os.path.join(repo_dir, "tests", "test_slow_math.py"),
        "from slow_math import slow_sum\n\n\ndef test_slow_sum():\n    assert slow_sum(4) == 6\n"
    );

    env = _git_env();
    subprocess.run(["git", "init"], cwd=repo_dir, env=env, check=True, capture_output=True);
    subprocess.run(["git", "checkout", "-B", "main"], cwd=repo_dir, env=env, check=True, capture_output=True);
    subprocess.run(["git", "add", "."], cwd=repo_dir, env=env, check=True, capture_output=True);
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, env=env, check=True, capture_output=True);
    return repo_dir;
}


def _wait_for_job(job_id: str, timeout_s: float = 60.0) -> dict {
    started = time.time();
    status = get_repo_agent_job(job_id);
    while status.get("status", "") != "succeeded" and status.get("status", "") != "failed" {
        if time.time() - started > timeout_s {
            return status;
        }
        time.sleep(0.5);
        status = get_repo_agent_job(job_id);
    }
    return status;
}


test "repo agent sync local repo returns pr preview" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_sync_");
    try {
        repo_dir = _create_local_repo(tmp_dir);
        result = run_repo_agent_sync({
            "repo_url": repo_dir,
            "prompt": "make slow_sum faster",
            "tests_root": "tests",
            "test_command": "python -m pytest tests",
            "config_name": "test-fast",
            "backend_config": {"backend": "local"},
            "publish_pr": False
        });

        assert result["success"] is True;
        assert result["selected_target"]["function_name"] == "slow_sum";
        assert result["pull_request"]["preview_only"] is True;
        assert result["validation_result"]["success"] is True;
        assert len(result["candidate_results"]) >= 1;
    } finally {
        for (dirpath, dirs, files) in os.walk(tmp_dir, topdown=False) {
            for fname in files {
                os.remove(os.path.join(dirpath, fname));
            }
            for dname in dirs {
                os.rmdir(os.path.join(dirpath, dname));
            }
        }
        os.rmdir(tmp_dir);
    }
}


test "repo agent async submit and status works for local repo" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_async_");
    try {
        repo_dir = _create_local_repo(tmp_dir);
        submitted = submit_repo_agent_job({
            "repo_url": repo_dir,
            "prompt": "make slow_sum faster",
            "tests_root": "tests",
            "test_command": "python -m pytest tests",
            "config_name": "test-fast",
            "backend_config": {"backend": "local"},
            "publish_pr": False
        });

        assert submitted["status"] in ["queued", "running"];
        finished = _wait_for_job(submitted["job_id"]);
        assert finished["status"] == "succeeded";
        assert finished["result"]["success"] is True;
        assert finished["result"]["pull_request"]["preview_only"] is True;
    } finally {
        for (dirpath, dirs, files) in os.walk(tmp_dir, topdown=False) {
            for fname in files {
                os.remove(os.path.join(dirpath, fname));
            }
            for dname in dirs {
                os.rmdir(os.path.join(dirpath, dname));
            }
        }
        os.rmdir(tmp_dir);
    }
}


test "repo agent github helpers resolve auth and build pr body" {
    mod = importlib.import_module("src.core.github_repo_service");
    old_token = os.environ.get("RINGTAIL_GITHUB_TOKEN", None);
    try {
        os.environ["RINGTAIL_GITHUB_TOKEN"] = "token-123";
        body = mod.build_pr_body(
            prompt="make this faster",
            target_summary="slow_math.py::slow_sum",
            test_summary="python -m pytest tests (success=True)",
            performance_summary="improvement_ratio=1.2"
        );
        assert mod.resolve_github_token(None) == "token-123";
        assert "slow_math.py::slow_sum" in body;
        assert "make this faster" in body;
    } finally {
        if old_token is None {
            os.environ.pop("RINGTAIL_GITHUB_TOKEN", None);
        } else {
            os.environ["RINGTAIL_GITHUB_TOKEN"] = old_token;
        }
    }
}
