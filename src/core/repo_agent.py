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
    working_tree_has_changes,
)
from src.core.optimization_request_contract import (
    DEFAULT_ANALYSIS_MODE,
    DEFAULT_CONFIG_NAME,
    DEFAULT_ENABLE_RUN_LOG,
    normalize_request_defaults,
)
from src.core.reporting import create_repo_job_artifacts
from src.core.repo_workspace import detect_repo_bootstrap, run_repo_commands, run_ringtail_worker_request
from src.utils.run_log import RunLog


def normalize_repo_job_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise TypeError("repo agent request must be a dict")
    repo_url = str(request.get("repo_url", "")).strip()
    prompt = str(request.get("prompt", "")).strip() or "optimize for performance"
    entry_point = str(request.get("entry_point", "")).strip()
    if not repo_url:
        raise ValueError("repo_url is required")
    if not entry_point:
        raise ValueError(
            "entry_point is required for repo jobs. "
            "Please provide an explicit command such as 'python runner.py'."
        )

    normalized = normalize_request_defaults(dict(request))
    normalized["operation"] = "run_repo_agent_job"
    normalized["repo_url"] = repo_url
    normalized["prompt"] = prompt
    normalized["base_branch"] = str(request.get("base_branch", "main"))
    normalized["tests_root"] = str(request.get("tests_root", "tests"))
    normalized["max_targets"] = max(1, int(request.get("max_targets", 3)))
    normalized["config_name"] = request.get("config_name", DEFAULT_CONFIG_NAME)
    normalized["analysis_mode"] = request.get("analysis_mode", DEFAULT_ANALYSIS_MODE)
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
    normalized["entry_point"] = entry_point
    return normalized


