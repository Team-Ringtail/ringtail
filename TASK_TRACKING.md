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

### Lance — Loop orchestration

- [ ] Implement `src/core/optimization_loop.jac`
  - [ ] Determine function to optimize (entry point, input parsing)
  - [ ] Orchestrate the full loop: think → write → test → profile → compare → iterate
  - [ ] Compare profiler result to estimated limit and decide whether to loop
  - [ ] Define termination / convergence criteria
- [ ] Implement `src/models/types.jac` — shared data models used across the loop
- [ ] Wire `src/utils/code_parser.jac` and `src/utils/metrics.jac` as needed

### GM — Agent and LLM integration

- [ ] Implement `src/agents/optimizer_agent.jac` with byllm integration
  - [ ] Think/prep phase: agent analyzes function and estimates best optimization approach
  - [ ] Write phase: agent generates optimized code from analysis
  - [ ] Hook into `optimization_loop.jac` think and write steps
- [ ] Define and document the agent's input/output interface so Lance can integrate it into the loop

**Notes / blockers:**
- Profiler and tester (Colin) are dependencies — coordinate on interfaces early
- GM should define the agent interface before Lance wires the loop so both sides stay in sync

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

**Goal:** Implement the profiling and unit testing utilities that the optimization loop relies on to evaluate whether an optimized solution is correct and performant.

### Tasks

- [ ] Implement `src/core/profiler.jac`
  - [ ] Measure execution time
  - [ ] Measure memory usage
  - [ ] Return structured metrics compatible with `src/utils/metrics.jac`
- [ ] Implement `src/core/tester.jac`
  - [ ] Run unit tests against optimized code
  - [ ] Return pass/fail with error details
  - [ ] Support test case injection from benchmark harness
- [ ] Unit tests for profiler and tester (`tests/unit/`)

**Notes / blockers:**
- These are blocking for the optimization loop — prioritize getting a working interface defined even if the full implementation follows later
