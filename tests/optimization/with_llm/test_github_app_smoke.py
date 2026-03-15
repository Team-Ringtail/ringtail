import json
import os

import pytest

from src.core.github_repo_service import create_installation_access_token, verify_repo_access


@pytest.mark.skipif(
    not (
        (
            os.environ.get("RINGTAIL_REPO_AGENT_CONFIG")
            or (
                os.environ.get("RINGTAIL_GITHUB_APP_ID")
                and (os.environ.get("RINGTAIL_GITHUB_APP_PRIVATE_KEY") or os.environ.get("RINGTAIL_GITHUB_APP_PRIVATE_KEY_PATH"))
                and os.environ.get("RINGTAIL_GITHUB_APP_INSTALLATION_ID")
            )
        )
        and os.environ.get("RINGTAIL_GITHUB_SMOKE_REPO_URL")
    ),
    reason="GitHub App smoke env vars are not configured",
)
def test_github_app_installation_smoke():
    if os.environ.get("RINGTAIL_REPO_AGENT_CONFIG"):
        cfg = json.loads(os.environ["RINGTAIL_REPO_AGENT_CONFIG"])
        installation_id = int(cfg.get("installation_id") or cfg.get("auth", {}).get("installation_id"))
    else:
        installation_id = int(os.environ["RINGTAIL_GITHUB_APP_INSTALLATION_ID"])
    repo_url = os.environ["RINGTAIL_GITHUB_SMOKE_REPO_URL"]

    token_payload = create_installation_access_token(installation_id)
    assert token_payload["token"]

    access = verify_repo_access(repo_url, auth={"installation_id": installation_id})
    assert access["success"] is True
    assert access["auth_mode"] == "github_app_installation"
