"""
High-level repo agent orchestration for the CLI-first workflow.
"""
from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.core.github_repo_service import (
    build_pr_body,
    clone_repo,
    commit_all,
    create_branch,
    create_pull_request,
    is_local_repo_url,
    make_branch_name,
    push_branch,
    resolve_github_token,
)
from src.core.repo_workspace import run_repo_commands

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_WORKER_PATH = _WORKSPACE_ROOT / "src" / "core" / "async_optimize_worker.jac"


def normalize_repo_job_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise TypeError("repo agent request must be a dict")
    repo_url = str(request.get("repo_url", "")).strip()
    prompt = str(request.get("prompt", "")).strip()
    if not repo_url:
        raise ValueError("repo_url is required")
    if not prompt:
        raise ValueError("prompt is required")

    normalized = dict(request)
    normalized["operation"] = "run_repo_agent_job"
    normalized["repo_url"] = repo_url
    normalized["prompt"] = prompt
    normalized["base_branch"] = str(request.get("base_branch", "main"))
    normalized["tests_root"] = str(request.get("tests_root", "tests"))
    normalized["max_targets"] = max(1, int(request.get("max_targets", 3)))
    normalized["config_name"] = request.get("config_name", "default")
    normalized["analysis_mode"] = request.get("analysis_mode", "llm")
    normalized["publish_pr"] = bool(request.get("publish_pr", False))
    normalized["setup_commands"] = list(request.get("setup_commands", []))
    normalized["test_command"] = request.get("test_command", None)
    normalized["backend_config"] = dict(request.get("backend_config", {"backend": "blaxel"}))
    normalized["token"] = request.get("token", None)
    normalized["replay_script"] = request.get("replay_script", None)
    normalized["branch_name"] = request.get("branch_name", None)
    return normalized


def run_repo_agent_job(request: dict[str, Any]) -> dict[str, Any]:
    job = normalize_repo_job_request(request)
    temp_root = tempfile.mkdtemp(prefix="ringtail_repo_agent_")
    clone_path = os.path.join(temp_root, "repo")
    token = resolve_github_token(job.get("token"))

    try:
        clone_repo(job["repo_url"], clone_path, job["base_branch"], token or None)
        tests_root = _resolve_repo_path(clone_path, job["tests_root"])
        replay_script = _resolve_optional_repo_path(clone_path, job.get("replay_script"))

        ranked_candidates = _rank_repo_candidates(clone_path, tests_root, replay_script, job)
        ranked_candidates = _apply_prompt_focus(job["prompt"], ranked_candidates)
        max_targets = min(job["max_targets"], len(ranked_candidates))
        selected_candidates = ranked_candidates[:max_targets]
        if not selected_candidates:
            raise ValueError("No candidate targets were found in the repository")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_targets) as pool:
            future_map = {
                pool.submit(_evaluate_candidate, clone_path, tests_root, replay_script, job, entry): entry
                for entry in selected_candidates
            }
            candidate_results = [future.result() for future in concurrent.futures.as_completed(future_map)]

        winner = _select_best_candidate(candidate_results)
        if winner is None:
            raise RuntimeError("No verified optimization candidate succeeded")

        winner_entry = winner["entry"]
        winner_result = winner["result"]
        source_file = str(winner_entry.get("source_file", ""))
        Path(source_file).write_text(str(winner_result.get("optimized_code", "")))

        validation_commands = list(job["setup_commands"])
        if job.get("test_command"):
            validation_commands.append(str(job["test_command"]))
        validation_result = run_repo_commands(
            clone_path,
            validation_commands,
            config=job["backend_config"],
        )
        if not validation_result.get("success", False):
            raise RuntimeError("Repository validation failed: " + str(validation_result.get("stderr", "")))

        branch_name = job.get("branch_name") or make_branch_name("ringtail")
        pr_title = _build_pr_title(job["prompt"], winner_entry)
        pr_body = build_pr_body(
            prompt=job["prompt"],
            target_summary=_target_summary(winner_entry),
            test_summary=_test_summary(validation_result, winner_result),
            performance_summary=_performance_summary(winner_result),
        )

        pull_request = {
            "title": pr_title,
            "body": pr_body,
            "head_branch": branch_name,
            "base_branch": job["base_branch"],
            "url": "",
            "published": False,
        }

        commit_sha = ""
        if job.get("publish_pr", False):
            create_branch(clone_path, branch_name)
            commit_sha = commit_all(clone_path, pr_title)
            push_branch(clone_path, job["repo_url"], branch_name, token)
            pr_data = create_pull_request(
                repo_url=job["repo_url"],
                title=pr_title,
                body=pr_body,
                head_branch=branch_name,
                base_branch=job["base_branch"],
                token=token,
            )
            pull_request["url"] = str(pr_data.get("html_url", ""))
            pull_request["published"] = True
            pull_request["number"] = pr_data.get("number", None)
        else:
            pull_request["preview_only"] = True

        return {
            "success": True,
            "repo_url": job["repo_url"],
            "base_branch": job["base_branch"],
            "prompt": job["prompt"],
            "clone_path": clone_path if request.get("keep_repo_checkout", False) else "",
            "rank_strategy": "replay_repo" if replay_script else "directory_rank",
            "candidate_count": len(ranked_candidates),
            "evaluated_candidate_count": len(candidate_results),
            "selected_target": {
                "source_file": winner_entry.get("source_file", ""),
                "function_name": winner_entry.get("function_name", ""),
                "selection_score": winner_entry.get("selection_score", 0.0),
            },
            "candidate_results": candidate_results,
            "winner_result": winner_result,
            "validation_result": validation_result,
            "branch_name": branch_name,
            "commit_sha": commit_sha,
            "pull_request": pull_request,
        }
    finally:
        if not request.get("keep_repo_checkout", False):
            shutil.rmtree(temp_root, ignore_errors=True)


