"""
Offline tests for OAuth helpers and session store.

    python -m pytest tests/unit/test_github_oauth_and_sessions.py -v
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core import github_oauth as oauth
from src.core import session_store as store


@pytest.fixture(autouse=True)
def isolate_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store, "_SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(store, "_INSTALLATIONS_DIR", tmp_path / "sessions" / "installations")


@pytest.fixture
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RINGTAIL_REPO_AGENT_CONFIG", raising=False)
    for name in oauth._CLIENT_SECRET_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


# ── session_store ──────────────────────────────────────────────────

class TestSessionStore:
    def test_create_and_validate_session(self) -> None:
        session = store.create_session({"id": 42, "login": "octocat", "avatar_url": "https://img"})
        assert session["github_user_id"] == 42
        assert session["github_login"] == "octocat"

        restored = store.validate_session(session["session_token"])
        assert restored is not None
        assert restored["github_login"] == "octocat"

    def test_validate_unknown_token_returns_none(self) -> None:
        assert store.validate_session("bogus-token") is None

    def test_delete_session(self) -> None:
        session = store.create_session({"id": 1, "login": "x"})
        assert store.delete_session(session["session_token"]) is True
        assert store.validate_session(session["session_token"]) is None
        assert store.delete_session(session["session_token"]) is False

    def test_save_and_get_installation(self) -> None:
        store._ensure_dirs()
        rec = store.save_installation(42, 9999, "acme-org")
        assert rec["installation_id"] == 9999
        fetched = store.get_installation(42)
        assert fetched is not None
        assert fetched["installation_id"] == 9999
        assert fetched["account_login"] == "acme-org"

    def test_get_installation_missing(self) -> None:
        assert store.get_installation(999999) is None

    def test_get_installation_for_session(self) -> None:
        session = store.create_session({"id": 7, "login": "u"})
        assert store.get_installation_for_session(session["session_token"]) is None
        store.save_installation(7, 1234, "team")
        inst = store.get_installation_for_session(session["session_token"])
        assert inst is not None
        assert inst["installation_id"] == 1234

    def test_get_installation_for_bad_session(self) -> None:
        assert store.get_installation_for_session("nope") is None


# ── github_oauth ───────────────────────────────────────────────────

class TestGithubOAuth:
    def test_get_oauth_config_missing(self, clear_env: None) -> None:
        cfg = oauth.get_oauth_config()
        assert cfg["configured"] is False
        assert "client_id" in cfg["missing"] or "client_secret" in cfg["missing"]

    def test_get_oauth_config_from_env(self, clear_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_ID", "cid")
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_SECRET", "csec")
        cfg = oauth.get_oauth_config()
        assert cfg["configured"] is True
        assert cfg["client_id"] == "cid"
        assert cfg["client_secret"] == "csec"

    def test_get_oauth_config_from_repo_agent_config(self, clear_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RINGTAIL_REPO_AGENT_CONFIG", json.dumps({
            "client_id": "rc-id",
            "client_secret": "rc-secret",
            "app_id": "1",
            "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
        }))
        cfg = oauth.get_oauth_config()
        assert cfg["configured"] is True
        assert cfg["client_secret"] == "rc-secret"

    def test_get_login_url_not_configured(self, clear_env: None) -> None:
        result = oauth.get_login_url("")
        assert result["url"] == ""
        assert "error" in result

    def test_get_login_url_returns_github_authorize(self, clear_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_ID", "my-cid")
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_SECRET", "s")
        result = oauth.get_login_url("http://localhost:8000/callback")
        assert result["url"].startswith("https://github.com/login/oauth/authorize")
        assert "client_id=my-cid" in result["url"]
        assert "state=" in result["url"]
        assert result["state"] != ""

    def test_exchange_code_bad_state(self, clear_env: None) -> None:
        result = oauth.exchange_code("code", "bad-state")
        assert "error" in result

    def test_exchange_code_happy_path(self, clear_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_ID", "cid")
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_SECRET", "csec")

        login_result = oauth.get_login_url("")
        state = login_result["state"]

        class FakeResp:
            def read(self) -> bytes:
                return b""
            def __enter__(self) -> FakeResp:
                return self
            def __exit__(self, *a: object) -> bool:
                return False

        call_count = [0]

        def fake_urlopen(req: object, timeout: int = 15) -> FakeResp:
            call_count[0] += 1
            resp = FakeResp()
            if call_count[0] == 1:
                resp.read = lambda: json.dumps({"access_token": "ghu_abc123"}).encode()
            else:
                resp.read = lambda: json.dumps({"id": 42, "login": "octocat", "avatar_url": ""}).encode()
            return resp

        monkeypatch.setattr(oauth.urllib.request, "urlopen", fake_urlopen)

        result = oauth.exchange_code("the-code", state)
        assert "error" not in result
        assert result["access_token"] == "ghu_abc123"
        assert result["github_user"]["login"] == "octocat"

    def test_exchange_code_token_error(self, clear_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_ID", "cid")
        monkeypatch.setenv("RINGTAIL_GITHUB_APP_CLIENT_SECRET", "csec")

        login_result = oauth.get_login_url("")
        state = login_result["state"]

        class FakeResp:
            def read(self) -> bytes:
                return json.dumps({"error": "bad_verification_code", "error_description": "nope"}).encode()
            def __enter__(self) -> FakeResp:
                return self
            def __exit__(self, *a: object) -> bool:
                return False

        monkeypatch.setattr(oauth.urllib.request, "urlopen", lambda req, timeout=15: FakeResp())

        result = oauth.exchange_code("bad-code", state)
        assert "error" in result
        assert "nope" in result["error"]
