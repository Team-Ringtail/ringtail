# Ringtail Task Tracking

Active workstream tracker for current architecture.

## Current Workstreams

| Workstream | Status | Notes |
|---|---|---|
| Interface reliability (Web/API/CLI/SDK parity) | In progress | Action-flow validation and contract alignment ongoing |
| Repo-agent robustness | In progress | Better diagnostics and recovery for async/repo jobs |
| Benchmark + baseline quality | In progress | Capture and compare regressions across releases |
| Documentation consistency | In progress | Keep interface/API/contract docs synchronized |

## Near-Term Priorities

- [ ] Eliminate remaining Jac type warnings in `src/api/optimization_requests.jac`.
- [ ] Add CI smoke checks that run one Web/API/CLI/SDK flow each.
- [ ] Validate repo tab UX when OAuth/App is not configured and when configured.
- [ ] Add one-page changelog entry whenever interface payloads/routes change.

## Historical Note

Older assignment-by-person checklists were archived because they referred to an earlier project phase and no longer matched the codebase structure.
