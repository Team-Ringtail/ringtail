"""Focused tests for packaged CLI request shaping and doctor output."""

import os;
import importlib;


test "ringtail cli shapes repo submit request" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    args = argparse.Namespace(
        repo="/tmp/sample_repo",
        prompt="make this faster",
        branch="main",
        backend="blaxel",
        config_name="candidate-search",
        publish_pr=True,
        test_command="python -m pytest tests",
        setup_command=["python -m pip install -r requirements.txt", ""],
        max_targets=4
    );

    payload = cli._build_repo_submit_request(args);

    assert payload["repo_url"].endswith("/tmp/sample_repo");
    assert payload["prompt"] == "make this faster";
    assert payload["base_branch"] == "main";
    assert payload["publish_pr"] is True;
    assert payload["backend_config"]["backend"] == "blaxel";
    assert payload["config_name"] == "candidate-search";
    assert payload["test_command"] == "python -m pytest tests";
    assert len(payload["setup_commands"]) == 1;
    assert payload["max_targets"] == 4;
}


test "ringtail cli shapes file optimize request" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    with open("/tmp/example.py", "w") as f {
        f.write("def sum_up(n: int):\n    return n\n");
    }
    args = argparse.Namespace(
        file_path="/tmp/example.py",
        function_name="sum_up",
        function_call="sum_up(10)",
        tests_root="tests",
        config_name="live-fast"
    );

    payload = cli._build_file_optimize_request(args);

    assert payload["operation"] == "optimize_file_function";
    assert payload["file_path"].endswith("/tmp/example.py");
    assert payload["function_name"] == "sum_up";
    assert payload["function_call"] == "sum_up(10)";
    assert payload["config_name"] == "live-fast";
    assert payload["tests_root"].endswith("/ringtail/tests");
    os.remove("/tmp/example.py");
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
        config_name="",
        publish_pr=False,
        test_command="",
        setup_command=[],
        max_targets=3
    );
    file_args = argparse.Namespace(
        file_path="/tmp/example.py",
        function_name="sum_up",
        function_call="",
        tests_root="tests",
        config_name="live-fast"
    );
    with open("/tmp/example.py", "w") as f {
        f.write("def sum_up(n: int):\n    return n\n");
    }

    repo_payload = {"request": cli._build_repo_submit_request(repo_args)};
    file_payload = {"request": cli._build_file_optimize_request(file_args)};

    assert repo_payload["request"]["repo_url"].endswith("/tmp/sample_repo");
    assert file_payload["request"]["operation"] == "optimize_file_function";
    assert file_payload["request"]["config_name"] == "live-fast";
    os.remove("/tmp/example.py");
}


test "ringtail cli fails early when file optimize path is missing" {
    argparse = importlib.import_module("argparse");
    cli = importlib.import_module("src.ringtail_cli");
    args = argparse.Namespace(
        file_path="/tmp/definitely_missing_ringtail_file.py",
        function_name="sum_up",
        function_call="sum_up(10)",
        tests_root="tests",
        config_name="live-fast"
    );

    try {
        cli._build_file_optimize_request(args);
        assert False;
    } except RuntimeError as e {
        assert "file_path does not exist" in str(e);
    }
}


test "ringtail cli formats successful repo summary with artifact paths" {
    cli = importlib.import_module("src.ringtail_cli");
    payload = {
        "status": "succeeded",
        "job_id": "job-1",
        "result": {
            "repo_url": "../demo",
            "candidate_count": 4,
            "evaluated_candidate_count": 3,
            "selected_target": {"source_file": "slow_math.py", "function_name": "slow_sum"},
            "validation_result": {"success": True},
            "summary_stats": {
                "improvement_ratio": 1.5,
                "baseline_time_ms": 10.0,
                "optimized_time_ms": 6.5,
                "time_saved_pct": 35.0
            },
            "artifacts": {
                "timing_graph_path": "/tmp/timing.svg",
                "summary_json_path": "/tmp/summary.json",
                "run_log_paths": ["/tmp/run.jsonl"]
            },
            "pull_request": {"preview_only": True}
        }
    };

    rendered = cli._format_repo_job_payload(payload);

    assert "status: succeeded" in rendered;
    assert "selected_target: slow_math.py::slow_sum" in rendered;
    assert "timing_graph: /tmp/timing.svg" in rendered;
    assert "summary_json: /tmp/summary.json" in rendered;
    assert "pull_request: preview_only" in rendered;
}


test "ringtail cli hints when server config is stale" {
    cli = importlib.import_module("src.ringtail_cli");
    payload = {
        "test_passed": False,
        "termination_reason": "Optimization failed",
        "improvement_ratio": 0.0,
        "summary_stats": {
            "baseline_time_ms": 1.0,
            "optimized_time_ms": 1.0,
            "time_saved_pct": 0.0
        },
        "artifacts": {},
        "run_log_path": "/tmp/run.jsonl",
        "error": "No optimizer backend configured. Use an LLM-backed profile or the explicit test mock backend."
    };

    rendered = cli._format_file_optimize_payload(payload);

    assert "restart `ringtail serve`" in rendered;
}


