## Ringtail Replay API - Current Server Contract

### Overview

- **Purpose**: Replay-driven optimization surface used by Ringtail CLI and UI.
- **Current transport**: Replay operations are routed through `POST /function/optimize_sync` using an `operation` field.
- **Backend module**: `src/api/optimization_requests.jac`.
- **Canonical operation/default contract**: `src/core/optimization_request_contract.py` and `/function/get_optimization_contract`.
- **Local base URL**: `http://localhost:8000`.

---

## Architecture and Routing

When running `jac start main.jac`, public API functions are exposed under `/function/<name>`.

Replay-specific operations are handled by `run_optimization_request(...)` and selected with:

```json
{
  "operation": "<operation-name>",
  "...": "operation-specific fields"
}
```

Supported replay operation names:

- `discover_and_rank_replay_repo`
- `optimize_replay_function`
- `optimize_best_replay_function`
- `optimize_best_replay_in_repo`

Replay inspection helpers also exist as callable public functions in `src/api/optimization_requests.jac`:

- `inspect_replay_repo(...)`
- `inspect_replay_function(...)`
- `inspect_replay_session(...)`
- `discover_and_rank_replay_file(...)`

---

## Conventions

- **Content type**: `application/json`
- **HTTP method**: `POST`
- **Paths**:
  - `POST /function/optimize_sync` (primary replay operations)
  - Optional direct function route for inspect helpers (depends on Jac runtime/module loading): `POST /function/<public-function-name>`
- **File paths**: `source_root`, `script_path`, and `file_path` should be absolute paths on the server host.

---

## Error Handling

- Failures should include a top-level `error` string.
- Optimization-style failures usually keep the normal response shape and set a non-empty `error`.

Minimum failure shape:

```json
{
  "error": "Replay trace captured no replay-backed repo candidates"
}
```

---

## Replay Operations via `/function/optimize_sync`

### 1) Rank replay-backed repo candidates

Request:

```json
{
  "operation": "discover_and_rank_replay_repo",
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py",
  "tests_root": "tests",
  "limit": 10
}
```

Response shape:

```json
[
  {
    "source_file": "/abs/repo/pkg/b.py",
    "function_name": "beta",
    "function_call": "beta(2)",
    "median_ms": 0.12,
    "peak_memory_kb": 8.0,
    "cyclomatic_complexity": 2,
    "discovered_test_count": 1,
    "replay_trace_count": 2,
    "replay_unique_call_count": 2,
    "replay_partial_success": false,
    "replay_script": "/abs/repo/drive.py"
  }
]
```

### 2) Optimize one replay-backed function

Request:

```json
{
  "operation": "optimize_replay_function",
  "file_path": "/absolute/path/to/file.py",
  "function_name": "target_fn",
  "script_path": "/absolute/path/to/driver.py",
  "tests_root": "tests"
}
```

Response shape:

```json
{
  "optimized_code": "def target_fn(...): ...",
  "iteration_number": 1,
  "metrics": {
    "execution_time": 0.12,
    "memory_usage": 8.0,
    "cpu_usage": null,
    "code_complexity": 2,
    "test_coverage": 100.0
  },
  "baseline_metrics": {
    "execution_time": 0.14,
    "memory_usage": 8.5,
    "cpu_usage": null,
    "code_complexity": 3,
    "test_coverage": 100.0
  },
  "test_passed": true,
  "improvement_ratio": 1.16,
  "termination_reason": "execution time within target",
  "converged": true,
  "error": ""
}
```

### 3) Optimize best replay-backed function in one file

Request:

```json
{
  "operation": "optimize_best_replay_function",
  "file_path": "/absolute/path/to/file.py",
  "script_path": "/absolute/path/to/driver.py",
  "tests_root": "tests"
}
```

Response is the optimization shape above plus:

- `selected_function`
- `replay_trace_count`

### 4) Optimize best replay-backed target in a repo

Request:

```json
{
  "operation": "optimize_best_replay_in_repo",
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py",
  "tests_root": "tests"
}
```

Response is the optimization shape above plus:

- `selected_source_file`
- `selected_function`
- `replay_trace_count`
- `selection_score`

---

## Optional Direct Inspect Calls

If your runtime exposes imported public functions as REST routes, these can be called directly:

- `POST /function/inspect_replay_repo`
- `POST /function/inspect_replay_function`
- `POST /function/inspect_replay_session`
- `POST /function/discover_and_rank_replay_file`

For maximum compatibility across environments, prefer routing replay actions through `POST /function/optimize_sync` with `operation`.

---

## Suggested UI Flow

1. Rank repo candidates using `discover_and_rank_replay_repo`.
2. Let the user choose either:
   - one function (`optimize_replay_function`), or
   - one-click best-in-repo (`optimize_best_replay_in_repo`).
3. Show before/after metrics and optimized code.
4. Only auto-apply when `test_passed` is true and `error` is empty.

