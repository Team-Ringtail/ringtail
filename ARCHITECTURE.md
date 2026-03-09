## Ringtail Architecture (High Level)

Ringtail is a **Jac/Jaseci-based system for automated code optimization**.

- You give it **Python source code**, a **function call**, and optional **tests**.
- Ringtail runs the code in isolated Python subprocesses to **profile**, **test**, and **cross-check** it.
- An **optimizer agent** (heuristic now, LLM‑driven later) proposes improvements.
- A central **optimization loop** applies the agent’s changes, re‑profiles, re‑tests (including property‑based tests), and decides when to stop.

The core idea: **let an LLM (or other agents) do the optimization work, while Ringtail handles safety, tests, metrics, and iteration.**

---

## Key Terminology

- **Function input** (`FunctionInput`):  
  A dict describing what to optimize:
  - `source_code`: the code containing the target function.
  - `function_call`: how to invoke it in Python (e.g. `"slow_sum(10)"`).
  - Optional: `function_name`, `language`, `test_cases`, `analysis_mode`, `extra`.

- **Metrics** (`Metrics`):  
  Runtime, memory, and quality data derived from profiling and analysis:
  - Core: `execution_time`, `memory_usage`.
  - Optional: `cpu_usage`, `code_complexity`, `test_coverage`.

- **Optimization plan** (`OptimizationPlan`):  
  The agent’s plan for improving the code:
  - Performance targets (e.g. `estimated_time_sec`).
  - Heuristic features (lines of code, number of loops).
  - Human‑readable `steps` and optional extra test cases.

- **Optimization result** (`OptimizationResult`):  
  What `run_optimization` returns:
  - `optimized_code`, `iteration_number`, `metrics`, `test_passed`, `improvement_ratio`.
  - Plus optional `baseline_metrics`, `termination_reason`, `converged`, `error`.
  - The loop may also attach convenience fields such as `is_significant` and `confidence` from metric comparison.

- **Agent**:  
  The “brain” that analyzes code and suggests changes:
  - Today: simple heuristics.
  - Future: LLM‑backed analysis and code generation.

- **Property tests**:  
  Hypothesis‑based tests that automatically generate many inputs and, when given both baseline and optimized implementations, assert they behave identically.

- **Deep profile** (`DetailedProfile`):  
  Per‑line CPU and memory data (via Scalene) that highlight hotspots and how much time is spent in Python vs native code. Used for **targeted deep dives**, not every optimization loop.

- **Named profiles**:  
  Short names for **configuration bundles**:
  - `criteria_name` → which `OptimizationCriteria` to use (what to optimize for).
  - `config_name` → which `AgentConfig` to use (how aggressively to run the loop, which LLM model, etc.).
  - Example (future): `"cheap-llm"` vs `"deep-optimization"`.

- **Criteria vs config**:
  - `OptimizationCriteria`: weights for performance vs code quality vs functionality.
  - `AgentConfig`: loop policy (iterations, thresholds, stop rules, LLM model, temperature).

---

## Main Pieces and Their Roles

### 1. Core Loop (`src/core/optimization_loop.jac`)

- **`run_optimization(input, criteria_name?, config_name?) -> dict`**
  - Public entrypoint.
  - Creates an `OptimizationCriteria` and selects an `AgentConfig` profile via `config_name` (default `"default"`), using `config.get_agent_config`.
  - Calls `_run_optimize(input, criteria, config)` and returns its final `OptimizationResult`‑shaped dict.
  - **Design decision**: keep this function small and stable so callers don’t need to know about internals.

