"""
High-level repo agent orchestration for the CLI-first workflow.
"""
from __future__ import annotations

import concurrent.futures
import copy
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from src.core.github_repo_service import (
    build_pr_body,
    clone_repo,
    commit_all,
    create_branch,
    create_pull_request,
    make_branch_name,
    push_branch,
    resolve_github_auth,
    verify_repo_access,
)
from src.core.reporting import create_repo_job_artifacts
from src.core.repo_workspace import detect_repo_bootstrap, run_repo_commands, run_ringtail_worker_request


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
    raw_auth = request.get("auth", {})
    normalized["auth"] = dict(raw_auth) if isinstance(raw_auth, dict) else {}
    if request.get("installation_id", None) is not None:
        normalized["auth"]["installation_id"] = request.get("installation_id")
    normalized["replay_script"] = request.get("replay_script", None)
    normalized["branch_name"] = request.get("branch_name", None)
    return normalized


def run_repo_agent_job(request: dict[str, Any]) -> dict[str, Any]:
    job = normalize_repo_job_request(request)
    temp_root = tempfile.mkdtemp(prefix="ringtail_repo_agent_")
    clone_path = os.path.join(temp_root, "repo")
    auth_context = resolve_github_auth(auth=job.get("auth", {}), explicit_token=job.get("token"))
    token = str(auth_context.get("token", ""))
    phase = "auth"

    try:
        phase = "preflight"
        repo_access = verify_repo_access(job["repo_url"], auth=job.get("auth", {}), explicit_token=job.get("token"))
        phase = "clone"
        clone_repo(job["repo_url"], clone_path, job["base_branch"], token or None)
        tests_root = _resolve_repo_path(clone_path, job["tests_root"])
        replay_script = _resolve_optional_repo_path(clone_path, job.get("replay_script"))
        phase = "bootstrap"
        bootstrap = detect_repo_bootstrap(
            clone_path,
            explicit_setup_commands=job.get("setup_commands", []),
            explicit_test_command=job.get("test_command", None),
        )

        phase = "rank"
        ranked_candidates = _rank_repo_candidates(clone_path, tests_root, replay_script, job)
        ranked_candidates = _apply_prompt_focus(job["prompt"], ranked_candidates)
        max_targets = min(job["max_targets"], len(ranked_candidates))
        selected_candidates = ranked_candidates[:max_targets]
        if not selected_candidates:
            raise ValueError("No candidate targets were found in the repository")

        phase = "optimize"
        candidate_results, child_jobs = _evaluate_candidates(
            clone_path,
            tests_root,
            replay_script,
            job,
            selected_candidates,
        )

        winner = _select_best_candidate(candidate_results)
        if winner is None:
            raise RuntimeError("No verified optimization candidate succeeded")

        winner_entry = winner["entry"]
        winner_result = winner["result"]
        source_file = str(winner_entry.get("source_file", ""))
        Path(source_file).write_text(str(winner_result.get("optimized_code", "")))

        phase = "validate"
        validation_commands = list(bootstrap.get("setup_commands", []))
        if bootstrap.get("test_command", "") != "":
            validation_commands.append(str(bootstrap["test_command"]))
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
            notes=[
                "Auth mode: " + str(auth_context.get("mode", "none")),
                "Repo strategy: " + ("replay_repo" if replay_script else "directory_rank"),
                "Evaluated candidates: " + str(len(candidate_results)),
            ],
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
            phase = "git"
            create_branch(clone_path, branch_name)
            commit_sha = commit_all(clone_path, pr_title)
            push_branch(clone_path, job["repo_url"], branch_name, token)
            phase = "pull_request"
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

        report_artifacts = create_repo_job_artifacts(
            {
                "repo_url": job["repo_url"],
                "prompt": job["prompt"],
                "candidate_count": len(ranked_candidates),
                "evaluated_candidate_count": len(candidate_results),
                "selected_target": {
                    "source_file": winner_entry.get("source_file", ""),
                    "function_name": winner_entry.get("function_name", ""),
                    "selection_score": winner_entry.get("selection_score", 0.0),
                },
                "candidate_summaries": _candidate_summaries(candidate_results),
                "winner_result": winner_result,
                "validation_result": validation_result,
                "pull_request": pull_request,
            }
        )

        return {
            "success": True,
            "repo_url": job["repo_url"],
            "base_branch": job["base_branch"],
            "prompt": job["prompt"],
            "clone_path": clone_path if request.get("keep_repo_checkout", False) else "",
            "auth": {
                "mode": auth_context.get("mode", "none"),
                "installation_id": auth_context.get("installation_id", None),
                "expires_at": auth_context.get("expires_at", None),
            },
            "phase": "done",
            "repo_access": repo_access,
            "bootstrap": bootstrap,
            "rank_strategy": "replay_repo" if replay_script else "directory_rank",
            "candidate_count": len(ranked_candidates),
            "evaluated_candidate_count": len(candidate_results),
            "selected_target": {
                "source_file": winner_entry.get("source_file", ""),
                "function_name": winner_entry.get("function_name", ""),
                "selection_score": winner_entry.get("selection_score", 0.0),
            },
            "candidate_results": candidate_results,
            "candidate_summaries": _candidate_summaries(candidate_results),
            "child_jobs": child_jobs,
            "winner_result": winner_result,
            "summary_stats": report_artifacts,
            "validation_result": validation_result,
            "branch_name": branch_name,
            "commit_sha": commit_sha,
            "artifacts": {
                "run_log_paths": _run_log_paths(candidate_results),
                "validation_commands": validation_result.get("commands", []),
                "summary_json_path": report_artifacts.get("summary_json_path", ""),
                "timing_graph_path": report_artifacts.get("timing_graph_path", ""),
            },
            "pull_request": pull_request,
        }
    except Exception as exc:
        raise RuntimeError(f"[{phase}] {exc}") from exc
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
            },
            repo_path=clone_path,
            backend_config=_ranking_backend_config(job),
        )
    return _run_worker_request(
        {
            "operation": "discover_and_rank_directory",
            "source_root": clone_path,
            "tests_root": tests_root,
            "limit": max(job["max_targets"] * 2, job["max_targets"]),
        },
        repo_path=clone_path,
        backend_config=_ranking_backend_config(job),
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
    result = _run_worker_request(
        request,
        repo_path=clone_path,
        backend_config=_candidate_backend_config(job),
    )
    return {
        "entry": copy.deepcopy(entry),
        "result": result,
        "score": _candidate_score(entry, result),
        "success": bool(result.get("test_passed", False)) and not result.get("error"),
        "job_id": "",
    }


def _evaluate_candidates(
    clone_path: str,
    tests_root: str,
    replay_script: str | None,
    job: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend_type = str(job.get("backend_config", {}).get("backend", "local"))
    fanout_mode = str(job.get("backend_config", {}).get("fanout_mode", ""))
    if backend_type == "local" and fanout_mode != "child_jobs":
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_candidates)) as pool:
            future_map = {
                pool.submit(_evaluate_candidate, clone_path, tests_root, replay_script, job, entry): entry
                for entry in selected_candidates
            }
            results = [future.result() for future in concurrent.futures.as_completed(future_map)]
        return results, []

    if backend_type == "blaxel":
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_candidates)) as pool:
            future_map = {
                pool.submit(_evaluate_candidate, clone_path, tests_root, replay_script, job, entry): entry
                for entry in selected_candidates
            }
            results = [future.result() for future in concurrent.futures.as_completed(future_map)]
        child_jobs = []
        for result in results:
            entry = result.get("entry", {})
            child_jobs.append(
                {
                    "job_id": "",
                    "source_file": entry.get("source_file", ""),
                    "function_name": entry.get("function_name", ""),
                    "backend": "blaxel",
                    "status": "succeeded" if result.get("success", False) else "failed",
                    "run_log_path": result.get("result", {}).get("run_log_path", ""),
                    "execution_mode": "blaxel_remote_worker",
                }
            )
        return results, child_jobs

    return _evaluate_candidates_via_child_jobs(clone_path, tests_root, replay_script, job, selected_candidates)