test "ringtail cli formats file optimize failure details" {
    cli = importlib.import_module("src.ringtail_cli");
    payload = {
        "test_passed": False,
        "termination_reason": "Property-based test failure",
        "improvement_ratio": 0.0,
        "candidate_label": "candidate_0",
        "optimized_code": "def slow_sum(n: int):\n    return n * (n - 1) // 2\n",
        "summary_stats": {
            "baseline_time_ms": 1.0,
            "optimized_time_ms": 1.0,
            "time_saved_pct": 0.0
        },
        "artifacts": {},
        "run_log_path": "/tmp/run.jsonl",
        "error": "Property-based test failure",
        "failure_feedback": {
            "type": "property_test_failure",
            "candidate_label": "candidate_0",
            "falsifying_example": "test_matches_reference(\nE       n=-1,\nE   )",
            "failures": [
                {
                    "message": "FAILED test_property.py::test_matches_reference",
                    "falsifying_example": "test_matches_reference(\nE       n=-1,\nE   )"
                }
            ]
        }
    };

    rendered = cli._format_file_optimize_payload(payload);

    assert "failure_type: property_test_failure" in rendered;
    assert "failed_candidate: candidate_0" in rendered;
    assert "falsifying_example:" in rendered;
    assert "n=-1" in rendered;
    assert "candidate_output:" in rendered;
    assert "return n * (n - 1) // 2" in rendered;
}


test "reporting creates timing graph artifact" {
    reporting = importlib.import_module("src.core.reporting");
    result = {
        "run_id": "unit_test_run",
        "run_log_path": "/tmp/unit_test_run.jsonl",
        "improvement_ratio": 2.0,
        "is_significant": True,
        "confidence": 0.99,
        "baseline_metrics": {"execution_time": 0.02},
        "metrics": {"execution_time": 0.01}
    };

    artifact = reporting.create_optimization_artifacts(
        result,
        artifact_prefix="unit_test_report",
        title="Unit Test Timing"
    );
    try {
        assert artifact["baseline_time_ms"] == 20.0;
        assert artifact["optimized_time_ms"] == 10.0;
        assert os.path.exists(artifact["timing_graph_path"]);
        assert os.path.exists(artifact["summary_json_path"]);
    } finally {
        if os.path.exists(artifact["timing_graph_path"]) {
            os.remove(artifact["timing_graph_path"]);
        }
        if os.path.exists(artifact["summary_json_path"]) {
            os.remove(artifact["summary_json_path"]);
        }
    }
}


test "ringtail cli collects repo log paths from job payload" {
    cli = importlib.import_module("src.ringtail_cli");
    payload = {
        "run_log_path": "/tmp/async.jsonl",
        "result": {
            "run_log_path": "/tmp/repo.jsonl",
            "artifacts": {
                "run_log_paths": ["/tmp/candidate_a.jsonl", "/tmp/candidate_b.jsonl"]
            },
            "candidate_summaries": [
                {"run_log_path": "/tmp/candidate_a.jsonl"},
                {"run_log_path": "/tmp/candidate_c.jsonl"}
            ],
            "child_jobs": [
                {"run_log_path": "/tmp/child.jsonl"}
            ]
        }
    };

    paths = cli._collect_repo_log_paths(payload);

    assert len(paths) == 6;
    assert "/tmp/async.jsonl" in paths;
    assert "/tmp/repo.jsonl" in paths;
    assert "/tmp/candidate_c.jsonl" in paths;
    assert "/tmp/child.jsonl" in paths;
}


test "ringtail cli formats json log lines for tailing" {
    cli = importlib.import_module("src.ringtail_cli");
    line = '{"elapsed_s": 1.25, "kind": "optimization_step", "iteration": 1, "improvement_ratio": 1.4, "is_significant": true}';

    rendered = cli._format_log_line("/tmp/example.jsonl", line);

    assert "[example.jsonl]" in rendered;
    assert "optimization_step" in rendered;
    assert "improvement_ratio=1.4" in rendered;
    assert "is_significant=True" in rendered;
}


test "ringtail cli formats observability log lines" {
    cli = importlib.import_module("src.ringtail_cli");
    llm_line = '{"elapsed_s": 0.75, "kind": "llm_call", "phase": "analyze_and_plan", "model": "claude-opus-4-6", "prompt_tokens": 200, "completion_tokens": 80}';
    plan_line = '{"elapsed_s": 0.90, "kind": "plan_summary", "backend": "llm", "step_count": 3, "candidate_count": 2, "analysis_excerpt": "Nested loops dominate runtime"}';
    candidate_line = '{"elapsed_s": 1.05, "kind": "candidate_plan", "iteration": 1, "candidate_label": "loop-overhead", "steps": ["Reduce loop overhead"]}';

    llm_rendered = cli._format_log_line("/tmp/example.jsonl", llm_line);
    plan_rendered = cli._format_log_line("/tmp/example.jsonl", plan_line);
    candidate_rendered = cli._format_log_line("/tmp/example.jsonl", candidate_line);

    assert "llm_call" in llm_rendered;
    assert "phase=analyze_and_plan" in llm_rendered;
    assert "model=claude-opus-4-6" in llm_rendered;
    assert "plan_summary" in plan_rendered;
    assert "Nested loops dominate runtime" in plan_rendered;
    assert "candidate_plan" in candidate_rendered;
    assert "loop-overhead" in candidate_rendered;
}
