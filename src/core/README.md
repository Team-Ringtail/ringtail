# src/core/ — Module Guide

This directory contains the core logic for Ringtail's optimization pipeline.
Files are grouped by domain below to help navigate the 24-file flat layout.

## Optimization Pipeline


| File                               | Role                                                                                  |
| ---------------------------------- | ------------------------------------------------------------------------------------- |
| `optimization_loop.jac`            | Central orchestration: profile baseline, iterate agent plan/write/test/compare cycles |
| `optimization_request_contract.py` | Canonical operation names, defaults, normalization helpers (pure Python)              |
| `parallel_candidate_eval.py`       | ThreadPool wrapper for evaluating multiple candidate optimizations concurrently       |
| `post_test_runner.py`              | Post-iteration checks: re-profile + property tests in parallel                        |


## Measurement


| File                  | Role                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| `profiler.jac`        | Subprocess-based pytest-benchmark + tracemalloc profiling                |
| `deep_profiler.jac`   | Scalene-based per-line CPU/memory profiling for targeted deep dives      |
| `tester.jac`          | Isolated pytest runner with optional coverage                            |
| `property_tester.jac` | Hypothesis-based property tests comparing baseline vs optimized behavior |


## Discovery & Ranking


| File               | Role                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| `discovery.jac`    | File/function discovery, replay input building, test inference           |
| `ranker.jac`       | Profile + complexity scoring to rank functions by optimization potential |
| `replay_tracer.py` | Subprocess replay tracing with disk cache                                |


## GitHub Integration


| File                     | Role                                                                           |
| ------------------------ | ------------------------------------------------------------------------------ |
| `github_repo_service.py` | GitHub REST API: clone, branches, PRs, App/token auth, installation management |
| `github_oauth.py`        | OAuth login URL generation and code exchange                                   |
| `session_store.py`       | JSON-backed session and installation persistence                               |


## Async Jobs


| File                        | Role                                                            |
| --------------------------- | --------------------------------------------------------------- |
| `async_jobs.py`             | In-memory + JSON-file job manager with thread-based workers     |
| `async_optimize_worker.jac` | Standalone Jac entry point for subprocess worker execution      |
| `worker_runner.py`          | Subprocess invocation of the Jac worker with JSON request files |
| `run_registry.py`           | Merges run logs + async job store for "latest run" queries      |


## Repo Agent


| File                | Role                                                                  |
| ------------------- | --------------------------------------------------------------------- |
| `repo_agent.py`     | High-level repo workflow: clone, rank, fan-out optimize, validate, PR |
| `repo_workspace.py` | Local/Blaxel repo command execution and tree reading                  |


## Execution Environment


| File                 | Role                                                             |
| -------------------- | ---------------------------------------------------------------- |
| `sandbox_runner.jac` | Abstract execution backend with Local and Blaxel implementations |


## Support & Reporting


| File                   | Role                                                        |
| ---------------------- | ----------------------------------------------------------- |
| `product_support.py`   | Config doctor, auth readiness, recent job summaries         |
| `reporting.py`         | SVG timing charts and JSON summary artifact generation      |
| `ranked_demo_suite.py` | Demo benchmark suite catalog, runner, and progress tracking |


