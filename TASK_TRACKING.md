# Ringtail — Task Tracking

Team assignments and status for the first implementation phase.
See [todo.md](todo.md) for the full project TODO and project structure.

---

## Work Streams

| Work Stream            | Owner(s)   | Status      |
|------------------------|------------|-------------|
| Agent optimization loop | GM, Lance  | Not started |
| LeetCode benchmarks    | Shiva      | Not started |
| CLI / interfaces       | Julian     | Not started |
| Profiler and tester    | Colin      | Not started |

---

## Agent Optimization Loop

**Owners:** GM, Lance

**Goal:** Implement the core agent loop that takes a function, optimizes it iteratively, and validates correctness and performance.

### Lance — Loop shell, data models, and I/O

- [ ] Implement `src/models/types.jac` — shared data models (function input, result, metrics) used by both sides
- [ ] Implement `src/core/optimization_loop.jac`
  - [ ] Entry point: accept target function and optimization criteria
  - [ ] Outer loop skeleton: call into GM's analyze/write steps, then call profiler/tester
  - [ ] Termination / convergence logic: decide when to stop iterating
  - [ ] Return and format final optimized result
- [ ] Wire `src/utils/code_parser.jac` (parse input function) and `src/utils/metrics.jac` (aggregate metrics)

### GM — Analysis and transformation pipeline

- [ ] Implement `src/agents/optimizer_agent.jac` (no byllm for now — stub or heuristic-based)
  - [ ] Think/prep phase: analyze the input function and produce an optimization plan/estimate
  - [ ] Write phase: apply or generate the optimized code based on the plan
  - [ ] Compare phase: evaluate profiler output against the estimated target, return continue/done signal
- [ ] Define and document the `optimizer_agent` interface (inputs/outputs) so Lance can wire it into the loop shell

**Notes / blockers:**
- byllm integration is deferred — GM should implement think/write/compare with stubs or simple heuristics first
- Profiler and tester (Colin) are dependencies — coordinate on the result/metrics interface early
- Lance should not start wiring the loop until GM has a working interface definition

---

## LeetCode Benchmarks

**Owner:** Shiva

**Goal:** Build a set of LeetCode problems as benchmark inputs so the optimization loop can be evaluated against known problems with known complexity limits.

### Tasks

- [ ] Set up benchmark harness (`benchmarks/harness/benchmark_harness.jac`)
- [ ] Implement metrics comparison (`benchmarks/metrics/comparison.jac`)
- [ ] Add initial LeetCode problem benchmarks (`benchmarks/leetcode/`)
  - [ ] Select a representative set of problems (e.g. easy/medium/hard across categories)
  - [ ] Provide reference (unoptimized) solutions as inputs
  - [ ] Define expected output / correctness criteria for each problem
- [ ] Validate benchmarks run end-to-end against the optimization loop

**Notes / blockers:**
- Depends on optimization loop and profiler being partially functional to run full benchmarks

### Next steps (in order)

1. **Record your problem subset** — Add the problems you’ve chosen to `benchmarks/leetcode/PROBLEMS.md` (or the table in `benchmarks/leetcode/README.md`) so the set is fixed and reproducible.
2. **Define one problem end-to-end** — Use the existing example `two_sum`: reference solution, pytest-based tests, and a small spec (id, difficulty, expected complexity). This is the template for every other problem.
3. **Run the harness on one benchmark** — From repo root: `python benchmarks/run_benchmark.py two_sum` (or equivalent). Confirm it runs the reference solution, reports pass/fail and timing, and exits 0.
4. **Implement metrics comparison** — Implement `benchmarks/metrics/comparison.jac` (or a small Python helper) to compare before/after metrics (correctness, time, memory) so the optimization loop can decide “better/same/worse”.
5. **Add more problems** — For each problem in your subset, add a folder under `benchmarks/leetcode/<slug>/` with the same shape as `two_sum`, then run the full benchmark suite.
6. **Integrate with the loop** — Once the optimization loop and profiler exist, wire the harness so the loop can run a benchmark before/after optimization and use the comparison result.

---

## CLI / Interfaces

**Owner:** Julian

**Goal:** Provide a CLI entrypoint so the team can trigger optimization runs locally during development and testing.

