# Ringtail Interfaces

This document explains how to use every public interface currently supported by Ringtail and how they map to the same operation contract.

## Quick Start: Which Interface To Use?

- **Web UI**: best for interactive runs, demo/pitch flows, and visual feedback.
- **HTTP API**: best for integrations from external tools/services.
- **CLI**: best for local terminal workflows and scripting.
- **Python SDK**: best for embedding Ringtail directly in Python automation.

## Prerequisites

- Python environment and deps installed (`pip install -r requirements.txt && pip install -e .`)
- Jac available (`jac --version`)
- Optional (LLM-backed optimization): `RINGTAIL_ANTHROPIC_API_KEY`
- Optional (GitHub repo-agent flows): `RINGTAIL_REPO_AGENT_CONFIG`

Run diagnostics:

```bash
ringtail config doctor
```

## 1) Web UI Interface

Source: [`main.jac`](main.jac) (`cl def:pub app`). The component must live in the entry module so `jac start` can register it (JSX-only modules do not export `app` to Python). The dashboard calls the HTTP API from the browser via `POST /function/<name>` using the `ringtail_*` helpers on the `app` component.

### Start the web app

```bash
jac start main.jac --port 8000
```

Open `http://localhost:8000`.

### Tabs and behavior

- **Paste Optimizer**
  - Submits `operation: optimize_input` via `submit_optimization_job`
  - Streams updates with `wait_job_notification` (long-poll Observer on the same `jac start` port; server notifies on job and run-log changes)
  - Shows before/after metrics and optimized code
- **Benchmark Studio**
  - Uses `run_ranked_demo_suite`
  - Streams progress via `wait_job_notification` plus merged `get_ranked_demo_job_progress` payloads
  - Renders suite summaries/graphs
- **Optimize a Repo**
  - Uses GitHub session/install endpoints plus repo-agent submit and `wait_job_notification` for job status
  - Requires an explicit repo `entry_point`; Ringtail does not infer one
  - Runs repo validation only when you provide a `test_command`
  - Requires GitHub auth config; otherwise shows readiness/config errors

`jac start` uses stdlib `http.server` (no native SSE route in-app). Ringtail implements push semantics with an in-process `JobEventHub` (`src/core/job_event_hub.py`) and `POST /function/wait_job_notification`.

### Known failure mode to expect

If GitHub OAuth/App is not configured, repo/GitHub actions return actionable config errors (expected behavior), not a crash.

## 2) HTTP API Interface

Base URL (local): `http://localhost:8000`

All routes are `POST /function/<name>` with JSON payload.

### Core endpoints

- `health`
- `optimize_sync`
- `get_optimization_contract`
- `submit_optimization_job`
- `get_optimization_job`
- `run_repo_agent_sync`
- `submit_repo_agent_job`
- `get_repo_agent_job`
- `get_ranked_demo_benchmarks`
- `get_ranked_demo_suite_catalog`
- `get_ranked_demo_job_progress`
- `get_latest_ranked_demo_suite`
- `get_latest_run`
- `get_auth_readiness`
- `get_config_doctor`

### Example: sync optimize request

```bash
curl -X POST http://localhost:8000/function/optimize_sync \
  -H 'Content-Type: application/json' \
  -d '{
    "request": {
      "operation": "optimize_input",
      "config_name": "test-fast",
      "analysis_mode": "mock",
      "input": {
        "source_code": "def slow_add(n):\\n    s=0\\n    for i in range(n):\\n        s+=i\\n    return s\\n",
        "function_name": "slow_add",
        "function_call": "slow_add(1000)",
        "test_cases": [{"call":"slow_add(5)","expected":10}]
      }
    }
  }'
```

### Request shape note

For public route handlers that accept `request: dict`, the HTTP payload should wrap fields under `{"request": ...}`.

## 3) CLI Interface

Source: `src/ringtail_cli.py`

### Start web server

```bash
ringtail serve --port 8000
```

### Optimize a function locally (no HTTP server required)

```bash
ringtail file optimize benchmarks/local_file_suite/slow_sum.py slow_sum \
  --function-call "slow_sum(1000)" \
  --config-name test-fast \
  --local --json
```

### Repo-agent commands

- Submit: `ringtail repo submit ...`
- Run and wait: `ringtail repo run ...`
- Poll: `ringtail repo status <job_id>`
- Watch: `ringtail repo watch <job_id>`
- Stream logs: `ringtail repo logs <job_id>`

Repo jobs require `--entry-point`. `--test-command` is optional and only runs when provided.

## 4) Python SDK Interface

Source: `src/sdk.py`

```python
from src import sdk

result = sdk.optimize_code(
    source_code="def slow_add(n):\n    s=0\n    for i in range(n):\n        s+=i\n    return s\n",
    function_call="slow_add(1000)",
    function_name="slow_add",
    test_cases=[{"call": "slow_add(5)", "expected": 10}],
    config_name="test-fast",
    analysis_mode="mock",
)

ranked_dir = sdk.discover_targets("benchmarks/local_file_suite", limit=3)
ranked_file = sdk.rank_targets("benchmarks/local_file_suite/slow_sum.py", limit=3)
repo_result = sdk.optimize_repo(
    "/path/to/repo",
    prompt="make this faster",
    entry_point="python runner.py",
)
```

### SDK functions

- `optimize_code(...)`
- `optimize_function(...)`
- `optimize_repo(...)`
- `discover_targets(...)`
- `rank_targets(...)`

## 5) Cross-Interface Contract Map

| Capability | Web UI | HTTP route | CLI | SDK | Operation |
|---|---|---|---|---|---|
| Optimize pasted code | Paste tab | `submit_optimization_job` / `get_optimization_job` | `ringtail file optimize` | `optimize_code`, `optimize_function` | `optimize_input`, `optimize_file_function` |
| Rank directory targets | Benchmark prep | `optimize_sync` | (indirect via repo/demo flows) | `discover_targets` | `discover_and_rank_directory` |
| Rank file targets | (internal) | `optimize_sync` | (indirect) | `rank_targets` | `discover_and_rank_file` |
| Run demo benchmark | Benchmark tab | `submit_optimization_job` + `get_ranked_demo_job_progress` | (runner scripts) | (n/a) | `run_ranked_demo_suite` |
| Repo optimization | Repo tab | `submit_repo_agent_job` / `get_repo_agent_job` | `ringtail repo submit/run/status/watch/logs` | `optimize_repo` | `run_repo_agent_job` |

## 6) Troubleshooting

- **UI loads but repo actions fail**
  - Check `get_auth_readiness` and `get_config_doctor`
  - Usually missing `RINGTAIL_REPO_AGENT_CONFIG` or GitHub OAuth/App settings
- **LLM operations fail**
  - Ensure `RINGTAIL_ANTHROPIC_API_KEY` is set
  - Use `config_name=test-fast` + `analysis_mode=mock` for local deterministic tests
- **Endpoint works via curl but not UI**
  - Confirm request envelope shape (`{"request": ...}` where expected)
  - Check browser network payload for route/body mismatch
- **SDK discover/rank errors**
  - Ensure you are on the latest workspace version including `discover_and_rank_file` operation support
