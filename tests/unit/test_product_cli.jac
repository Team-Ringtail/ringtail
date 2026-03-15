"""Focused tests for packaged CLI request shaping and doctor output."""

import importlib;


test "ringtail cli shapes repo submit request" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    args = argparse.Namespace(
        repo="/tmp/sample_repo",
        prompt="make this faster",
        branch="main",
        backend="blaxel",
        publish_pr=True,
        test_command="python -m pytest tests",
        setup_command=["python -m pip install -r requirements.txt", ""],
        max_targets=4
    );

    payload = cli._build_repo_submit_request(args);

    assert payload["repo_url"] == "/tmp/sample_repo";
    assert payload["prompt"] == "make this faster";
    assert payload["base_branch"] == "main";
    assert payload["publish_pr"] is True;
    assert payload["backend_config"]["backend"] == "blaxel";
    assert payload["test_command"] == "python -m pytest tests";
    assert len(payload["setup_commands"]) == 1;
    assert payload["max_targets"] == 4;
}


test "ringtail cli shapes file optimize request" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    args = argparse.Namespace(
        file_path="/tmp/example.py",
        function_name="sum_up",
        function_call="sum_up(10)",
        tests_root="tests"
    );

    payload = cli._build_file_optimize_request(args);

    assert payload["operation"] == "optimize_file_function";
    assert payload["file_path"] == "/tmp/example.py";
    assert payload["function_name"] == "sum_up";
    assert payload["function_call"] == "sum_up(10)";
    assert payload["tests_root"] == "tests";
}


test "ringtail cli doctor text is ui friendly" {
    cli = importlib.import_module("src.ringtail_cli");
    doctor = {
        "ok": False,
        "checks": {
            "jac": {"available": True, "path": "/usr/local/bin/jac"},
            "git": {"available": True, "path": "/usr/bin/git"},
            "openssl": {"available": False, "path": ""}
        },
        "env": {
            "repo_agent_config_present": True,
            "anthropic_configured": False,
            "blaxel_configured": True
        },
        "auth": {
            "auth_mode": "github_app",
            "installation_id": 12345
        },
        "jobs_dir": "/tmp/ringtail_jobs",
        "issues": ["openssl not found"]
    };

    rendered = cli._render_doctor_text(doctor);

    assert "overall_ok: False" in rendered;
    assert "jac: /usr/local/bin/jac" in rendered;
    assert "auth_mode: github_app" in rendered;
    assert "installation_id: 12345" in rendered;
    assert "issues:" in rendered;
    assert "openssl not found" in rendered;
}


test "ringtail cli uses jac function route shape" {
    cli = importlib.import_module("src.ringtail_cli");

    assert cli._function_route("submit_repo_agent_job") == "/function/submit_repo_agent_job";
    assert cli._function_route("/get_repo_agent_job") == "/function/get_repo_agent_job";
    assert cli._function_route("optimize_sync") == "/function/optimize_sync";
}


test "ringtail cli unwraps jac function response envelope" {
    cli = importlib.import_module("src.ringtail_cli");
    wrapped = {
        "ok": True,
        "data": {
            "reports": [],
            "result": {"job_id": "job-1", "status": "queued"}
        }
    };

    unwrapped = cli._unwrap_function_response(wrapped);

    assert unwrapped["job_id"] == "job-1";
    assert unwrapped["status"] == "queued";
}


test "ringtail cli wraps dict request bodies for jac functions" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    repo_args = argparse.Namespace(
        repo="/tmp/sample_repo",
        prompt="make this faster",
        branch="main",
        backend="local",
        publish_pr=False,
        test_command="",
        setup_command=[],
        max_targets=3
    );
    file_args = argparse.Namespace(
        file_path="/tmp/example.py",
        function_name="sum_up",
        function_call="",
        tests_root="tests"
    );

    repo_payload = {"request": cli._build_repo_submit_request(repo_args)};
    file_payload = {"request": cli._build_file_optimize_request(file_args)};

    assert repo_payload["request"]["repo_url"] == "/tmp/sample_repo";
    assert file_payload["request"]["operation"] == "optimize_file_function";
}