def run_repo_agent_job(request: dict[str, Any]) -> dict[str, Any]:
    job = normalize_repo_job_request(request)
    if not str(job.get("entry_point", "")).strip():
        raise ValueError(
            "entry_point is required for repo jobs. "
            "Please provide an explicit command such as 'python runner.py'."
        )
    temp_root = tempfile.mkdtemp(prefix="ringtail_repo_agent_")
    clone_path = os.path.join(temp_root, "repo")
    run_log = _maybe_create_repo_run_log(request)
    auth_context: dict[str, Any] = {
        "mode": "none",
        "token": "",
        "installation_id": None,
        "expires_at": None,
    }
    token = ""
    phase = "auth"
    branch_name = str(job.get("branch_name") or "")

    try:
        _safe_log_event(
            run_log,
            "repo_job_request",
            repo_url=job["repo_url"],
            base_branch=job["base_branch"],
            publish_pr=bool(job.get("publish_pr", False)),
            has_session_auth=bool(job.get("auth", {})),
        backend=str(job.get("backend_config", {}).get("backend", "")),
        )
        auth_context = resolve_github_auth(auth=job.get("auth", {}), explicit_token=job.get("token"))
        token = str(auth_context.get("token", ""))
        _safe_log_event(
            run_log,
            "repo_auth_resolved",
            auth_mode=auth_context.get("mode", "none"),
            installation_id=auth_context.get("installation_id", None),
            token_available=bool(token),
        )
        phase = "preflight"
        _safe_log_event(run_log, "repo_phase", phase=phase, state="start")
        repo_access = verify_repo_access(job["repo_url"], auth=job.get("auth", {}), explicit_token=job.get("token"))
        _safe_log_event(
            run_log,
            "repo_phase",
            phase=phase,
            state="complete",
            success=bool(repo_access.get("success", False)),
            auth_mode=repo_access.get("auth_mode", ""),
            installation_id=repo_access.get("installation_id", None),
            default_branch=repo_access.get("default_branch", ""),
        )
        phase = "clone"
        _safe_log_event(
            run_log,
            "repo_phase",
            phase=phase,
            state="start",
            base_branch=job["base_branch"],
        )
        clone_repo(job["repo_url"], clone_path, job["base_branch"], token or None)
        phase = "bootstrap"
        _safe_log_event(run_log, "repo_phase", phase=phase, state="start")
        bootstrap = detect_repo_bootstrap(
            clone_path,
            explicit_setup_commands=job.get("setup_commands", []),
            explicit_test_command=job.get("test_command", None),
        )
        _safe_log_event(
            run_log,
            "repo_bootstrap",
            setup_command_count=len(bootstrap.get("setup_commands", [])),
            has_test_command=bool(str(bootstrap.get("test_command", "")).strip()),
            venv_python=str(bootstrap.get("venv_python", "")),
        )

        # Run setup commands (create venv, install deps)
        if bootstrap.get("setup_commands"):
            _safe_log_event(
                run_log,
                "repo_setup_commands",
                command_count=len(bootstrap.get("setup_commands", [])),
            )
            setup_result = run_repo_commands(
                clone_path,
                bootstrap["setup_commands"],
                config=job["backend_config"],
            )
            if not setup_result.get("success", False):
                failed_cmd = ""
                for step in setup_result.get("commands", []):
                    if not step.get("success", False):
                        failed_cmd = step.get("command", "")
                        break
                raise RuntimeError(
                    f"Setup command failed: {failed_cmd}\n"
                    f"stderr: {setup_result.get('stderr', '')[:500]}"
                )

        venv_python = bootstrap.get("venv_python", "")

        # Entry point is required for repo jobs; do not infer it.
        phase = "entry_point"
        entry_point = str(job.get("entry_point", "")).strip()
        if not entry_point:
            raise ValueError(
                "entry_point is required for repo jobs. "
                "Please provide an explicit command such as 'python runner.py'."
            )
        _safe_log_event(
            run_log,
            "repo_entry_point",
            entry_point=entry_point,
            auto_detected=False,
        )

        # Profile the repo via the entry point
        phase = "profile"
        _safe_log_event(run_log, "repo_phase", phase=phase, state="start", entry_point=entry_point)
        from src.core.cprofile_analyzer import (
            build_call_dag,
            compute_hotness_threshold,
            run_cprofile_analysis,
        )
        analysis = run_cprofile_analysis(clone_path, entry_point, venv_python=venv_python)

        hot_functions = compute_hotness_threshold(analysis)
        _safe_log_event(
            run_log,
            "repo_profile_summary",
            total_time=analysis.total_time,
            functions_analyzed=len(analysis.functions),
            hot_functions=len(hot_functions),
        )
        validation_result: dict[str, Any] = {
            "success": True,
            "backend": str(job.get("backend_config", {}).get("backend", "local")),
            "commands": [],
            "stdout": "",
            "stderr": "",
        }
        function_summaries: list[dict[str, Any]] = []
        optimization_summary: dict[str, Any] = {
            "total_functions": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "baseline_total_time": None,
            "optimized_total_time": None,
            "overall_speedup": None,
        }
        profiling_dag_levels = 0
        smoke_test_only = False
        smoke_test_artifact = ""

        if not hot_functions:
            if job.get("publish_pr", False):
                phase = "smoke_test_change"
                smoke_test_only = True
                smoke_test_artifact = _write_pr_smoke_test_artifact(
                    clone_path=clone_path,
                    job=job,
                    analysis=analysis,
                    entry_point=entry_point,
                    auth_context=auth_context,
                    reason="No significant bottlenecks detected; emitting a commit so PR publishing can be verified.",
                )
                validation_result["smoke_test_artifact"] = smoke_test_artifact
                _safe_log_event(
                    run_log,
                    "repo_smoke_test_change",
                    artifact_path=smoke_test_artifact,
                    reason="no_bottlenecks",
                )
            else:
                _safe_log_event(run_log, "repo_job_complete", result="no_bottlenecks")
                return {
                    "success": True,
                    "repo_url": job["repo_url"],
                    "entry_point": entry_point,
                    "bootstrap": bootstrap,
                    "validation_result": validation_result,
                    "pull_request": {"preview_only": True},
                    "message": "No significant bottlenecks detected",
                    "total_time": analysis.total_time,
                    "functions_analyzed": len(analysis.functions),
                    "phase": "profile",
                    "run_id": getattr(run_log, "run_id", ""),
                    "run_log_path": getattr(run_log, "log_path", ""),
                }

        if not smoke_test_only:
            dag = build_call_dag(analysis, hot_functions)
            profiling_dag_levels = len(dag.levels)

            # Capture real arguments for hot functions
            phase = "capture"
            _safe_log_event(run_log, "repo_phase", phase=phase, state="start", target_count=len(dag.nodes))
            from src.core.arg_capture import capture_function_io
            target_functions = {
                k: {"module": v.module, "name": v.name, "file_path": v.file_path}
                for k, v in dag.nodes.items()
            }
            io_data = capture_function_io(clone_path, entry_point, target_functions, venv_python=venv_python)
            _safe_log_event(
                run_log,
                "repo_capture_summary",
                target_count=len(target_functions),
                captured_count=len(io_data),
            )

            # Run DAG-based optimization
            phase = "optimize"
            _safe_log_event(run_log, "repo_phase", phase=phase, state="start", target_count=len(dag.nodes))
            from src.core.optimization_dag import optimize_dag
            dag_config = {
                "llm_model": job.get("llm_model"),
                "analysis_mode": job.get("analysis_mode", "llm"),
                "max_attempts": 3,
                "max_parallel_candidates": min(len(dag.nodes), 4),
            }
            dag_result = optimize_dag(
                repo_path=clone_path,
                dag=dag,
                io_data=io_data,
                config=dag_config,
                entry_point=entry_point,
            )
            _safe_log_event(
                run_log,
                "repo_optimize_summary",
                total_functions=dag_result.total_functions,
                successful=dag_result.successful_optimizations,
                failed=dag_result.failed_optimizations,
                skipped=dag_result.skipped_functions,
                overall_speedup=dag_result.overall_speedup,
            )

            if dag_result.successful_optimizations == 0:
                raise RuntimeError(
                    f"No optimizations succeeded out of {dag_result.total_functions} hot functions"
                )

            # Validate: re-run bootstrap commands to ensure nothing broke
            phase = "validate"
            validation_commands = list(bootstrap.get("setup_commands", []))
            if bootstrap.get("test_command", "") != "":
                validation_commands.append(str(bootstrap["test_command"]))
            _safe_log_event(
                run_log,
                "repo_phase",
                phase=phase,
                state="start",
                command_count=len(validation_commands),
            )
            validation_result = run_repo_commands(
                clone_path,
                validation_commands,
                config=job["backend_config"],
            )
            _safe_log_event(
                run_log,
                "repo_validation_summary",
                success=bool(validation_result.get("success", False)),
                command_count=len(validation_commands),
            )

            function_summaries = _dag_function_summaries(dag_result)
            optimization_summary = {
                "total_functions": dag_result.total_functions,
                "successful": dag_result.successful_optimizations,
                "failed": dag_result.failed_optimizations,
                "skipped": dag_result.skipped_functions,
                "baseline_total_time": dag_result.baseline_total_time,
                "optimized_total_time": dag_result.optimized_total_time,
                "overall_speedup": dag_result.overall_speedup,
            }
            pr_title = _build_dag_pr_title(job["prompt"], dag_result)
            pr_body = _build_dag_pr_body(job, dag_result, analysis, validation_result, auth_context)
        else:
            pr_title = _build_smoke_test_pr_title(job["prompt"])
            pr_body = _build_smoke_test_pr_body(
                job=job,
                analysis=analysis,
                entry_point=entry_point,
                auth_context=auth_context,
                artifact_path=smoke_test_artifact,
            )

        branch_name = job.get("branch_name") or make_branch_name("ringtail")

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
            if not working_tree_has_changes(clone_path):
                phase = "smoke_test_change"
                smoke_test_artifact = _write_pr_smoke_test_artifact(
                    clone_path=clone_path,
                    job=job,
                    analysis=analysis,
                    entry_point=entry_point,
                    auth_context=auth_context,
                    reason="Optimization completed without a repository diff; emitting a commit so PR publishing can be verified.",
                )
                validation_result["smoke_test_artifact"] = smoke_test_artifact
                _safe_log_event(
                    run_log,
                    "repo_smoke_test_change",
                    artifact_path=smoke_test_artifact,
                    reason="empty_working_tree",
                )
            phase = "git"
            _safe_log_event(
                run_log,
                "repo_git_prepare",
                head_branch=branch_name,
                base_branch=job["base_branch"],
            )
            create_branch(clone_path, branch_name)
            commit_sha = commit_all(clone_path, pr_title)
            _safe_log_event(
                run_log,
                "repo_git_commit",
                head_branch=branch_name,
                commit_sha=commit_sha,
            )
            _safe_log_event(
                run_log,
                "repo_git_push",
                head_branch=branch_name,
                auth_mode=auth_context.get("mode", "none"),
                installation_id=auth_context.get("installation_id", None),
            )
            push_branch(clone_path, job["repo_url"], branch_name, token)
            phase = "pull_request"
            _safe_log_event(
                run_log,
                "repo_pull_request_create",
                head_branch=branch_name,
                base_branch=job["base_branch"],
                auth_mode=auth_context.get("mode", "none"),
                installation_id=auth_context.get("installation_id", None),
            )
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
            _safe_log_event(
                run_log,
                "repo_pull_request_created",
                number=pull_request["number"],
                url=pull_request["url"],
            )
        else:
            pull_request["preview_only"] = True
            _safe_log_event(
                run_log,
                "repo_pull_request_preview",
                head_branch=branch_name,
                base_branch=job["base_branch"],
            )

        _safe_log_event(
            run_log,
            "repo_job_complete",
            published=bool(pull_request.get("published", False)),
            preview_only=bool(pull_request.get("preview_only", False)),
            branch_name=branch_name,
            commit_sha=commit_sha,
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
            "strategy": "dag_profile_driven",
            "entry_point": entry_point,
            "repo_access": repo_access,
            "bootstrap": bootstrap,
            "profiling": {
                "total_time": analysis.total_time,
                "functions_analyzed": len(analysis.functions),
                "hot_functions": len(hot_functions),
                "dag_levels": profiling_dag_levels,
            },
            "optimization": optimization_summary,
            "function_summaries": function_summaries,
            "validation_result": validation_result,
            "branch_name": branch_name,
            "commit_sha": commit_sha,
            "pull_request": pull_request,
            "message": smoke_test_only and "No significant bottlenecks detected; opened a PR with a smoke-test artifact." or "",
            "run_id": getattr(run_log, "run_id", ""),
            "run_log_path": getattr(run_log, "log_path", ""),
        }
    except Exception as exc:
        _safe_log_error(
            run_log,
            f"[{phase}] {exc}",
            phase=phase,
            repo_url=job["repo_url"],
            base_branch=job["base_branch"],
            head_branch=branch_name,
            publish_pr=bool(job.get("publish_pr", False)),
        )
        raise RuntimeError(f"[{phase}] {exc}") from exc
    finally:
        _close_run_log(run_log)
        if not request.get("keep_repo_checkout", False):
            shutil.rmtree(temp_root, ignore_errors=True)


