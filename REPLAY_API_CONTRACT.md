# Replay API Contract

Minimum backend contract for the replay-driven CLI/web flow.

This keeps the surface small while the internals are still evolving.

## Goals

- Let the UI run a replay script and see what code was actually exercised.
- Let the UI show ranked replay-backed optimization targets.
- Let the UI optimize either the best target automatically or one chosen target.
- Avoid exposing lots of tuning knobs for now.

## Endpoint 1: Inspect Replay Repo

`POST /replay/inspect`

Purpose: run the replay trace and return the observed repo candidates.

Request:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

Response:

```json
{
  "source_files": [
    "/abs/repo/pkg/a.py",
    "/abs/repo/pkg/b.py"
  ],
  "replay_script": "/abs/repo/drive.py",
  "observed_source_files": [
    "/abs/repo/pkg/a.py",
    "/abs/repo/pkg/b.py"
  ],
  "observed_function_keys": [
    "/abs/repo/pkg/a.py::alpha",
    "/abs/repo/pkg/b.py::beta"
  ],
  "candidate_count": 2,
  "candidates": [
    {
      "source_file": "/abs/repo/pkg/a.py",
      "function_name": "alpha",
      "function_call": "alpha(1)",
      "replay_trace_count": 1,
      "discovered_test_count": 0
    },
    {
      "source_file": "/abs/repo/pkg/b.py",
      "function_name": "beta",
      "function_call": "beta(2)",
      "replay_trace_count": 2,
      "discovered_test_count": 1
    }
  ],
  "replay_trace": {
    "success": true,
    "total_trace_count": 3,
    "observed_source_files": [
      "/abs/repo/pkg/a.py",
      "/abs/repo/pkg/b.py"
    ],
    "run_error": "",
    "partial_success": false
  }
}
```

Notes:

- This should back `inspect_replay_repo(...)`.
- The UI can use this as the first screen after a replay run.

## Endpoint 2: Rank Replay Repo Candidates

`POST /replay/rank`

Purpose: return replay-backed repo candidates in best-first order.

Request:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

Response:

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

Notes:

- This should back `discover_and_rank_replay_repo(...)`.
- The backend owns the ranking formula.

## Endpoint 3: Optimize Best Replay Target

`POST /replay/optimize-best`

Purpose: one-click workflow for the UI. Trace, rank, choose, optimize.

Request:

```json
{
  "source_root": "/absolute/path/to/repo-or-subdir",
  "script_path": "/absolute/path/to/driver.py"
}
```

Response:

```json
{
  "selected_source_file": "/abs/repo/pkg/b.py",
  "selected_function": "beta",
  "replay_trace_count": 2,
  "optimized_code": "def beta(...): ...",
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

Notes:

- This should back `optimize_best_replay_in_repo(...)`.
- This is the simplest “do the thing” entrypoint for the web UI.

## Endpoint 4: Optimize One Replay Target

`POST /replay/optimize-one`

Purpose: optimize a specific replay-backed function chosen by the user.

Request:

```json
{
  "source_file": "/absolute/path/to/file.py",
  "function_name": "target_fn",
  "script_path": "/absolute/path/to/driver.py"
}
```

Response:

Same shape as `POST /replay/optimize-best`, but `selected_source_file` and
`selected_function` should match the requested target.

Notes:

- This should back `optimize_replay_function(...)` for now.
- We can later add a repo-aware version if needed, but this is enough for MVP.

## Error Shape

All replay endpoints should return a top-level `error` string on failure.

Suggested minimum failure response:

```json
{
  "error": "Replay trace captured no replay-backed repo candidates"
}
```

If the endpoint normally returns optimization results, it can keep the current
result-shaped error object as long as `error` is present and non-empty.

## Mapping To Current Backend Functions

- `POST /replay/inspect` -> `inspect_replay_repo(...)`
- `POST /replay/rank` -> `discover_and_rank_replay_repo(...)`
- `POST /replay/optimize-best` -> `optimize_best_replay_in_repo(...)`
- `POST /replay/optimize-one` -> `optimize_replay_function(...)`

## Suggested UI Flow

1. Call `POST /replay/inspect`
2. Show observed candidates
3. Optionally call `POST /replay/rank`
4. Either:
   - call `POST /replay/optimize-best`, or
   - let the user choose one candidate and call `POST /replay/optimize-one`