### Tasks

- [ ] Implement `interfaces/cli/cli.jac`
  - [ ] Accept a target file/function as input
  - [ ] Accept optimization criteria as flags or config
  - [ ] Display optimization loop progress and results
  - [ ] Output optimized code to stdout or file
- [ ] Python decorator interface (`interfaces/decorators/decorators.py`)
- [ ] GitHub integration (`interfaces/github/github_integration.jac`)
- [ ] Web interface (`interfaces/web/`) — lower priority for first steps
  - [ ] `CodeEditor.jac`
  - [ ] `OptimizationPanel.jac`
  - [ ] `ResultsView.jac`
  - [ ] `MainPage.jac`

**Notes / blockers:**
- CLI depends on core optimization loop being callable; agree on the call interface early

---

## Profiler and Tester

**Owner:** Colin

**Goal:** Implement production-grade profiling and testing utilities with statistical rigor, deep per-line analysis, automated test generation, and isolated sandbox execution.

### Phase 1: Statistical Profiling Hardening — DONE

- [x] Warmup iterations to eliminate cold-start bias
- [x] IQR-based outlier filtering
- [x] Stdev, mean, 95% confidence intervals in profiler output
- [x] Welch's t-test significance testing in `compare_metrics`

### Phase 2: Deep Profiling (Scalene) — DONE

- [x] `src/core/deep_profiler.py` — per-line CPU + memory via Scalene subprocess
- [x] `LineProfile` and `DetailedProfile` dataclasses in `src/models/types.py`
- [x] Hotspot extraction (top N lines by CPU %)

### Phase 3: Code Complexity Analysis — DONE

- [x] `src/utils/complexity.py` — AST-based cyclomatic complexity
- [x] Max nesting depth, LOC, function count
- [x] Populates `Metrics.code_complexity` in the optimization loop

### Phase 4: Coverage-Integrated Testing — DONE

- [x] `run_tests_with_coverage` in `src/core/tester.jac`
- [x] `coverage.py` integration for line coverage percentage
- [x] Populates `Metrics.test_coverage` in the optimization loop

### Phase 5: Property-Based Testing (Hypothesis) — DONE

- [x] `src/core/property_tester.py` — auto-generate tests from type annotations
- [x] Reference comparison mode: assert `optimized == original` across all inputs
- [x] Strategy mapping for standard Python types

### Phase 6: Blaxel Sandbox Execution — DONE

- [x] `src/core/sandbox_runner.py` — `ExecutionBackend` abstraction
- [x] `LocalBackend` (subprocess) and `BlaxelBackend` (microVM)
- [x] `config/blaxel_config.py` — reads from env vars (Infisical)
- [ ] Infisical setup for `BL_API_KEY` (Colin — in progress)

### Phase 7: Data Model and Metrics Updates — DONE

- [x] `ProfileResult`, `LineProfile`, `DetailedProfile` dataclasses
- [x] `calculate_score` uses real complexity + coverage, baseline-relative perf scoring
- [x] Memory penalty in scoring

### Phase 8: Optimization Loop Wiring — DONE

- [x] Baseline complexity measurement
- [x] `run_tests_with_coverage` replaces `run_tests` in the loop
- [x] Property-based testing against original code each iteration
- [x] Statistical significance gate in convergence logic

### Phase 9: Tests — DONE

- [x] `test_statistical_profiler.py` — warmup, stdev, CI, outlier fields
- [x] `test_complexity.py` — cyclomatic complexity on various code shapes
- [x] `test_deep_profiler.py` — Scalene JSON parsing, error handling
- [x] `test_coverage_tester.py` — coverage fields, partial coverage, timeouts
- [x] `test_property_tester.py` — strategy generation, reference comparison, buggy detection
- [x] `test_sandbox_runner.py` — LocalBackend, Blaxel env check
- [x] Updated `test_profiler.jac`, `test_tester.jac`, `test_metrics.py`, `test_types.py`

**Notes / blockers:**
- Infisical secret management setup is in progress (Colin)
- Scalene requires `pip install scalene` in the test/CI environment
- Deep profiler (Scalene) is optional; the loop works without it using the statistical profiler
