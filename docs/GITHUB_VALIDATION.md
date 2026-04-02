# GitHub Integration Validation

This guide covers how to validate GitHub auth/install and repo-agent integration.

## 1) Offline / local checks (no GitHub account required)

From repo root:

```bash
python -m pytest tests/unit/test_github_repo_service.py -v
python -m pytest tests/unit/test_github_oauth_and_sessions.py -v
jac test tests/unit/test_repo_agent_workflow.jac
```

These validate parsing, auth resolution, session persistence, and core repo-agent wiring without live GitHub calls.

## 2) Live smoke check (real GitHub App install)

Requires a GitHub App and installation on a test repo.

Set:

- `RINGTAIL_REPO_AGENT_CONFIG` (JSON string or path)
- `RINGTAIL_GITHUB_SMOKE_REPO_URL`

Then run:

```bash
python -m pytest tests/optimization/with_llm/test_github_app_smoke.py -v
```

Success means installation token minting and repo access checks work.

## 3) Product path check (web/api)

Start server:

```bash
jac start main.jac --port 8000
```

Then validate:

- `POST /function/get_auth_readiness`
- `POST /function/get_config_doctor`
- `POST /function/get_github_app_install_info`
- `POST /function/verify_github_repo_access`

## Not covered by automation yet

- Full browser OAuth login flow with callback and cookie/session restoration.
- End-to-end publish-PR flow against a real repo with `publish_pr: true`.
- Webhook signature validation for installation events.