- **`_run_optimize(function_input, criteria, config) -> dict`**
  - The **central orchestration function**:
  - Reads loop settings from `config`:
    - `max_iterations`, `max_no_improvement_iters`.
    - `stop_on_test_failure`, `min_improvement_ratio`.
    - `llm_model` (which LLM to use when enabled).
  - Validates and parses the function:
    - Uses `parse_function(source_code, language)` to infer `function_name` if needed.
    - Ensures `function_call` is present; otherwise returns an error result.
  - Profiles the baseline with `profile_code`, then:
    - Computes baseline **complexity metrics** with `compute_complexity`.
    - Captures standard deviation and sample size from pytest‑benchmark for later **significance testing**.
    - Builds a `Metrics` object + plain dict (`baseline_metrics_obj` / `baseline_metrics`).
  - Runs the **iteration loop**:
    1. Calls the agent to **plan** (`think_and_prep`).
    2. Calls the agent to **write optimized code** (`write_optimized_code`).
    3. **Generates tests** from user + agent test cases, then:
       - Runs unit tests with coverage (`run_tests_with_coverage`) to enforce correctness and measure `test_coverage`.
       - Runs **property‑based tests** (`run_property_tests`) against the original implementation to catch semantic regressions.
    4. Profiles the optimized code (`profile_code`) and recomputes complexity.
    5. Builds current `Metrics`, then compares baseline vs optimized metrics with `compare_metrics`, including **Welch‑style significance** (`is_significant`, `confidence`).
    6. Asks the agent if we should continue or stop (`compare`).
    7. Applies stopping rules from `AgentConfig` + the agent’s signal and tracks **no‑improvement streaks**.
  - Returns a single final result:
    - Last iteration’s metrics and code.
    - Baseline metrics and why the loop stopped.

**Key design decision**:  
_The loop never “thinks” about optimization details; it only orchestrates agents, tests, profiling, and metrics._

---

### 2. Optimizer Agent (`src/agents/optimizer_agent.jac`)

The optimizer agent is where “intelligence” lives. The loop passes it:

- The current source code.
- Optimization criteria.
- A function call.
- Test cases.
- Configuration hints (`analysis_mode`, `llm_model`).

The agent returns:

- A plan (`OptimizationPlan`‑shaped dict).
- New optimized code.
- A convergence signal.

Public functions:

- **`think_and_prep(source_code, criteria, function_call, test_cases, analysis_mode?, llm_model?) -> dict`**
  - Chooses between:
    - Heuristic analysis (`_analyze_and_plan`).
    - LLM-backed analysis (`_think_and_prep_llm`) when `analysis_mode == "llm"` or `llm_model` is set, implemented via `src/utils/llm_client.jac::analyze_and_plan`.
  - Returns the plan: targets, steps, and optionally extra tests.

- **`write_optimized_code(source_code, plan, llm_model?) -> str`**
  - **Purpose**: apply the plan and return new code.
  - When the plan contains an `analysis` field (indicating an LLM-originated plan), calls `src/utils/llm_client.jac::generate_optimized_code` to rewrite the code.
  - Otherwise, or on any LLM failure, falls back to a safe heuristic stub that prepends a comment summarizing the plan.

- **`compare(profiler_metrics, plan) -> dict`**
  - Looks at actual performance vs target (time, etc.).
  - Returns `{"signal": "continue" | "done", "reason": str}`.
  - The loop uses this to help decide when to stop, alongside its own convergence rules.

**Key design decision**:  
_Long‑term, both planning and code rewriting should be LLM‑driven; the heuristic version is just a safe starting point._

---

### 3. Testing and Profiling (`src/core/tester.jac`, `src/core/property_tester.jac`, `src/core/profiler.jac`, `src/core/deep_profiler.jac`)

- **Tester (`run_tests`, `run_tests_with_coverage`)**
  - Writes:
    - `solution.py` with the (baseline or optimized) code.
    - `test_solution.py` with pytest tests generated from structured test cases.
  - Runs `pytest` in a subprocess.
  - Parses output into a structured result dict:
    - `passed`, `total`, `passed_count`, `failed_count`, `failures`, `error`.
  - With coverage enabled (`run_tests_with_coverage`), also parses a `coverage.json` report:
    - `coverage_percent`, `covered_lines`, `missing_lines`.
  - The loop uses this to:
    - Enforce correctness before accepting any optimization.
    - Track **test coverage** as part of `Metrics`.
    - Decide whether test failures should stop the loop (`stop_on_test_failure`).

