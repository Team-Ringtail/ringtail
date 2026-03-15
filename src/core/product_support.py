"""
Shared product-facing helpers for CLI and local web UX.
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Any

from src.core import async_jobs
from src.core.github_repo_service import get_github_app_install_info, resolve_github_auth


def get_auth_readiness() -> dict[str, Any]:
    install_info = get_github_app_install_info(None, None)
    auth_context = resolve_github_auth(None, None)
    has_repo_config = bool(os.environ.get("RINGTAIL_REPO_AGENT_CONFIG", "").strip())
    has_blaxel = bool(
        os.environ.get("BLAXEL_API_KEY", "")
        or os.environ.get("blaxel_api_key", "")
        or os.environ.get("BL_API_KEY", "")
    )
    return {
        "repo_agent_config_present": has_repo_config,
        "auth_mode": auth_context.get("mode", "none"),
        "installation_id": auth_context.get("installation_id", None),
        "expires_at": auth_context.get("expires_at", None),
        "github_app": install_info,
        "blaxel_configured": has_blaxel,
    }


def config_doctor() -> dict[str, Any]:
    readiness = get_auth_readiness()
    checks = {
        "python": _binary_check(sys.executable),
        "jac": _binary_check("jac"),
        "git": _binary_check("git"),
        "openssl": _binary_check("openssl"),
        "uv": _binary_check("uv"),
    }
    env = {
        "anthropic_configured": bool(os.environ.get("RINGTAIL_ANTHROPIC_API_KEY", "").strip()),
        "repo_agent_config_present": readiness["repo_agent_config_present"],
        "blaxel_configured": readiness["blaxel_configured"],
        "default_model_override_present": bool(os.environ.get("RINGTAIL_DEFAULT_LLM_MODEL", "").strip()),
    }
    issues = []
    if not checks["jac"]["available"]:
        issues.append("jac CLI not found")
    if not checks["git"]["available"]:
        issues.append("git not found")
    if not checks["openssl"]["available"]:
        issues.append("openssl not found")
    if not env["repo_agent_config_present"]:
        issues.append("RINGTAIL_REPO_AGENT_CONFIG is not set")
    return {
        "ok": len(issues) == 0,
        "checks": checks,
        "env": env,
        "auth": readiness,
        "jobs_dir": async_jobs.get_jobs_dir(),
        "issues": issues,
    }


def list_recent_jobs(limit: int = 10) -> list[dict[str, Any]]:
    jobs = async_jobs.list_jobs(limit)
    summarized = []
    for job in jobs:
        summarized.append(
            {
                "job_id": job.get("job_id", ""),
                "status": job.get("status", ""),
                "submitted_at": job.get("submitted_at", ""),
                "finished_at": job.get("finished_at", None),
                "run_id": job.get("run_id", ""),
                "run_log_path": job.get("run_log_path", ""),
                "request_summary": job.get("request_summary", {}),
                "error": job.get("error", ""),
            }
        )
    return summarized


def _binary_check(name: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    return {
        "available": resolved is not None,
        "path": resolved or "",
    }
