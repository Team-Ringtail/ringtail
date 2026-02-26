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
  - Creates an `OptimizationCriteria` and `AgentConfig` (today effectively using a `"default"` profile, but accepting names for future profile selection).
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
    - Future: LLM analysis (`_think_and_prep_llm`) when `analysis_mode == "llm"` or `llm_model` is set.
  - Returns the plan: targets, steps, and optionally extra tests.

- **`write_optimized_code(source_code, plan) -> str`**
  - **Purpose**: apply the plan and return new code.
  - Today: only prepends a comment summarizing the plan (stub) so the loop wiring can be exercised safely.
  - **Intended direction**: call out to an **LLM to rewrite the code**, using the plan (and future analysis agents) as context.

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

- **`OptimizationCriteria`**
  - What we value:
    - `performance_weight`
    - `code_quality_weight`
    - `functionality_weight`

In the future, `criteria_name` and `config_name` will select different **named profiles**:

- Example:
  - `"cheap-llm"` → few iterations, smaller model, relaxed thresholds.
  - `"deep-optimization"` → more iterations, stronger model, stricter thresholds.

---

## LLM Integration and API Keys

- **Goal**: most of the “optimization work” (planning and rewriting) should be done by an LLM.
- **Where LLMs plug in**:
  - `_think_and_prep_llm` in `optimizer_agent.jac` (planning).
  - `write_optimized_code` (rewriting) when an LLM is configured.
- **Key management**:
  - No secrets in code; keys come from environment variables, typically populated by Infisical:
    - `RINGTAIL_OPENAI_API_KEY`
    - `RINGTAIL_ANTHROPIC_API_KEY`
  - This is documented in `AGENTS.md`.

---

## Next Steps (Focused)

### 1. Make `write_optimized_code` LLM‑driven

- Implement `_think_and_prep_llm`:
  - Use environment variables (via Infisical) for credentials.
  - Send the function code, parsed metadata, criteria, and existing tests to an LLM.
  - Return a structured `OptimizationPlan` with concrete steps and optional new tests.
- Update `write_optimized_code` so that, when an `llm_model` is set:
  - It calls the LLM with the original code + plan.
  - Returns an actual rewritten code string that preserves the public API.
  - Relies on the existing tester/profiler loop (including property tests) to validate changes.

### 2. Define practical named profiles

- Add a small set of `AgentConfig` / `OptimizationCriteria` profiles:
  - Example:
    - `"fast-iter"`: fewer iterations, lower LLM cost.
    - `"quality-first"`: more iterations, higher model quality, higher thresholds.
- Wire `criteria_name` and `config_name` in `run_optimization` to look up these profiles.

### 3. Improve observability

- Record per‑iteration:
  - Metrics and improvement ratios.
  - Agent `signal` and `reason`.
  - Profile name and LLM model used.
  - Test coverage and property‑test status.
- Optionally, emit a JSONL trace per run for debugging and benchmarking.

### 4. Deep diagnostics and multi‑agent analysis

- Expose `deep_profile` in higher‑level interfaces (CLI, web) for on‑demand hotspot analysis.
- Consider a dedicated **analysis agent** that:
  - Consumes deep‑profiling, complexity, and coverage data.
  - Suggests targeted refactorings or algorithm swaps beyond raw speedups.
- Keep the architecture simple: the loop orchestrates, optimizer/analysis agents propose changes, and tests/profilers keep everything honest.

