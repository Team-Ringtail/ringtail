"""
Simple JSON-file session and installation store.

Sessions and installation links are persisted under logs/sessions/ so they
survive process restarts. For production, swap to a real database.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from src.utils.run_log import LOGS_DIR

_SESSIONS_DIR = Path(os.environ.get("RINGTAIL_SESSIONS_DIR", Path(LOGS_DIR) / "sessions"))
_INSTALLATIONS_DIR = _SESSIONS_DIR / "installations"


def _ensure_dirs() -> None:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _INSTALLATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(token: str) -> Path:
    digest = hashlib.sha256(token.encode()).hexdigest()
    return _SESSIONS_DIR / f"{digest}.json"


def _installation_path(github_user_id: int) -> Path:
    return _INSTALLATIONS_DIR / f"{github_user_id}.json"


def create_session(github_user: dict[str, Any]) -> dict[str, Any]:
    _ensure_dirs()
    token = secrets.token_urlsafe(48)
    session = {
        "session_token": token,
        "github_user_id": int(github_user["id"]),
        "github_login": str(github_user.get("login", "")),
        "github_avatar_url": str(github_user.get("avatar_url", "")),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _session_path(token).write_text(json.dumps(session), encoding="utf-8")
    return session


def validate_session(token: str) -> dict[str, Any] | None:
    path = _session_path(token)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def delete_session(token: str) -> bool:
    path = _session_path(token)
    if path.exists():
        path.unlink()
        return True
    return False


def save_installation(github_user_id: int, installation_id: int, account_login: str = "") -> dict[str, Any]:
    _ensure_dirs()
    record = {
        "github_user_id": int(github_user_id),
        "installation_id": int(installation_id),
        "account_login": account_login,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _installation_path(github_user_id).write_text(json.dumps(record), encoding="utf-8")
    return record


def get_installation(github_user_id: int) -> dict[str, Any] | None:
    path = _installation_path(github_user_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_installation_for_session(token: str) -> dict[str, Any] | None:
    session = validate_session(token)
    if session is None:
        return None
    return get_installation(int(session["github_user_id"]))
