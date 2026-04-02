"""
Unit tests for GitHub App / token auth helpers (no network).

These double as a contract for “GitHub-enabled Ringtail” behavior: run

    python -m pytest tests/unit/test_github_repo_service.py -v

Live verification still needs a real GitHub App + installation; see docs/GITHUB_VALIDATION.md
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core import github_repo_service as gh


class FakeHTTPResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


@pytest.fixture
def clear_repo_agent_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RINGTAIL_REPO_AGENT_CONFIG", raising=False)
    for name in gh._TOKEN_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name in gh._APP_ID_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "url,owner,repo",
    [
        ("https://github.com/acme/widget", "acme", "widget"),
        ("https://github.com/acme/widget.git", "acme", "widget"),
        ("git@github.com:acme/widget.git", "acme", "widget"),
    ],
)
def test_parse_repo_slug_variants(url: str, owner: str, repo: str) -> None:
    assert gh.parse_repo_slug(url) == (owner, repo)


def test_parse_repo_slug_invalid() -> None:
    with pytest.raises(ValueError, match="Could not parse"):
        gh.parse_repo_slug("https://example.com/not-github")


def test_build_authenticated_clone_url_with_token() -> None:
    out = gh.build_authenticated_clone_url("https://github.com/o/r.git", "tok")
    assert out == "https://x-access-token:tok@github.com/o/r.git"


def test_build_authenticated_clone_url_without_token() -> None:
    url = "https://github.com/o/r.git"
    assert gh.build_authenticated_clone_url(url, None) == url


def test_resolve_github_auth_explicit_token_wins(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RINGTAIL_GITHUB_TOKEN", "from-env")
    ctx = gh.resolve_github_auth({"token": "from-auth"}, explicit_token="explicit")
    assert ctx["mode"] == "token"
    assert ctx["token"] == "explicit"


def test_resolve_github_auth_env_token(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    ctx = gh.resolve_github_auth(None)
    assert ctx["mode"] == "token"
    assert ctx["token"] == "env-token"


def test_resolve_github_auth_installation_mints_token(
    clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_create(iid: int, auth: dict | None = None) -> dict:
        calls.append(iid)
        return {"token": "iid-token", "expires_at": "2099-01-01T00:00:00Z", "permissions": {"contents": "read"}}

    monkeypatch.setattr(gh, "create_installation_access_token", fake_create)
    ctx = gh.resolve_github_auth({"installation_id": 4242})
    assert ctx["mode"] == "github_app_installation"
    assert ctx["token"] == "iid-token"
    assert ctx["installation_id"] == 4242
    assert calls == [4242]


def test_get_github_app_install_info_state_is_quoted(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "RINGTAIL_REPO_AGENT_CONFIG",
        json.dumps({"app_id": "1", "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----", "app_slug": "ringtail"}),
    )
    info = gh.get_github_app_install_info("a/b+c", None)
    assert info["configured"] is True
    # quote() leaves "/" safe; "+" must not be literal in query strings
    assert info["install_url"].endswith("?state=a/b%2Bc")


def test_verify_repo_access_no_token(clear_repo_agent_config) -> None:
    out = gh.verify_repo_access("https://github.com/o/r")
    assert out["success"] is False
    assert out["auth_mode"] == "none"
    assert "No GitHub token" in (out.get("error") or "")


def test_verify_repo_access_github_success(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RINGTAIL_GITHUB_TOKEN", "pat")

    payload = {
        "default_branch": "main",
        "private": True,
        "permissions": {"admin": False, "push": True},
        "clone_url": "https://github.com/o/r.git",
    }

    def fake_urlopen(request, timeout=30):  # noqa: ANN001
        return FakeHTTPResponse(json.dumps(payload).encode())

    monkeypatch.setattr(gh.urllib.request, "urlopen", fake_urlopen)

    out = gh.verify_repo_access("https://github.com/o/r")
    assert out["success"] is True
    assert out["auth_mode"] == "token"
    assert out["default_branch"] == "main"


def test_create_pull_request_posts_json(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=30):  # noqa: ANN001
        captured["data"] = json.loads(request.data.decode())
        captured["method"] = request.method
        return FakeHTTPResponse(json.dumps({"html_url": "https://github.com/o/r/pull/1"}).encode())

    monkeypatch.setattr(gh.urllib.request, "urlopen", fake_urlopen)

    pr = gh.create_pull_request(
        repo_url="https://github.com/o/r",
        title="t",
        body="b",
        head_branch="feat/x",
        base_branch="main",
        token="tok",
    )
    assert pr["html_url"].endswith("/pull/1")
    assert captured["method"] == "POST"
    assert captured["data"]["head"] == "feat/x"


def test_create_pull_request_http_error(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    err = gh.urllib.error.HTTPError("url", 422, "Unprocessable", hdrs=MagicMock(), fp=MagicMock())
    err.read = lambda: b'{"message":"validation failed"}'

    def boom(request, timeout=30):  # noqa: ANN001
        raise err

    monkeypatch.setattr(gh.urllib.request, "urlopen", boom)

    with pytest.raises(RuntimeError, match="GitHub PR creation failed: 422"):
        gh.create_pull_request(
            repo_url="https://github.com/o/r",
            title="t",
            body="b",
            head_branch="feat/x",
            base_branch="main",
            token="tok",
        )


def test_load_repo_agent_config_from_file(tmp_path: Path, clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"token": "file-token", "app_slug": "from-file"}), encoding="utf-8")
    monkeypatch.setenv("RINGTAIL_REPO_AGENT_CONFIG", str(cfg_path))
    merged = gh._load_repo_agent_env_config()
    assert merged["token"] == "file-token"
    assert merged["app_slug"] == "from-file"


def test_load_repo_agent_config_missing_file_raises(tmp_path: Path, clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RINGTAIL_REPO_AGENT_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(EnvironmentError, match="must be JSON or a path"):
        gh._load_repo_agent_env_config()


def test_handle_install_callback_lists_repos(clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_list(iid: int, auth: dict | None = None) -> dict:
        return {
            "total_count": 2,
            "repositories": [
                {"full_name": "o/a", "private": False, "default_branch": "main", "permissions": {}},
            ],
            "expires_at": "2099-01-01T00:00:00Z",
        }

    monkeypatch.setattr(gh, "list_installation_repositories", fake_list)
    out = gh.handle_github_app_install_callback(77, "install", "state-x")
    assert out["success"] is True
    assert out["installation_id"] == 77
    assert out["repository_count"] == 2
    assert out["state"] == "state-x"


class TestGithubIntegrationContract:
    """
    Named scenarios for “done” on GitHub-enabled product flows.
    All should pass offline; they lock API behavior the UI and jobs rely on.
    """

    def test_contract_token_env_names_include_gh_cli_token(self) -> None:
        assert "GH_TOKEN" in gh._TOKEN_ENV_NAMES

    def test_contract_resolve_accepts_github_installation_id_alias(
        self, clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            gh,
            "create_installation_access_token",
            lambda iid, auth=None: {"token": "t", "expires_at": None, "permissions": {}},
        )
        ctx = gh.resolve_github_auth({"github_installation_id": 100})
        assert ctx["installation_id"] == 100

    def test_contract_install_url_uses_official_apps_path(
        self, clear_repo_agent_config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "RINGTAIL_REPO_AGENT_CONFIG",
            json.dumps(
                {
                    "app_id": "1",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
                    "app_slug": "my-app",
                }
            ),
        )
        info = gh.get_github_app_install_info(None)
        assert info["install_url"] == "https://github.com/apps/my-app/installations/new"
