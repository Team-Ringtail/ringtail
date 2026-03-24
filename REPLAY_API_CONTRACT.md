# Replay API Contract (Logical + Live Mapping)

This document describes replay-specific operations and how they map onto the live API.

## Live Transport

Replay actions are currently executed through:

- `POST /function/optimize_sync` with `{"request": {"operation": ...}}`

Canonical operation names/defaults:

- `src/core/optimization_request_contract.py`
- `POST /function/get_optimization_contract`

## Replay Operations

- `discover_and_rank_replay_repo`
- `optimize_replay_function`
- `optimize_best_replay_function`
- `optimize_best_replay_in_repo`

Replay inspection helpers in `src/api/optimization_requests.jac`:

- `inspect_replay_repo(...)`
- `inspect_replay_function(...)`
- `inspect_replay_session(...)`
- `discover_and_rank_replay_file(...)`

## Request Envelope

```json
{
  "request": {
    "operation": "discover_and_rank_replay_repo",
    "source_root": "/abs/path/to/repo",
    "script_path": "/abs/path/to/driver.py",
    "tests_root": "tests",
    "limit": 10
  }
}
```

## Response Shape

Replay ranking operations return a list of candidate dicts (source file, function name/call, timing/complexity, replay counts).

Replay optimization operations return standard optimization result dicts with additional replay selection fields where relevant.

## Error Contract

Replay failures should include top-level `error`, for example:

```json
{
  "error": "Replay trace captured no replay-backed repo candidates"
}
```

## Recommended UI Flow

1. Discover/rank replay candidates.
2. Let user choose one target or one-click best target.
3. Run replay-backed optimization.
4. Display before/after metrics and code.
5. Apply only when `test_passed=true` and `error` is empty.

## Related Docs

- `API_DOCUMENTATION.md` (full live API)
- `OPTIMIZATION_CONTRACT.md` (all operation names/defaults)
- `interfaces.md` (user-facing usage)
