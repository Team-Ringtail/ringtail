## Ringtail Architecture (High Level)

Ringtail is a **Jac/Jaseci-based system for automated code optimization**.

- You give it **Python source code**, a **function call**, and optional **tests**.
- Ringtail runs the code in isolated Python subprocesses to **profile** and **test** it.
- An **optimizer agent** (heuristic now, LLM‑driven later) proposes improvements.
- A central **optimization loop** applies the agent’s changes, re‑profiles, re‑tests, and decides when to stop.

The core idea: **let an LLM do the optimization work, while Ringtail handles safety, tests, and iteration.**

---

## Key Terminology

- **Function input** (`FunctionInput`):  
  A dict describing what to optimize:
  - `source_code`: the code containing the target function.
  - `function_call`: how to invoke it in Python (e.g. `"slow_sum(10)"`).
  - Optional: `function_name`, `language`, `test_cases`, `analysis_mode`, `extra`.

- **Metrics** (`Metrics`):  
  Runtime and memory data from the profiler:
  - `execution_time`, `memory_usage`, and optional fields like `cpu_usage`, `code_complexity`.

- **Optimization plan** (`OptimizationPlan`):  
  The agent’s plan for improving the code:
  - Performance targets (e.g. `estimated_time_sec`).
  - Heuristic features (lines of code, number of loops).
  - Human‑readable `steps` and optional extra test cases.

- **Optimization result** (`OptimizationResult`):  
  What `run_optimization` returns:
  - `optimized_code`, `iteration_number`, `metrics`, `test_passed`, `improvement_ratio`.
  - Plus optional `baseline_metrics`, `termination_reason`, `converged`, `error`.

- **Agent**:  
  The “brain” that analyzes code and suggests changes:
  - Today: simple heuristics.
  - Future: LLM‑backed analysis and code generation.

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
  - Creates an `OptimizationCriteria` and `AgentConfig` (today always using the `"default"` profile).
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
  - Profiles the baseline with `profile_code`, builds `baseline_metrics`.
  - Runs the **iteration loop**:
    1. Calls the agent to **plan** (`think_and_prep`).
    2. Calls the agent to **write optimized code** (`write_optimized_code`).
    3. **Generates tests** from user + agent test cases, then runs them (`run_tests`).
    4. Profiles the optimized code (`profile_code`).
    5. Compares baseline vs optimized metrics (`compare_metrics`).
    6. Asks the agent if we should continue or stop (`compare`).
    7. Applies stopping rules from `AgentConfig` + the agent’s signal.
  - Returns a single final result:
    - Last iteration’s metrics and code.
    - Baseline metrics and why the loop stopped.

**Key design decision**:  
_The loop never “thinks” about optimization details; it only orchestrates agents, tests, and profiling._

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
  - Today: only adds a comment summarizing the plan (stub).
  - **Intended direction**: call out to an **LLM to rewrite the code**, using the plan as context.

- **`compare(profiler_metrics, plan) -> dict`**
  - Looks at actual performance vs target (time, etc.).
  - Returns `{"signal": "continue" | "done", "reason": str}`.
  - The loop uses this to help decide when to stop.

**Key design decision**:  
_Long‑term, both planning and code rewriting should be LLM‑driven; the heuristic version is just a safe starting point._

---

### 3. Tester and Profiler (`src/core/tester.jac`, `src/core/profiler.jac`)

- **Tester (`run_tests`)**
  - Writes:
    - `solution.py` with the (optimized) code.
    - `test_solution.py` with pytest tests generated from structured test cases.
  - Runs `pytest` in a subprocess.
  - Parses output into a structured result dict:
    - `passed`, `total`, `passed_count`, `failed_count`, `failures`, `error`.
  - The loop uses this to:
    - Enforce correctness before accepting any optimization.
    - Decide whether test failures should stop the loop (`stop_on_test_failure`).

- **Profiler (`profile_code`)**
  - Writes the code and a small harness script to a temp directory.
  - Measures:
    - Execution time over multiple iterations.
    - Peak memory via `tracemalloc`.
  - Returns a dict the loop turns into a `Metrics` object.

**Key design decision**:  
_All user code (baseline and optimized) runs in **separate Python subprocesses**, keeping Jac safe and focused on orchestration._

---

### 4. Parsing and Metrics Utilities

- **Code parser (`src/utils/code_parser.jac`)**
  - `parse_function(source_code, language)`:
    - For Python: uses `ast` to find function definitions, parameters, and docstrings.
    - For other languages: falls back to a regex‑based parser.
  - This is the main **language‑awareness hook**.

- **Metrics helpers (`src/utils/metrics.jac`)**
  - Work with `Metrics` objects and lists.
  - Provide:
    - Aggregation and comparison between baseline and optimized runs.
    - A consistent `improvement_ratio` used by the loop.

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
  - Relies on the existing tester/profiler loop to validate changes.

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
- Optionally, emit a JSONL trace per run for debugging and benchmarking.

### 4. Gradual multi‑language support

- Extend `parse_function` for non‑Python languages (initially via better regexes).
- Add language‑specific tester/profiler backends selected by the `language` field in `FunctionInput`.

These steps keep the architecture simple: **the loop orchestrates, the agent (eventually LLM‑backed) optimizes, and tests/profilers keep everything honest.**

