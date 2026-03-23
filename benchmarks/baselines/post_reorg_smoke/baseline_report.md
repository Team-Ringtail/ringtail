# Baseline Performance Report

- Created: 2026-03-23T20:28:46.716432+00:00
- Output directory: /Users/lancebuescher/Umich/course_code/eecs449/ringtail/benchmarks/baselines/post_reorg_smoke
- Server URL: http://127.0.0.1:8000
- Warmups: 0
- Trials per case: 1
- Config: baseline-measure
- Analysis mode: llm
- LLM model override: (none)
- Repo target: /Users/lancebuescher/Umich/course_code/eecs449/ringtail/benchmarks/ranked_pitch_repo

## Cases
- file_async_submit_optimization_job
- file_sync_optimize_file_function
- function_sync_optimize_input
- replay_sync_optimize_replay_function
- repo_sync_run_repo_agent_job

## Metrics
- file_async_submit_optimization_job: p50=39325.18ms p95=39325.18ms cv=0.0000 llm_calls=4 prompt_tokens=1499 completion_tokens=706 estimated_cost_usd=0.000000
- file_sync_optimize_file_function: p50=36301.18ms p95=36301.18ms cv=0.0000 llm_calls=4 prompt_tokens=1521 completion_tokens=770 estimated_cost_usd=0.000000
- function_sync_optimize_input: p50=37005.49ms p95=37005.49ms cv=0.0000 llm_calls=4 prompt_tokens=1546 completion_tokens=788 estimated_cost_usd=0.000000
- replay_sync_optimize_replay_function: p50=55826.86ms p95=55826.86ms cv=0.0000 llm_calls=6 prompt_tokens=3177 completion_tokens=1172 estimated_cost_usd=0.000000
- repo_sync_run_repo_agent_job: p50=64635.26ms p95=64635.26ms cv=0.0000 llm_calls=0 prompt_tokens=0 completion_tokens=0 estimated_cost_usd=0.000000

## Notes
- Replay case may fail if replay tracing cannot create cache state in your runtime.
- Stage timings are approximate until explicit stage start/end events exist in run logs.
- Use this report as the locked baseline before implementing optimization/refactor changes.