def _maybe_create_repo_run_log(request: dict[str, Any]) -> RunLog | None:
    enabled = request.get("enable_run_log", DEFAULT_ENABLE_RUN_LOG)
    if enabled is None or not bool(enabled):
        return None

    run_name = str(request.get("run_name", "")).strip() or "repo-agent"
    run_id = str(request.get("run_id", "")).strip()
    try:
        if run_id:
            return RunLog(run_name, run_id=run_id)
        return RunLog(run_name)
    except Exception:
        return None


def _safe_log_event(run_log: RunLog | None, kind: str, **data: Any) -> None:
    if run_log is None:
        return
    try:
        run_log.event(kind, **data)
    except Exception:
        return


def _safe_log_error(run_log: RunLog | None, message: str, **extra: Any) -> None:
    if run_log is None:
        return
    try:
        run_log.error(message, **extra)
    except Exception:
        return


def _close_run_log(run_log: RunLog | None) -> None:
    if run_log is None:
        return
    try:
        run_log.close()
    except Exception:
        return


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
            "enable_run_log": DEFAULT_ENABLE_RUN_LOG,
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
            "enable_run_log": DEFAULT_ENABLE_RUN_LOG,
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
            "enable_run_log": DEFAULT_ENABLE_RUN_LOG,
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
        "enable_run_log": DEFAULT_ENABLE_RUN_LOG,
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


