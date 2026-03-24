# Ringtail HTTP API (Live Contract)

This document describes the live HTTP surface exposed by `jac start main.jac`.

## Base URL

- Local default: `http://localhost:8000`

All calls are `POST /function/<public-function-name>` with JSON payload.

## Endpoint Groups

### Diagnostics

- `health()`
- `hello(name="Ringtail")`
- `get_auth_readiness()`
- `get_config_doctor()`
- `get_latest_run(kind="any")`

### Optimization / contract

- `optimize_sync(request)`
- `get_optimization_contract()`

### Async jobs

- `submit_optimization_job(request)`
- `get_optimization_job(job_id)`
- `run_repo_agent_sync(request)`
- `submit_repo_agent_job(request)`
- `get_repo_agent_job(job_id)`
- `get_recent_jobs(limit=10)`

### Demo / benchmark

- `get_ranked_demo_suite_catalog(benchmark_id="")`
- `get_ranked_demo_benchmarks()`
- `get_latest_ranked_demo_suite()`
- `get_ranked_demo_job_progress(job_id)`

### GitHub auth/session/install

- `get_github_app_install_info(state="")`
- `handle_github_app_install_callback(installation_id, setup_action="", state="")`
- `verify_github_repo_access(request)`
- `get_github_login_url(redirect_uri="")`
- `exchange_github_code(code, state)`
- `get_session(session_token)`
- `logout(session_token)`
- `save_github_installation(session_token, installation_id, account_login="")`

## Payload Shape Rules

### Rule 1: parameter name matching

For each route, send a JSON object whose keys match the function parameters.

Examples:

- `health()` -> `{}`
- `get_optimization_job(job_id)` -> `{"job_id": "..."}`
- `optimize_sync(request)` -> `{"request": { ...operation payload... }}`

### Rule 2: optimization operations are nested in `request`

`optimize_sync` and async submit routes expect a `request` dict whose `operation` controls behavior.

```json
{
  "request": {
    "operation": "optimize_input",
    "config_name": "live-fast",
    "analysis_mode": "llm",
    "input": {
      "source_code": "def f(x): return x",
      "function_name": "f",
      "function_call": "f(1)",
      "test_cases": [{"call": "f(1)", "expected": 1}]
    }
  }
}
```

## Operation Names

Source of truth:

- `src/core/optimization_request_contract.py`
- `POST /function/get_optimization_contract`

Current discovery operations include `discover_and_rank_file` and `discover_and_rank_directory`.

## cURL Examples

### Health

```bash
curl -s -X POST http://localhost:8000/function/health \
  -H 'Content-Type: application/json' -d '{}'
```

### Sync optimize

```bash
curl -s -X POST http://localhost:8000/function/optimize_sync \
  -H 'Content-Type: application/json' \
  -d '{"request":{"operation":"optimize_input","config_name":"test-fast","analysis_mode":"mock","input":{"source_code":"def slow_add(n):\\n    s=0\\n    for i in range(n):\\n        s+=i\\n    return s\\n","function_name":"slow_add","function_call":"slow_add(1000)","test_cases":[{"call":"slow_add(5)","expected":10}]}}}'
```

### Submit async optimize + poll

```bash
curl -s -X POST http://localhost:8000/function/submit_optimization_job \
  -H 'Content-Type: application/json' \
  -d '{"request":{"operation":"optimize_input","config_name":"test-fast","analysis_mode":"mock","input":{"source_code":"def f(x): return x","function_name":"f","function_call":"f(1)","test_cases":[{"call":"f(1)","expected":1}]}}}'

curl -s -X POST http://localhost:8000/function/get_optimization_job \
  -H 'Content-Type: application/json' \
  -d '{"job_id":"<job-id>"}'
```

## Errors

- Most failures return a dict containing top-level `error`.
- Some routes can return FastAPI/Jaseci validation errors if required body keys are missing.

## Related Docs

- `interfaces.md` for user-oriented workflows
- `OPTIMIZATION_CONTRACT.md` for operation semantics
- `REPLAY_API_CONTRACT.md` for replay-specific logical contract
