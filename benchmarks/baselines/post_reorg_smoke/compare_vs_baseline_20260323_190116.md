# Post-Reorg Comparison

- baseline: `benchmarks/baselines/baseline_20260323_190116`
- candidate: `benchmarks/baselines/post_reorg_smoke`

## file_async_submit_optimization_job
- p50 ms: baseline=31803.90, post_reorg=39325.18, delta=+7521.28
- status counts baseline ok/error=8/0
- status counts post_reorg ok/error=1/0

## file_sync_optimize_file_function
- p50 ms: baseline=33854.71, post_reorg=36301.18, delta=+2446.47
- status counts baseline ok/error=8/0
- status counts post_reorg ok/error=1/0

## function_sync_optimize_input
- p50 ms: baseline=33231.63, post_reorg=37005.49, delta=+3773.86
- status counts baseline ok/error=8/0
- status counts post_reorg ok/error=1/0

## replay_sync_optimize_replay_function
- p50 ms: baseline=48393.24, post_reorg=55826.86, delta=+7433.62
- status counts baseline ok/error=0/8
- status counts post_reorg ok/error=0/1

## repo_sync_run_repo_agent_job
- p50 ms: baseline=56192.80, post_reorg=64635.26, delta=+8442.47
- status counts baseline ok/error=8/0
- status counts post_reorg ok/error=1/0