def _build_dag_pr_title(prompt: str, dag_result: Any) -> str:
    count = dag_result.successful_optimizations
    speedup = dag_result.overall_speedup
    speedup_str = f" ({speedup:.1f}x faster)" if speedup and speedup > 1.0 else ""
    return f"Optimize {count} function{'s' if count != 1 else ''}{speedup_str}"


def _build_dag_pr_body(
    job: dict[str, Any],
    dag_result: Any,
    analysis: Any,
    validation_result: dict[str, Any],
    auth_context: dict[str, Any],
) -> str:
    lines = [
        "## Ringtail Performance Optimization",
        "",
        f"**Prompt:** {job['prompt']}",
        f"**Entry point:** `{job.get('entry_point', '')}`",
        "",
        "### Profiling Results",
        "",
        f"- Total program time: {analysis.total_time:.3f}s",
        "",
        "### Optimization Results",
        "",
        f"- Successfully optimized: {dag_result.successful_optimizations}",
        f"- Failed to optimize: {dag_result.failed_optimizations}",
    ]

    if dag_result.baseline_total_time and dag_result.optimized_total_time:
        lines.extend([
            "",
            f"- Baseline time across optimized functions: {dag_result.baseline_total_time:.3f}s",
            f"- Post-change time across optimized functions: {dag_result.optimized_total_time:.3f}s",
        ])
        if dag_result.overall_speedup:
            lines.append(f"- Net speedup across optimized functions: **{dag_result.overall_speedup:.2f}x**")

    rows = [fr for fr in dag_result.function_results.values() if not getattr(fr, "skipped", False)]
    rows.sort(key=lambda fr: (not fr.success, os.path.basename(fr.file_path), fr.function_name))
    lines.extend([
        "",
        "### Per-Function Results",
        "",
    ])
    if rows:
        lines.extend([
            "| Function | File | Baseline (s) | Optimized (s) | Speedup | Attempts | Status |",
            "|----------|------|-------------|---------------|---------|----------|--------|",
        ])
        for fr in rows:
            status = "optimized" if fr.success else _truncate_status(fr.error or "failed")
            optimized_time = _format_optional_seconds(fr.optimized_tottime) if fr.success else ""
            speedup = _format_optional_speedup(fr.speedup) if fr.success else ""
            lines.append(
                f"| `{fr.function_name}` | `{os.path.basename(fr.file_path)}` | "
                f"{fr.baseline_tottime:.4f} | {optimized_time} | "
                f"{speedup} | {len(fr.attempts)} | {status} |"
            )
    else:
        lines.append("No extractable function definitions were attempted.")

    validated = validation_result.get("success", False)
    lines.extend([
        "",
        "### Validation",
        "",
        f"- Repo validation: {'passed' if validated else 'failed'}",
        f"- Auth mode: {auth_context.get('mode', 'none')}",
    ])

    return "\n".join(lines)