def _evaluate_candidates_via_child_jobs(
    clone_path: str,
    tests_root: str,
    replay_script: str | None,
    job: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    async_jobs = _async_jobs_module()
    submitted_jobs: list[dict[str, Any]] = []
    child_job_prefix = str(job.get("run_id", "")) or ("repo_agent_" + os.urandom(4).hex())
    for index, entry in enumerate(selected_candidates):
        request = _candidate_request(clone_path, tests_root, replay_script, job, entry)
        request["job_id"] = f"{child_job_prefix}_candidate_{index}"
        request["run_name"] = "candidate-" + str(entry.get("function_name", index))
        request["parent_job_id"] = str(job.get("job_id", ""))
        submitted = async_jobs.submit_job(request)
        submitted_jobs.append(
            {
                "job_id": submitted["job_id"],
                "source_file": entry.get("source_file", ""),
                "function_name": entry.get("function_name", ""),
                "backend": job.get("backend_config", {}).get("backend", "local"),
                "status": submitted.get("status", "queued"),
            }
        )

    results: list[dict[str, Any]] = []
    for child in submitted_jobs:
        finished = _wait_for_child_job(async_jobs, str(child["job_id"]))
        result = finished.get("result", {}) if isinstance(finished.get("result"), dict) else {}
        entry = _match_candidate_entry(selected_candidates, child)
        results.append(
            {
                "entry": copy.deepcopy(entry),
                "result": result,
                "score": _candidate_score(entry, result),
                "success": bool(result.get("test_passed", False)) and not result.get("error"),
                "job_id": child["job_id"],
                "job_status": finished.get("status", ""),
                "backend": child["backend"],
            }
        )
        child["status"] = finished.get("status", "")
        child["run_log_path"] = result.get("run_log_path", "")
        child["error"] = finished.get("error", "")

    return results, submitted_jobs


def _candidate_request(
    clone_path: str,
    tests_root: str,
    replay_script: str | None,
    job: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    if replay_script:
        return {
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
    return {
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


def _wait_for_child_job(async_jobs: Any, job_id: str, timeout_s: float = 180.0) -> dict[str, Any]:
    started = time.time()
    status = async_jobs.get_job(job_id)
    while str(status.get("status", "")) not in {"succeeded", "failed", "interrupted"}:
        if time.time() - started > timeout_s:
            return status
        time.sleep(0.5)
        status = async_jobs.get_job(job_id)
    return status


def _match_candidate_entry(selected_candidates: list[dict[str, Any]], child: dict[str, Any]) -> dict[str, Any]:
    target_file = str(child.get("source_file", ""))
    target_function = str(child.get("function_name", ""))
    for entry in selected_candidates:
        if str(entry.get("source_file", "")) == target_file and str(entry.get("function_name", "")) == target_function:
            return entry
    return selected_candidates[0]


def _async_jobs_module() -> Any:
    mod = __import__("src.core.async_jobs", fromlist=["submit_job"])
    return mod


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


def _run_worker_request(
    request: dict[str, Any],
    *,
    repo_path: str | None = None,
    backend_config: dict[str, Any] | None = None,
) -> Any:
    result = run_ringtail_worker_request(
        request,
        repo_path=repo_path,
        backend_config=backend_config,
    )
    if isinstance(result, dict) and result.get("error") and "Unsupported optimization operation" in str(result["error"]):
        raise RuntimeError(str(result["error"]))
    return result


def _candidate_backend_config(job: dict[str, Any]) -> dict[str, Any]:
    return dict(job.get("backend_config", {}))


def _ranking_backend_config(job: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(job.get("backend_config", {}))
    if cfg.get("backend", "local") == "blaxel" and not bool(cfg.get("remote_rank", False)):
        cfg["backend"] = "local"
    return cfg


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


def _candidate_summaries(candidate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for candidate in candidate_results:
        entry = candidate.get("entry", {})
        result = candidate.get("result", {})
        summaries.append(
            {
                "source_file": entry.get("source_file", ""),
                "function_name": entry.get("function_name", ""),
                "success": bool(candidate.get("success", False)),
                "score": float(candidate.get("score", 0.0)),
                "improvement_ratio": float(result.get("improvement_ratio", 0.0)),
                "is_significant": bool(result.get("is_significant", False)),
                "run_log_path": result.get("run_log_path", ""),
                "error": result.get("error", ""),
            }
        )
    summaries.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return summaries


def _run_log_paths(candidate_results: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for candidate in candidate_results:
        path = str(candidate.get("result", {}).get("run_log_path", ""))
        if path != "" and path not in paths:
            paths.append(path)
    return paths
