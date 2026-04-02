# Optimization Request Contract

This document defines the canonical optimization request contract shared across CLI, web, async jobs, and repo-agent orchestration.

## Defaults

- `operation`: `optimize_input`
- `config_name`: `live-fast`
- `analysis_mode`: `llm`
- `enable_run_log`: `true`

Defaults are applied for optimization operations only.

## Optimization Operations

- `optimize_input`
- `optimize_file_function`
- `optimize_replay_function`
- `optimize_best_replay_function`
- `optimize_best_replay_in_repo`
- `run_repo_agent_job`

## Discovery / Metadata Operations

- `discover_and_rank_file`
- `discover_and_rank_directory`
- `discover_and_rank_replay_repo`
- `get_ranked_demo_suite_catalog`
- `get_ranked_demo_benchmarks`
- `get_latest_ranked_demo_suite`
- `get_ranked_demo_job_progress`
- `run_ranked_demo_suite`

## Entrypoints

- Web/API sync: `POST /function/optimize_sync`
- Web/API async submit: `POST /function/submit_optimization_job`
- Web/API async poll: `POST /function/get_optimization_job`
- Repo shortcuts: `submit_repo_agent_job`, `get_repo_agent_job`, `run_repo_agent_sync`
- CLI wrappers: `ringtail file optimize`, `ringtail repo submit|run|status|watch`

## Source Of Truth

- Python contract helpers: `src/core/optimization_request_contract.py`
- Jac dispatcher: `src/api/optimization_requests.jac` (`run_optimization_request`)
- Public contract endpoint: `GET/POST /function/get_optimization_contract`
