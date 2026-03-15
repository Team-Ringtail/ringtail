"""Focused tests for the CLI-first repo agent workflow."""

import os;
import subprocess;
import tempfile;
import time;
import importlib;

import from main {
    run_repo_agent_sync,
    submit_repo_agent_job,
    get_repo_agent_job,
    get_auth_readiness,
    get_config_doctor,
    get_recent_jobs,
    get_github_app_install_info,
    handle_github_app_install_callback,
    verify_github_repo_access
}


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
        assert result["bootstrap"]["test_command"] == "python -m pytest tests";
        assert len(result["candidate_summaries"]) >= 1;
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


test "product status endpoints expose auth doctor and recent jobs" {
    auth = get_auth_readiness();
    doctor = get_config_doctor();
    jobs = get_recent_jobs(5);

    assert "auth_mode" in auth;
    assert "github_app" in auth;
    assert "checks" in doctor;
    assert "issues" in doctor;
    assert isinstance(jobs, list);
}


test "repo agent can fan out via child jobs" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_child_jobs_");
    try {
        repo_dir = _create_local_repo(tmp_dir);
        result = run_repo_agent_sync({
            "repo_url": repo_dir,
            "prompt": "make slow_sum faster",
            "tests_root": "tests",
            "test_command": "python -m pytest tests",
            "config_name": "test-fast",
            "backend_config": {"backend": "local", "fanout_mode": "child_jobs"},
            "publish_pr": False
        });

        assert result["success"] is True;
        assert len(result["child_jobs"]) >= 1;
        assert result["child_jobs"][0]["job_id"] != "";
        assert result["candidate_results"][0]["job_id"] != "";
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
    old_config = os.environ.get("RINGTAIL_REPO_AGENT_CONFIG", None);
    try {
        os.environ["RINGTAIL_REPO_AGENT_CONFIG"] = '{"token":"token-123","app_slug":"ringtail-test-app"}';
        body = mod.build_pr_body(
            prompt="make this faster",
            target_summary="slow_math.py::slow_sum",
            test_summary="python -m pytest tests (success=True)",
            performance_summary="improvement_ratio=1.2",
            notes=["Auth mode: token"]
        );
        install_info = get_github_app_install_info("job-123");
        assert mod.resolve_github_token(None) == "token-123";
        assert "slow_math.py::slow_sum" in body;
        assert "make this faster" in body;
        assert "Auth mode: token" in body;
        assert "ringtail-test-app" in install_info["install_url"];
    } finally {
        if old_config is None {
            os.environ.pop("RINGTAIL_REPO_AGENT_CONFIG", None);
        } else {
            os.environ["RINGTAIL_REPO_AGENT_CONFIG"] = old_config;
        }
    }
}


test "repo agent auto-detects bootstrap and test command" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_auto_");
    try {
        repo_dir = _create_local_repo(tmp_dir);
        _write(os.path.join(repo_dir, "requirements.txt"), "");
        subprocess.run(["git", "add", "."], cwd=repo_dir, env=_git_env(), check=True, capture_output=True);
        subprocess.run(["git", "commit", "-m", "add requirements"], cwd=repo_dir, env=_git_env(), check=True, capture_output=True);

        result = run_repo_agent_sync({
            "repo_url": repo_dir,
            "prompt": "make slow_sum faster",
            "config_name": "test-fast",
            "backend_config": {"backend": "local"},
            "publish_pr": False
        });

        assert result["success"] is True;
        assert "python -m pip install -r requirements.txt" in result["bootstrap"]["setup_commands"];
        assert result["bootstrap"]["test_command"] == "python -m pytest tests";
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


test "clone_repo snapshots local repo without git clone" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_clone_local_");
    try {
        repo_dir = _create_local_repo(tmp_dir);
        service = importlib.import_module("src.core.github_repo_service");
        clone_path = os.path.join(tmp_dir, "copied_repo");

        cloned = service.clone_repo(repo_dir, clone_path, "main", None);

        assert cloned == clone_path;
        assert os.path.exists(os.path.join(clone_path, "slow_math.py"));
        assert os.path.exists(os.path.join(clone_path, ".git"));
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


test "github app callback and repo access helpers can be mocked" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_repo_agent_access_");
    service = importlib.import_module("src.core.github_repo_service");
    original_list = service.list_installation_repositories;
    original_create = service.create_installation_access_token;
    try {
        repo_dir = _create_local_repo(tmp_dir);
        service.list_installation_repositories = lambda installation_id, auth=None: {
            "total_count": 1,
            "repositories": [{"full_name": "owner/repo", "private": True, "default_branch": "main", "permissions": {"pull_requests": "write"}}],
            "expires_at": "2026-03-15T16:00:00Z",
            "installation_id": installation_id
        };
        service.create_installation_access_token = lambda installation_id, auth=None: {
            "token": "install-token-123",
            "expires_at": "2026-03-15T16:00:00Z",
            "permissions": {"contents": "write"}
        };
        callback = handle_github_app_install_callback(12345, "install", "state-1");
        access = verify_github_repo_access({"repo_url": repo_dir});
        auth_context = service.resolve_github_auth({"installation_id": 12345});

        assert callback["success"] is True;
        assert callback["installation_id"] == 12345;
        assert callback["repository_count"] == 1;
        assert access["auth_mode"] == "local";
        assert auth_context["mode"] == "github_app_installation";
        assert auth_context["token"] == "install-token-123";
    } finally {
        service.list_installation_repositories = original_list;
        service.create_installation_access_token = original_create;
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


test "repo agent config env can provide installation auth defaults" {
    old_config = os.environ.get("RINGTAIL_REPO_AGENT_CONFIG", None);
    service = importlib.import_module("src.core.github_repo_service");
    original_create = service.create_installation_access_token;
    try {
        os.environ["RINGTAIL_REPO_AGENT_CONFIG"] = '{"app_id":"123","app_slug":"ringtail-test-app","private_key":"-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----","installation_id":999}';
        service.create_installation_access_token = lambda installation_id, auth=None: {
            "token": "env-install-token",
            "expires_at": "2026-03-15T16:00:00Z",
            "permissions": {"contents": "write"}
        };
        auth_context = service.resolve_github_auth(None);
        install_info = get_github_app_install_info("state-2");

        assert auth_context["mode"] == "github_app_installation";
        assert auth_context["installation_id"] == 999;
        assert auth_context["token"] == "env-install-token";
        assert install_info["app_slug"] == "ringtail-test-app";
    } finally {
        service.create_installation_access_token = original_create;
        if old_config is None {
            os.environ.pop("RINGTAIL_REPO_AGENT_CONFIG", None);
        } else {
            os.environ["RINGTAIL_REPO_AGENT_CONFIG"] = old_config;
        }
    }
}