- **Property‑based tester (`run_property_tests`)**
  - Uses Hypothesis to auto‑generate inputs from **type annotations**.
  - When provided both original and optimized implementations:
    - Asserts they produce equivalent outputs (with float‑aware comparison).
    - Surfaces falsifying examples when behavior diverges.
  - Treated as an additional **correctness gate** before accepting an iteration.

- **Profiler (`profile_code`)**
  - Writes the code and a small pytest‑benchmark harness to a temp directory.
  - Measures:
    - Execution time over multiple iterations using pytest‑benchmark statistics (median, mean, stdev, IQR, percentiles, rounds, outliers).
    - Peak memory via `tracemalloc`.
  - Returns a rich dict (`ProfileResult`‑shaped) that the loop converts into `Metrics` and feeds into `compare_metrics`.

- **Deep profiler (`deep_profile`)**
  - Uses Scalene to collect **per‑line CPU and memory** data.
  - Produces a `DetailedProfile`:
    - Line‑level `LineProfile` entries with CPU %, memory MB, and Python‑vs‑native fraction.
    - A small set of hottest lines for quick inspection.
  - Intended for **manual or targeted investigations** of hotspots rather than every optimization run (it is heavier and requires Scalene).

**Key design decision**:  
_All user code (baseline and optimized) runs in **separate Python subprocesses**, keeping Jac safe and focused on orchestration. Testing, property testing, and profiling are all externalized into subprocesses with structured summaries._

---

### 4. Parsing, Complexity, and Metrics Utilities

- **Code parser (`src/utils/code_parser.jac`)**
  - `parse_function(source_code, language)`:
    - For Python: uses `ast` to find function definitions, parameters, docstrings, and simple structural metadata.
    - For other languages: falls back to a regex‑based parser.
  - This is the main **language‑awareness hook** for the loop and future agents.

- **Complexity analyzer (`src/utils/complexity.jac`)**
  - `compute_complexity(source_code)`:
    - Uses **radon** when available to compute cyclomatic complexity, maintainability index, LOC, and function counts.
    - Falls back to a lightweight AST‑based estimator when radon is not installed.
  - Feeds `code_complexity` and related fields into `Metrics` so the system can reason about **code quality**, not just speed.

- **Metrics helpers (`src/utils/metrics.jac`)**
  - Work with `Metrics` objects and lists.
  - Provide:
    - Aggregation across runs (`aggregate_metrics`).
    - Statistical comparison (`compare_metrics`) between baseline and optimized runs:
      - Computes `improvement_ratio`, time and memory deltas.
      - Uses a Welch‑style t‑test approximation to set `is_significant` and `confidence`.
    - A weighted scoring function (`calculate_score`) that combines performance, complexity, and test coverage using `OptimizationCriteria`.

---

### 5. Configuration and Profiles (`config/*.jac`)

- **`AgentConfig`**
  - Loop behavior and LLM usage:
    - `max_iterations`, `max_no_improvement_iters`.
    - `stop_on_test_failure`, `min_improvement_ratio`.
    - `llm_model`, `temperature`.
  - Named profiles are created via `config.get_agent_config(name)`:
    - `"default"`: heuristic-only (no LLM model configured).
    - `"anthropic-sonnet"`: enables LLM-backed planning and codegen with a Claude Sonnet model and conservative iteration limits.

- **`OptimizationCriteria`**
  - What we value:
    - `performance_weight`
    - `code_quality_weight`
    - `functionality_weight`

---

### 6. Interfaces and Benchmarks

- **CLI (`interfaces/cli/cli.jac`)**
  - Currently a stub `walker optimize_function` that will become the Jac entrypoint for local optimization runs.
  - Planned responsibilities:
    - Read a function (or file) from disk/stdin.
    - Construct a `FunctionInput` dict.
    - Call `run_optimization` and print a summarized result.

