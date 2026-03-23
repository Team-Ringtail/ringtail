# Baseline Performance Report

- Created: 2026-03-23T19:36:53.420368+00:00
- Output directory: /Users/lancebuescher/Umich/course_code/eecs449/ringtail/benchmarks/baselines/baseline_20260323_190116
- Server URL: http://127.0.0.1:8000
- Warmups: 2
- Trials per case: 8
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
- file_async_submit_optimization_job: p50=31803.90ms p95=70621.32ms cv=0.3478 llm_calls=32 prompt_tokens=12004 completion_tokens=5715 estimated_cost_usd=0.000000
- file_sync_optimize_file_function: p50=33854.71ms p95=47817.18ms cv=0.1374 llm_calls=34 prompt_tokens=12635 completion_tokens=6122 estimated_cost_usd=0.000000
- function_sync_optimize_input: p50=33231.63ms p95=48004.72ms cv=0.1484 llm_calls=34 prompt_tokens=12955 completion_tokens=6608 estimated_cost_usd=0.000000
- replay_sync_optimize_replay_function: p50=48393.24ms p95=103518.96ms cv=0.3404 llm_calls=48 prompt_tokens=25357 completion_tokens=9896 estimated_cost_usd=0.000000
- repo_sync_run_repo_agent_job: p50=56192.80ms p95=58301.27ms cv=0.0222 llm_calls=0 prompt_tokens=0 completion_tokens=0 estimated_cost_usd=0.000000

## Notes
- Replay case may fail if replay tracing cannot create cache state in your runtime.
- Stage timings are approximate until explicit stage start/end events exist in run logs.
- Use this report as the locked baseline before implementing optimization/refactor changes.
