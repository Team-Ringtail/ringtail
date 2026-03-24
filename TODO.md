# Ringtail TODO (Current)

This file tracks high-level remaining work. Historical implementation checklists were removed because they no longer reflected current architecture.

## Interfaces

- [ ] Add browser-based regression checks for Web UI action flows (paste, benchmark, repo tabs).
- [ ] Add a small SDK smoke test module under `tests/` for `optimize_code`, `discover_targets`, and `rank_targets`.
- [ ] Ensure all HTTP examples in docs are exercised in CI smoke jobs.

## API / Contract

- [ ] Resolve Jac type-check warnings in `src/api/optimization_requests.jac` for helper wrappers around `dict | list` return types.
- [ ] Add contract-version metadata to `/function/get_optimization_contract` payload.
- [ ] Add explicit route-level examples for `discover_and_rank_file` and replay inspect helpers.

## Web App

- [ ] Refactor `main.jac` client component into smaller internal sections while preserving Jac import compatibility.
- [ ] Add clear UI messaging for missing GitHub OAuth/App config and missing LLM keys.
- [ ] Add a lightweight in-app "API request inspector" panel for troubleshooting action failures.

## Repo-Agent

- [ ] Add optional resume/retry tooling for interrupted async jobs.
- [ ] Improve automatic setup/test command inference for non-standard Python repos.
- [ ] Add clearer PR publish gating in output when auth mode is incomplete.

## Benchmarks / Reporting

- [ ] Add nightly baseline capture automation and drift alerting.
- [ ] Add markdown summary renderer for repo suite CSV output.
- [ ] Add a compact leaderboard artifact for top improvements.

## Documentation

- [ ] Keep `interfaces.md`, `API_DOCUMENTATION.md`, and `OPTIMIZATION_CONTRACT.md` synchronized after each contract change.
- [ ] Add a dedicated "interface migration notes" section whenever route signatures change.

