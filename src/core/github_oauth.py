"""
GitHub OAuth helpers for browser-based "Sign in with GitHub".

Uses the GitHub App's client_id / client_secret for the authorization code
exchange flow.  Reads credentials from RINGTAIL_REPO_AGENT_CONFIG (which
already stores app_id, client_id, etc.) plus a new client_secret field, or
from dedicated RINGTAIL_GITHUB_APP_CLIENT_SECRET / GITHUB_APP_CLIENT_SECRET
env vars.
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.core.github_repo_service import resolve_github_app_config


_CLIENT_SECRET_ENV_NAMES = (
    "RINGTAIL_GITHUB_APP_CLIENT_SECRET",
    "GITHUB_APP_CLIENT_SECRET",
)

_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
_API_USER_URL = "https://api.github.com/user"

# In-memory nonce store; maps state → True.  Good enough for a single-process
# server.  Replace with Redis / DB for multi-process deployments.
_pending_states: dict[str, bool] = {}


def _resolve_client_secret() -> str:
    raw = os.environ.get("RINGTAIL_REPO_AGENT_CONFIG", "").strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            secret = data.get("client_secret", "")
            if secret:
                return str(secret)
        except json.JSONDecodeError:
            pass
    for name in _CLIENT_SECRET_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_oauth_config() -> dict[str, Any]:
    app_cfg = resolve_github_app_config()
    client_id = app_cfg.get("client_id", "")
    client_secret = _resolve_client_secret()
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "configured": bool(client_id and client_secret),
        "missing": [
            *([] if client_id else ["client_id"]),
            *([] if client_secret else ["client_secret"]),
        ],
    }


def get_login_url(redirect_uri: str = "") -> dict[str, Any]:
    cfg = get_oauth_config()
    if not cfg["configured"]:
        return {"error": "OAuth not configured", "missing": cfg["missing"], "url": ""}
    state = secrets.token_urlsafe(32)
    _pending_states[state] = True
    params = {
        "client_id": cfg["client_id"],
        "state": state,
    }
    if redirect_uri:
        params["redirect_uri"] = redirect_uri
    url = _OAUTH_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
    return {"url": url, "state": state}


def exchange_code(code: str, state: str) -> dict[str, Any]:
    if state not in _pending_states:
        return {"error": "Invalid or expired state parameter"}
    del _pending_states[state]

    cfg = get_oauth_config()
    if not cfg["configured"]:
        return {"error": "OAuth not configured", "missing": cfg["missing"]}

    token_data = _post_form(
        _OAUTH_TOKEN_URL,
        {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
        },
    )
    access_token = token_data.get("access_token", "")
    if not access_token:
        return {
            "error": token_data.get("error_description", token_data.get("error", "Token exchange failed")),
        }

    user = _github_api_get(_API_USER_URL, access_token)
    return {
        "access_token": access_token,
        "github_user": user,
    }


def _post_form(url: str, params: dict[str, str]) -> dict[str, Any]:
    data = urllib.parse.urlencode(params).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "User-Agent": "ringtail-oauth",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OAuth token exchange failed: {exc.code} {detail}") from exc


def _github_api_get(url: str, token: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ringtail-oauth",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {exc.code} {detail}") from exc