def _rank_repo_candidates(
    clone_path: str,
    tests_root: str,
    replay_script: str | None,
    job: dict[str, Any],
) -> list[dict[str, Any]]:
    if replay_script:
        return _run_worker_request(
            {
                "operation": "discover_and_rank_replay_repo",
                "source_root": clone_path,
                "script_path": replay_script,
                "tests_root": tests_root,
                "limit": max(job["max_targets"] * 2, job["max_targets"]),
            }
        )
    return _run_worker_request(
        {
            "operation": "discover_and_rank_directory",
            "source_root": clone_path,
            "tests_root": tests_root,
            "limit": max(job["max_targets"] * 2, job["max_targets"]),
        }
    )


def _evaluate_candidate(
    clone_path: str,
    tests_root: str,
    replay_script: str | None,
    job: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    if replay_script:
        request = {
            "operation": "optimize_replay_function",
            "file_path": entry.get("source_file"),
            "function_name": entry.get("function_name"),
            "script_path": replay_script,
            "tests_root": tests_root,
            "criteria_name": job.get("criteria_name", None),
            "config_name": job.get("config_name"),
            "analysis_mode": job.get("analysis_mode"),
            "llm_model": job.get("llm_model", None),
            "enable_run_log": True,
        }
    else:
        request = {
            "operation": "optimize_file_function",
            "file_path": entry.get("source_file"),
            "function_name": entry.get("function_name"),
            "function_call": entry.get("function_call"),
            "tests_root": tests_root,
            "criteria_name": job.get("criteria_name", None),
            "config_name": job.get("config_name"),
            "analysis_mode": job.get("analysis_mode"),
            "llm_model": job.get("llm_model", None),
            "enable_run_log": True,
        }
    result = _run_worker_request(request)
    return {
        "entry": copy.deepcopy(entry),
        "result": result,
        "score": _candidate_score(entry, result),
        "success": bool(result.get("test_passed", False)) and not result.get("error"),
    }


def _candidate_score(entry: dict[str, Any], result: dict[str, Any]) -> float:
    improvement = float(result.get("improvement_ratio", 0.0))
    significance = 1.0 if bool(result.get("is_significant", False)) else 0.0
    selection = float(entry.get("selection_score", entry.get("median_ms", 0.0)))
    return improvement * 1000.0 + significance * 100.0 + selection


def _select_best_candidate(candidate_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [entry for entry in candidate_results if entry.get("success", False)]
    if not passing:
        return None
    passing.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return passing[0]


def _run_worker_request(request: dict[str, Any]) -> Any:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        json.dump(request, handle)
        request_file = handle.name
    try:
        env = os.environ.copy()
        env["RINGTAIL_ASYNC_REQUEST_FILE"] = request_file
        proc = subprocess.run(
            ["jac", "run", str(_WORKER_PATH)],
            cwd=str(_WORKSPACE_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        result = _extract_json_result(proc.stdout)
        if proc.returncode != 0:
            raise RuntimeError(result.get("error", proc.stderr.strip() or "worker request failed"))
        if isinstance(result, dict) and result.get("error") and "Unsupported optimization operation" in str(result["error"]):
            raise RuntimeError(str(result["error"]))
        return result
    finally:
        os.remove(request_file)


def _extract_json_result(stdout: str) -> Any:
    for raw_line in reversed(stdout.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Worker did not produce JSON output")


def _apply_prompt_focus(prompt: str, ranked_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompt_lower = prompt.lower()
    rescored: list[dict[str, Any]] = []
    for entry in ranked_candidates:
        bonus = 0.0
        source_file = str(entry.get("source_file", "")).lower()
        function_name = str(entry.get("function_name", "")).lower()
        if function_name and function_name in prompt_lower:
            bonus += 50000.0
        filename = os.path.basename(source_file)
        if filename and filename.lower() in prompt_lower:
            bonus += 25000.0
        updated = dict(entry)
        updated["selection_score"] = float(updated.get("selection_score", updated.get("median_ms", 0.0))) + bonus
        rescored.append(updated)
    rescored.sort(key=lambda item: float(item.get("selection_score", 0.0)), reverse=True)
    return rescored


def _resolve_repo_path(repo_root: str, raw_path: str) -> str:
    if os.path.isabs(raw_path):
        return raw_path
    return os.path.join(repo_root, raw_path)


def _resolve_optional_repo_path(repo_root: str, raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    return _resolve_repo_path(repo_root, str(raw_path))


def _build_pr_title(prompt: str, entry: dict[str, Any]) -> str:
    return f"Optimize {entry.get('function_name', 'target')} for performance"


def _target_summary(entry: dict[str, Any]) -> str:
    return f"{entry.get('source_file', '')}::{entry.get('function_name', '')}"


def _test_summary(validation_result: dict[str, Any], winner_result: dict[str, Any]) -> str:
    if validation_result.get("commands"):
        last = validation_result["commands"][-1]
        return f"{last.get('command', '')} (success={last.get('success', False)})"
    return f"optimization tests passed={winner_result.get('test_passed', False)}"


def _performance_summary(winner_result: dict[str, Any]) -> str:
    return (
        f"improvement_ratio={winner_result.get('improvement_ratio', 0.0)}, "
        f"is_significant={winner_result.get('is_significant', False)}"
    )
