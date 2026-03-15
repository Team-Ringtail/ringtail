"""
GitHub/repository automation helpers for repo-agent workflows.

The first milestone uses environment-injected credentials and the GitHub REST
API directly so the orchestration layer stays independent from the eventual
GitHub App installation flow.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_GITHUB_API_BASE = "https://api.github.com"
_REPO_AGENT_CONFIG_ENV = "RINGTAIL_REPO_AGENT_CONFIG"
_TOKEN_ENV_NAMES = (
    "RINGTAIL_GITHUB_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)
_APP_ID_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_ID",
    "GITHUB_APP_ID",
)
_APP_SLUG_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_SLUG",
    "GITHUB_APP_SLUG",
)
_APP_CLIENT_ID_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_CLIENT_ID",
    "GITHUB_APP_CLIENT_ID",
)
_APP_PRIVATE_KEY_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_PRIVATE_KEY",
    "GITHUB_APP_PRIVATE_KEY",
)
_APP_PRIVATE_KEY_PATH_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_PRIVATE_KEY_PATH",
    "GITHUB_APP_PRIVATE_KEY_PATH",
)


def resolve_github_token(explicit_token: str | None = None, auth: dict[str, Any] | None = None) -> str:
    context = resolve_github_auth(auth=auth, explicit_token=explicit_token)
    return str(context.get("token", ""))


def resolve_github_auth(
    auth: dict[str, Any] | None = None,
    explicit_token: str | None = None,
) -> dict[str, Any]:
    auth_data = _merged_repo_agent_auth(auth)
    token = explicit_token or str(auth_data.get("token", "")).strip()
    if token:
        return {
            "mode": "token",
            "token": token,
            "installation_id": None,
            "expires_at": None,
        }
    for name in _TOKEN_ENV_NAMES:
        value = os.environ.get(name, "")
        if value:
            return {
                "mode": "token",
                "token": value,
                "installation_id": None,
                "expires_at": None,
            }

    installation_id = auth_data.get("installation_id", auth_data.get("github_installation_id", None))
    if installation_id is not None and str(installation_id) != "":
        token_payload = create_installation_access_token(int(installation_id), auth=auth_data)
        return {
            "mode": "github_app_installation",
            "token": str(token_payload.get("token", "")),
            "installation_id": int(installation_id),
            "expires_at": token_payload.get("expires_at", None),
            "permissions": token_payload.get("permissions", {}),
        }

    return {
        "mode": "none",
        "token": "",
        "installation_id": None,
        "expires_at": None,
    }


def resolve_github_app_config(auth: dict[str, Any] | None = None) -> dict[str, Any]:
    auth_data = _merged_repo_agent_auth(auth)
    app_id = str(auth_data.get("app_id", _first_env(_APP_ID_ENV_NAMES))).strip()
    app_slug = str(auth_data.get("app_slug", _first_env(_APP_SLUG_ENV_NAMES))).strip()
    client_id = str(auth_data.get("client_id", _first_env(_APP_CLIENT_ID_ENV_NAMES))).strip()
    private_key = str(auth_data.get("private_key", _first_env(_APP_PRIVATE_KEY_ENV_NAMES))).strip()
    private_key_path = str(auth_data.get("private_key_path", _first_env(_APP_PRIVATE_KEY_PATH_ENV_NAMES))).strip()

    pem = ""
    if private_key:
        pem = private_key.replace("\\n", "\n")
    elif private_key_path:
        pem = Path(private_key_path).read_text()

    missing: list[str] = []
    if app_id == "":
        missing.append("app_id")
    if pem.strip() == "":
        missing.append("private_key")

    return {
        "app_id": app_id,
        "app_slug": app_slug,
        "client_id": client_id,
        "private_key": pem,
        "configured": len(missing) == 0,
        "missing": missing,
    }


def get_github_app_install_info(state: str | None = None, auth: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = resolve_github_app_config(auth)
    install_url = ""
    if cfg.get("app_slug", "") != "":
        install_url = f"https://github.com/apps/{cfg['app_slug']}/installations/new"
        if state:
            install_url = install_url + "?state=" + urllib.parse.quote(str(state))
    return {
        "configured": bool(cfg.get("configured", False)),
        "app_id": cfg.get("app_id", ""),
        "app_slug": cfg.get("app_slug", ""),
        "client_id": cfg.get("client_id", ""),
        "install_url": install_url,
        "missing": cfg.get("missing", []),
        "state": state or "",
    }


def handle_github_app_install_callback(
    installation_id: int,
    setup_action: str | None = None,
    state: str | None = None,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    access = list_installation_repositories(installation_id, auth=auth)
    return {
        "success": True,
        "installation_id": int(installation_id),
        "setup_action": setup_action or "",
        "state": state or "",
        "repository_count": access.get("total_count", 0),
        "repositories": access.get("repositories", []),
        "auth_mode": "github_app_installation",
        "expires_at": access.get("expires_at", None),
    }


def verify_repo_access(
    repo_url: str,
    auth: dict[str, Any] | None = None,
    explicit_token: str | None = None,
) -> dict[str, Any]:
    if is_local_repo_url(repo_url):
        path = repo_url[7:] if repo_url.startswith("file://") else repo_url
        return {
            "success": Path(path).exists(),
            "auth_mode": "local",
            "repo_url": repo_url,
            "permissions": {},
        }

    owner, repo = parse_repo_slug(repo_url)
    auth_context = resolve_github_auth(auth=auth, explicit_token=explicit_token)
    token = str(auth_context.get("token", ""))
    if token == "":
        return {
            "success": False,
            "auth_mode": "none",
            "repo_url": repo_url,
            "error": "No GitHub token or installation auth available",
        }

    repo_data = _github_api_request(f"/repos/{owner}/{repo}", token=token)
    permissions = repo_data.get("permissions", {})
    return {
        "success": True,
        "auth_mode": auth_context.get("mode", "token"),
        "repo_url": repo_url,
        "installation_id": auth_context.get("installation_id", None),
        "expires_at": auth_context.get("expires_at", None),
        "default_branch": repo_data.get("default_branch", ""),
        "private": bool(repo_data.get("private", False)),
        "permissions": permissions,
        "clone_url": repo_data.get("clone_url", ""),
    }


def is_local_repo_url(repo_url: str) -> bool:
    if repo_url.startswith("file://"):
        return True
    if repo_url.startswith("http://") or repo_url.startswith("https://") or repo_url.startswith("git@"):
        return False
    return Path(repo_url).exists()


def parse_repo_slug(repo_url: str) -> tuple[str, str]:
    cleaned = repo_url.strip()
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+)$", cleaned)
    if not match:
        raise ValueError(f"Could not parse GitHub owner/repo from URL: {repo_url}")
    return match.group("owner"), match.group("repo")


def clone_repo(repo_url: str, destination_dir: str, base_branch: str | None = None, token: str | None = None) -> str:
    dest = Path(destination_dir)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if is_local_repo_url(repo_url):
        source = Path(repo_url[7:] if repo_url.startswith("file://") else repo_url).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Local repository path does not exist: {repo_url}")
        shutil.copytree(
            source,
            dest,
            ignore=shutil.ignore_patterns(
                ".venv",
                "node_modules",
                ".pytest_cache",
                "__pycache__",
                ".mypy_cache",
                ".ruff_cache",
                ".jac",
            ),
        )
        return str(dest)

    command = ["git", "clone"]
    if base_branch:
        command.extend(["--branch", base_branch])
    command.extend(["--depth", "1", build_authenticated_clone_url(repo_url, token), str(dest)])
    _run_git(command)
    return str(dest)


def build_authenticated_clone_url(repo_url: str, token: str | None = None) -> str:
    if is_local_repo_url(repo_url):
        if repo_url.startswith("file://"):
            return repo_url
        return str(Path(repo_url).resolve())
    if not token:
        return repo_url

    owner, repo = parse_repo_slug(repo_url)
    return f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"


def create_branch(repo_path: str, branch_name: str) -> None:
    _run_git(["git", "checkout", "-B", branch_name], cwd=repo_path)


def working_tree_has_changes(repo_path: str) -> bool:
    result = _run_git(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True)
    return bool(result.stdout.strip())


def commit_all(repo_path: str, message: str) -> str:
    _run_git(["git", "add", "."], cwd=repo_path)
    if not working_tree_has_changes(repo_path):
        raise ValueError("No repository changes to commit")

    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "Ringtail")
    env.setdefault("GIT_AUTHOR_EMAIL", "ringtail@local")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    _run_git(["git", "commit", "-m", message], cwd=repo_path, env=env)
    sha = _run_git(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True).stdout.strip()
    return sha


def push_branch(repo_path: str, repo_url: str, branch_name: str, token: str) -> None:
    if not token:
        raise EnvironmentError("GitHub token is required to push a branch")
    remote_url = build_authenticated_clone_url(repo_url, token)
    _run_git(["git", "push", remote_url, f"HEAD:refs/heads/{branch_name}"], cwd=repo_path)


def build_pr_body(
    *,
    prompt: str,
    target_summary: str,
    test_summary: str,
    performance_summary: str,
    notes: list[str] | None = None,
) -> str:
    lines = [
        "## Summary",
        f"- Prompt: {prompt}",
        f"- Selected target: {target_summary}",
        f"- Validation: {test_summary}",
        f"- Performance: {performance_summary}",
        "",
        "## Notes",
        "- Generated by Ringtail repo agent.",
    ]
    for note in notes or []:
        lines.append(f"- {note}")
    return "\n".join(lines)


def create_pull_request(
    *,
    repo_url: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    token: str,
) -> dict[str, Any]:
    if not token:
        raise EnvironmentError("GitHub token is required to create a pull request")

    owner, repo = parse_repo_slug(repo_url)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    payload = json.dumps(
        {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
        }
    ).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ringtail-repo-agent",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub PR creation failed: {exc.code} {detail}") from exc


def make_branch_name(prefix: str = "ringtail") -> str:
    return f"{prefix}/optimize-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}"


def build_github_app_jwt(auth: dict[str, Any] | None = None, now_ts: int | None = None) -> str:
    cfg = resolve_github_app_config(auth)
    if not bool(cfg.get("configured", False)):
        raise EnvironmentError(
            "GitHub App auth is not configured: missing " + ", ".join(cfg.get("missing", []))
        )

    issued_at = int(now_ts or time.time())
    header = _b64url_json({"alg": "RS256", "typ": "JWT"})
    payload = _b64url_json(
        {
            "iat": issued_at - 60,
            "exp": issued_at + 540,
            "iss": cfg["app_id"],
        }
    )
    signing_input = f"{header}.{payload}"
    signature = _sign_rs256(signing_input.encode("utf-8"), str(cfg["private_key"]))
    return signing_input + "." + _b64url(signature)


def create_installation_access_token(
    installation_id: int,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    jwt_token = build_github_app_jwt(auth=auth)
    return _github_api_request(
        f"/app/installations/{int(installation_id)}/access_tokens",
        method="POST",
        token=jwt_token,
        json_body={},
    )


def list_installation_repositories(
    installation_id: int,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    auth_context = resolve_github_auth(auth={"installation_id": int(installation_id), **(auth or {})})
    payload = _github_api_request("/installation/repositories", token=str(auth_context.get("token", "")))
    repositories = []
    for repo in payload.get("repositories", []):
        repositories.append(
            {
                "full_name": repo.get("full_name", ""),
                "private": bool(repo.get("private", False)),
                "default_branch": repo.get("default_branch", ""),
                "permissions": repo.get("permissions", {}),
            }
        )
    return {
        "total_count": int(payload.get("total_count", len(repositories))),
        "repositories": repositories,
        "expires_at": auth_context.get("expires_at", None),
        "installation_id": int(installation_id),
    }


def _run_git(
    command: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git command failed: "
            + " ".join(command)
            + "\n"
            + (result.stderr or result.stdout or "").strip()
        )
    if capture_output:
        return result
    return result


def _first_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value
    return ""


def _merged_repo_agent_auth(auth: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = _load_repo_agent_env_config()
    if auth:
        merged.update(auth)
    return merged


def _load_repo_agent_env_config() -> dict[str, Any]:
    raw = os.environ.get(_REPO_AGENT_CONFIG_ENV, "").strip()
    if raw == "":
        return {}

    payload = raw
    if not raw.startswith("{"):
        path = Path(raw)
        if not path.exists():
            raise EnvironmentError(
                f"{_REPO_AGENT_CONFIG_ENV} must be JSON or a path to an existing JSON file"
            )
        payload = path.read_text()

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise EnvironmentError(f"{_REPO_AGENT_CONFIG_ENV} is not valid JSON") from exc

    if not isinstance(data, dict):
        raise EnvironmentError(f"{_REPO_AGENT_CONFIG_ENV} must decode to a JSON object")

    auth = dict(data.get("auth", {})) if isinstance(data.get("auth"), dict) else {}
    for key in (
        "token",
        "installation_id",
        "github_installation_id",
        "app_id",
        "app_slug",
        "client_id",
        "private_key",
        "private_key_path",
    ):
        if key in data and key not in auth:
            auth[key] = data[key]
    return auth


def _b64url_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url(raw)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign_rs256(message: bytes, private_key_pem: str) -> bytes:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as handle:
        handle.write(private_key_pem)
        key_path = handle.name
    try:
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            input=message,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError("openssl signing failed: " + proc.stderr.decode("utf-8", errors="replace").strip())
        return proc.stdout
    finally:
        os.remove(key_path)


def _github_api_request(
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ringtail-repo-agent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(_GITHUB_API_BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {detail}") from exc
