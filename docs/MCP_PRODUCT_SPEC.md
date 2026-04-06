# Ringtail MCP Product Spec

## Goal
Ringtail's MCP surface is for coding agents that have already finished writing code and want a separate, performance-specific toolchain to:

1. profile a real workload
2. rank the hotspots that are worth editing
3. return a validated patch for one hotspot
4. escalate to a longer async repo pass only when the fast path is not enough

The default trust model is strict validation. Ringtail should only report a successful optimization when it can show measured improvement and preserved correctness.

## Recommended Call Order

1. Call `profile_repo`.
2. Inspect `recommended_targets`.
3. Call `optimize_hotspot` with one hotspot id.
4. If the agent wants a broader autonomous pass, call `submit_optimize_repo_job` and poll `get_optimize_repo_job`.

## Tool Contracts

### `profile_repo`

Inputs:
- `repo_path`
- `entry_point`
- `pct_threshold`
- `max_results`
- `timeout_s`

Success output:
- `kind: "profile_report"`
- `total_time`
- `functions_analyzed`
- `hot_function_count`
- `editable_hotspot_count`
- `recommended_targets`
- `hotspots`
- `message`
- `next_action`

Each hotspot includes:
- canonical `id`
- `module`, `function`, `file`, `line`
- `tottime`, `cumtime`, `ncalls`, `hotness_pct`
- `ownership` as one of `user_code`, `mixed`, `library_bound`
- `editable`
- `worth_optimizing`
- `skip_reason`
- `callers`, `callees`
- `recommendation`

Failure output:
- `success: false`
- `error.code`
- `error.message`
- optional `error.details`

### `optimize_hotspot`

Inputs:
- `repo_path`
- `entry_point`
- one of:
  - `hotspot_id`
  - `file_path` plus `function_name`
- optional `analysis_mode`
- optional `llm_model`
- `min_speedup`
- `timeout_s`

Success output:
- `kind: "hotspot_optimization"`
- `target`
- `validation`
- `metrics`
- `attempts`
- `patch`
- `message`

`validation.accepted` is only true when the acceptance gate passes.

Rejected output:
- `success: false`
- same structured body as above
- `error.code: "optimization_rejected"`
- `error.message` describing why the candidate was rejected

### `submit_optimize_repo_job`

Inputs:
- `repo_url`
- `entry_point`
- optional `prompt`
- optional `base_branch`
- optional `max_targets`
- optional `tests_root`
- optional `publish_pr`
- optional `analysis_mode`
- optional `llm_model`

Success output:
- `kind: "async_repo_optimization_submission"`
- `job_id`
- `status`
- `run_id`
- `run_log_path`

### `get_optimize_repo_job`

Inputs:
- `job_id`

Output:
- `kind: "async_repo_optimization_status"`
- `job`

## Acceptance Gate

Ringtail accepts a hotspot optimization only when:
- tests passed for the candidate
- post-optimization profiling completed
- a measured speedup exists
- measured speedup is at least `min_speedup`

Rejected candidates must be explicit failures, not soft successes.

## Latency Targets

- `profile_repo`: fast local feedback, usually seconds not minutes
- `optimize_hotspot`: slower than profiling, but still scoped to one target
- `submit_optimize_repo_job`: long-running and explicitly async

## Deprecated MCP Behavior

The old mental model of calling a broad synchronous repo optimizer as the first MCP step is no longer the recommended path. Agents should start with `profile_repo` and use the async repo flow only as an escalation path.
