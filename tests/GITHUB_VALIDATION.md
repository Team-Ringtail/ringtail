# GitHub integration validation

## Automated (no GitHub account)

From the repo root:

```bash
python -m pytest tests/unit/test_github_repo_service.py -v
jac test tests/unit/test_repo_agent_workflow.jac
```

Or:

```bash
python scripts/validate_github_integration.py
```

## Human / staging (real GitHub App)

Requires a [GitHub App](https://docs.github.com/en/apps/creating-github-apps) with a private key, and an installation on a test repo.

1. Set `RINGTAIL_REPO_AGENT_CONFIG` (JSON or path to JSON) with at least `app_id`, `private_key` or `private_key_path`, and `installation_id` for a test install.
2. Set `RINGTAIL_GITHUB_SMOKE_REPO_URL` to that repo’s HTTPS URL.
3. Run:

```bash
python -m pytest tests/optimization/with_llm/test_github_app_smoke.py -v
```

Success means installation tokens mint correctly and `verify_repo_access` sees the repo.

## Not covered by automation yet

These need product implementation plus optional new tests:

- OAuth “Sign in with GitHub” session (identity) — separate from App installation tokens.
- Persisting `installation_id` per user/team after install (database).
- Webhook signature verification for `installation` events.
- End-to-end: `jac start` → `get_github_app_install_info` → browser install → callback URL → `submit_repo_agent_job` with stored `installation_id` and `publish_pr: true`.

When those exist, extend `tests/unit/test_github_repo_service.py` or add integration tests under `tests/integration/`.