def _build_smoke_test_pr_title(prompt: str) -> str:
    if str(prompt).strip() != "":
        return "Validate PR publishing path"
    return "Validate Ringtail PR publishing path"


def _build_smoke_test_pr_body(
    *,
    job: dict[str, Any],
    analysis: Any,
    entry_point: str,
    auth_context: dict[str, Any],
    artifact_path: str,
) -> str:
    lines = [
        "## Ringtail PR Publishing Validation",
        "",
        f"**Prompt:** {job['prompt']}",
        f"**Entry point:** `{entry_point}`",
        f"**Auth mode:** {auth_context.get('mode', 'none')}",
        "",
        "No performance diff was produced for this run, so Ringtail wrote a smoke-test artifact to verify branch push and pull request creation.",
        "",
        "### Profiling Summary",
        "",
        f"- Total program time: {analysis.total_time:.3f}s",
    ]
    if artifact_path != "":
        lines.extend([
            "",
            "### Artifact",
            "",
            f"- Committed file: `{artifact_path}`",
        ])
    return "\n".join(lines)


def _write_pr_smoke_test_artifact(
    *,
    clone_path: str,
    job: dict[str, Any],
    analysis: Any,
    entry_point: str,
    auth_context: dict[str, Any],
    reason: str,
) -> str:
    rel_path = "ringtail_pr_smoke_test.md"
    target = Path(clone_path) / rel_path
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = "\n".join(
        [
            "# Ringtail PR Smoke Test",
            "",
            f"Generated at: {timestamp}",
            f"Repository: {job['repo_url']}",
            f"Prompt: {job['prompt']}",
            f"Entry point: {entry_point}",
            f"Auth mode: {auth_context.get('mode', 'none')}",
            "",
            reason,
            "",
            "Profiling summary:",
            f"- total_time_s: {analysis.total_time:.6f}",
            f"- functions_analyzed: {len(analysis.functions)}",
            "",
            "This file exists to verify Ringtail can commit, push, and open a pull request even when optimization produces no code diff.",
            "",
        ]
    )
    target.write_text(body, encoding="utf-8")
    return rel_path


def _dag_function_summaries(dag_result: Any) -> list[dict[str, Any]]:
    summaries = []
    for key, fr in dag_result.function_results.items():
        summaries.append({
            "func_key": key,
            "function_name": fr.function_name,
            "file_path": fr.file_path,
            "success": fr.success,
            "skipped": getattr(fr, "skipped", False),
            "skip_reason": getattr(fr, "skip_reason", ""),
            "attempts": len(fr.attempts),
            "baseline_tottime": fr.baseline_tottime,
            "optimized_tottime": fr.optimized_tottime,
            "speedup": fr.speedup,
            "error": fr.error,
        })
    return summaries


def _format_optional_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _format_optional_speedup(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}x"


def _truncate_status(text: str, limit: int = 48) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."
