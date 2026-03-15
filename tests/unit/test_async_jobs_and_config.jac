"""Focused tests for async optimization jobs and shipped model defaults."""

import os;
import tempfile;
import time;

import importlib;

import from config.agent_config { get_agent_config, resolve_default_llm_model }
import from main { get_optimization_job, submit_optimization_job }


def _write(path: str, content: str) -> None {
    with open(path, "w") as f {
        f.write(content);
    }
}


def _wait_for_job(job_id: str, timeout_s: float = 40.0) -> dict {
    started = time.time();
    status = get_optimization_job(job_id);
    while status.get("status", "") != "succeeded" and status.get("status", "") != "failed" {
        if time.time() - started > timeout_s {
            return status;
        }
        time.sleep(0.5);
        status = get_optimization_job(job_id);
    }
    return status;
}


test "submit_optimization_job runs file optimization asynchronously" {
    tmp_dir = tempfile.mkdtemp(prefix="ringtail_async_job_");
    try {
        module_path = os.path.join(tmp_dir, "sum_up.py");
        _write(
            module_path,
            "def sum_up(n: int):\n    total = 0\n    for i in range(n):\n        total += i\n    return total\n"
        );

        request = {
            "operation": "optimize_file_function",
            "file_path": module_path,
            "function_name": "sum_up",
            "function_call": "sum_up(10)",
            "tests_root": "tests",
            "config_name": "test-fast"
        };
        submitted = submit_optimization_job(request);

        assert submitted["status"] in ["queued", "running"];
        assert submitted["run_id"] != "";
        assert submitted["run_log_path"] != "";

        finished = _wait_for_job(submitted["job_id"]);
        assert finished["status"] == "succeeded";
        assert finished["result"]["test_passed"] is True;
        assert finished["result"]["run_id"] == finished["run_id"];
        assert finished["result"]["run_log_path"] == finished["run_log_path"];
    } finally {
        os.remove(module_path);
        os.rmdir(tmp_dir);
    }
}


test "get_optimization_job reports unknown ids" {
    missing = get_optimization_job("missing-job");

    assert missing["status"] == "not_found";
    assert "Unknown job_id" in missing["error"];
}


test "default model resolution honors env override and heuristic profile stays empty" {
    old_model = os.environ.get("RINGTAIL_DEFAULT_LLM_MODEL", None);
    try {
        os.environ["RINGTAIL_DEFAULT_LLM_MODEL"] = "claude-opus-test";

        default_cfg = get_agent_config("default");
        heuristic_cfg = get_agent_config("heuristic");
        client_mod = importlib.import_module("src.utils.llm_client");

        assert resolve_default_llm_model(None) == "claude-opus-test";
        assert resolve_default_llm_model("claude-manual") == "claude-manual";
        assert default_cfg.llm_model == "claude-opus-test";
        assert heuristic_cfg.llm_model == "";
        assert client_mod._resolve_model(None) == "claude-opus-test";
        assert client_mod._resolve_model("claude-manual") == "claude-manual";
    } finally {
        if old_model is None {
            os.environ.pop("RINGTAIL_DEFAULT_LLM_MODEL", None);
        } else {
            os.environ["RINGTAIL_DEFAULT_LLM_MODEL"] = old_model;
        }
    }
}


test "persisted async jobs reload from disk and interrupted jobs are marked" {
    module = importlib.import_module("src.core.async_jobs");
    jobs_dir = module.get_jobs_dir();
    job_path = os.path.join(jobs_dir, "persisted-job.json");
    try {
        with open(job_path, "w") as f {
            f.write(
                '{"job_id":"persisted-job","status":"running","submitted_at":"2026-03-15T00:00:00Z","started_at":"2026-03-15T00:00:01Z","finished_at":null,"run_id":"persisted-run","run_name":"persisted-run","run_log_path":"logs/persisted-run.jsonl","request_summary":{"operation":"optimize_input"},"error":"","result":null,"pid":1234}'
            );
        }

        manager = module.AsyncJobManager();
        recovered = manager.get_job("persisted-job");

        assert recovered["status"] == "interrupted";
        assert "restarted" in recovered["error"];
    } finally {
        if os.path.exists(job_path) {
            os.remove(job_path);
        }
    }
}