- **LeetCode benchmarks (`benchmarks/`)**
  - `benchmarks/run_benchmark.py`:
    - Discovers problems under `benchmarks/leetcode/*`.
    - Runs their pytest suites, optionally against an alternative solution via `BENCHMARK_SOLUTION`.
    - Outputs JSON with per‑problem pass/fail and timing.
  - `benchmarks/optimize_and_bench.py`:
    - Uses `RunLog` and the Python `llm_client` to:
      - Call Anthropic Claude (`analyze_and_plan`, `generate_optimized_code`) on each LeetCode solution.
      - Run tests locally or in a Blaxel sandbox.
      - Time baseline vs optimized implementations and compute speedups.
    - Emits a structured JSONL log per run in `logs/`.

---

## LLM Integration, Tests, and API Keys

- **Goal**: most of the “optimization work” (planning and rewriting) should be done by an LLM, with heuristics as a safe fallback.
- **Where LLMs plug in (current implementation)**:
  - `_think_and_prep_llm` in `optimizer_agent.jac` (planning):
    - Calls `src/utils/llm_client.jac::analyze_and_plan` when `analysis_mode == "llm"` or `AgentConfig.llm_model` is set (e.g. `"anthropic-sonnet"`).
    - Falls back to a heuristic plan on any LLM error, while logging the failure via `RunLog` when available.
  - `write_optimized_code` in `optimizer_agent.jac` (rewriting):
    - Calls `src/utils/llm_client.jac::generate_optimized_code` when the plan includes an `analysis` field (LLM-originated plan).
    - Falls back to a stub `_apply_plan_to_code` that prepends a comment when LLM codegen fails or when the plan is heuristic.
  - Python benchmarking pipeline (`benchmarks/optimize_and_bench.py`):
    - Uses `src/utils/llm_client.py` directly for LeetCode problems, with full logging to `RunLog`.
- **Key management**:
  - No secrets in code; keys come from environment variables, typically populated by Infisical:
    - `RINGTAIL_OPENAI_API_KEY`
    - `RINGTAIL_ANTHROPIC_API_KEY`
  - This is documented in `AGENTS.md` and enforced by `src/utils/llm_client.{jac,py}`.
- **Test layout for LLM usage**:
  - Default Jac tests: `jac test tests/unit/` — fast, deterministic, and do not require any LLM or external services.
  - Optional LLM-backed tests live under `tests/optimization/with_llm/` and exercise planning, codegen, and end-to-end optimization with real LLM calls when run explicitly by developers.

---

## Current State Summary

- The **core optimization loop** (`run_optimization` / `_run_optimize`) is fully implemented and wired to:
  - Profile baseline code, compute complexity, and derive structured `Metrics`.
  - Call the optimizer agent (`think_and_prep`, `write_optimized_code`, `compare`) each iteration.
  - Generate pytest test code from structured test cases and run both unit tests with coverage and property‑based tests.
  - Perform statistical comparison of baseline vs optimized runs and apply convergence logic based on `AgentConfig` and the agent’s signal.
- The **metrics utilities**, **parser**, **complexity analyzer**, **tester**, **profiler**, **deep profiler**, property‑based tester, and **type models** are implemented and covered by Jac unit tests.
- The **optimizer agent** supports both heuristic and LLM-backed workflows:
  - Heuristic mode is the default (`AgentConfig` `"default"` with no `llm_model`), used in unit tests to avoid external dependencies.
  - LLM mode is enabled by profiles such as `"anthropic-sonnet"`, which configure `llm_model` and rely on `llm_client` for planning and codegen, with robust fallbacks when LLM calls fail.
- A **Python benchmarking pipeline** (`benchmarks/run_benchmark.py`, `benchmarks/optimize_and_bench.py`) plus a suite of **LeetCode benchmarks** are in place to compare baseline vs LLM‑optimized solutions, log runs to JSONL under `logs/`, and quantify speedups.

