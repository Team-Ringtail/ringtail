# Ringtail Project TODO

## Project Structure

```
ringtail/
├── ARCHITECTURE.md            # High-level system architecture
├── TODO.md                    # This file
├── AGENTS.md                  # Agent and LLM usage conventions
├── README.md                  # Project documentation
├── jac.toml                   # Jaseci configuration
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore patterns
├── .infisical.json            # Infisical project configuration (no secrets)
│
├── config/                    # Configuration files
│   ├── optimization_criteria.jac  # Default optimization criteria
│   └── agent_config.jac           # Agent configuration profiles
│
├── src/                       # Core application logic
│   ├── agents/
│   │   ├── __init__.jac
│   │   └── optimizer_agent.jac     # Main optimization agent (heuristic + LLM)
│   ├── core/
│   │   ├── __init__.jac
│   │   ├── optimization_loop.jac   # Main optimization loop
│   │   ├── profiler.jac            # Code profiling utilities
│   │   ├── tester.jac              # Unit testing + coverage
│   │   ├── property_tester.jac     # Hypothesis-based property testing
│   │   ├── deep_profiler.jac       # Scalene-based detailed profiling
│   │   └── sandbox_runner.jac      # Sandboxed execution utilities
│   ├── models/
│   │   ├── __init__.jac
│   │   └── types.jac               # Type definitions
│   └── utils/
│       ├── __init__.jac
│       ├── code_parser.jac         # Code parsing utilities
│       ├── complexity.jac          # Complexity analysis
│       ├── metrics.jac             # Performance metrics helpers
│       ├── llm_client.jac          # Jac Anthropic client
│       ├── llm_client.py           # Python Anthropic client
│       └── run_log.py              # JSONL run logging helper
│
├── interfaces/                # User interface implementations
│   └── cli/                   # Command-line interface (stub)
│       └── cli.jac            # CLI entry point
│
├── benchmarks/                # Benchmarking infrastructure
│   ├── run_benchmark.py       # Run LeetCode tests against a solution
│   ├── optimize_and_bench.py  # LLM optimize + benchmark pipeline
│   ├── harness/               # Benchmark harness boilerplate
│   │   └── benchmark_harness.jac
│   └── leetcode/              # LeetCode problem specs, solutions, tests
│
├── tests/                     # Test files
│   ├── unit/                  # Jac unit tests
│   └── optimization/
│       └── with_llm/          # Optional LLM-backed smoke tests
│
└── logs/                           # JSONL logs from optimization and benchmarks
    └── *.jsonl
```

## TODO List

### Phase 1: Initial Setup
- [x] Create project structure
- [x] Set up Jaseci configuration (jac.toml, requirements.txt)
- [x] Create basic app.jac entry point
- [x] Set up .gitignore and README.md

### Phase 2: Core Optimization Loop
- [x] Implement `src/core/optimization_loop.jac` with main agent loop:
  - [x] Determine function to optimize (via `FunctionInput` and `parse_function`)
  - [x] Agent think/prep phase (`think_and_prep`)
  - [x] Agent write code phase (`write_optimized_code` stubbed but wired)
  - [x] Unit test and profile for baseline and optimized code
  - [x] Compare to baseline with statistical tests (`compare_metrics`)
  - [x] Loop with convergence and stopping logic
- [x] Create `src/agents/optimizer_agent.jac` with heuristic implementation and LLM integration points
- [x] Create `src/core/profiler.jac` for code profiling
- [x] Create `src/core/tester.jac` for unit testing and coverage

### Phase 3: User Interfaces

- [ ] CLI interface (`interfaces/cli/cli.jac`)
  - [ ] Flesh out `optimize_function` walker to accept source code and options
  - [ ] Wire CLI to `run_optimization` and print summarized metrics/results
- [ ] Web interface (`interfaces/web/`) with jac-client (planned, directory not yet created)
  - [ ] Code editor component
  - [ ] Optimization criteria input
  - [ ] Results visualization
  - [ ] GitHub repo linking
- [ ] Python decorator interface (`interfaces/decorators/decorators.py`) (planned)
- [ ] GitHub integration (`interfaces/github/github_integration.jac`) (planned)

### Phase 4: Benchmarking Infrastructure

- [x] Set up LeetCode problem benchmarks (`benchmarks/leetcode/*`)
- [x] Implement benchmark runners:
  - [x] `benchmarks/run_benchmark.py` (pytest-based correctness + timing)
  - [x] `benchmarks/optimize_and_bench.py` (LLM optimize + benchmark pipeline)
- [x] Implement basic timing and speedup comparison in `optimize_and_bench.py`
- [ ] Add GitHub repository benchmarks (e.g. `benchmarks/github_repos/*`, planned)

### Phase 5: Testing & Documentation
- [x] Unit tests for core components (`src/utils/metrics.jac`, `src/utils/code_parser.jac`, `src/models/types.jac`)
- [x] Integration tests for optimization loop (`tests/unit/test_optimization_loop.jac`)
- [ ] Additional integration tests for failure modes and edge cases
- [ ] Complete README with usage examples
- [ ] API documentation

---

## Next Steps (Prioritized)

### 1. LLM‑Driven Optimization Path

- [x] Implement `_think_and_prep_llm` in `optimizer_agent.jac`:
  - Uses `src/utils/llm_client.jac::analyze_and_plan` with optional feedback + run logging.
- [x] Read API keys from environment (`RINGTAIL_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY`) via `llm_client.{jac,py}`.
- [x] Send source code, criteria, function call, and tests to the LLM and return a structured plan.
- [x] Upgrade `write_optimized_code` so that, when an `llm_model` is set and the plan contains `analysis`:
  - It calls the LLM to rewrite the code according to the plan (with fallbacks to a safe heuristic stub).
  - It preserves the public API and relies on unit + property tests as the safety net.
- [ ] Add caching / idempotent run controls for LLM calls to keep costs bounded.
- [ ] Add richer failure feedback loops from tests/property tests back into `_think_and_prep_llm`.

### 2. Named Profiles and Config Presets

- [x] Define initial `AgentConfig` profiles:
  - [x] `"default"`: heuristic-only (no LLM model configured).
  - [x] `"anthropic-sonnet"`: enables Claude Sonnet with conservative iteration limits.
- [x] Wire `config_name` in `run_optimization` to look up these profiles via `get_agent_config`.
- [ ] Add additional presets, for example:
  - [ ] `"fast-iter"`: fewer iterations, cheaper models.
  - [ ] `"quality-first"`: more iterations, stricter thresholds, higher‑quality models.
- [ ] Add matching `OptimizationCriteria` presets and a `criteria_name` lookup helper.

### 3. Observability and Run Logs

- [x] Extend run logging (Jac + Python) to record per‑iteration:
  - [x] Metrics and improvement ratios (`run_log.optimization_step`).
  - [x] Agent `signal` and `reason`.
  - [x] Chosen profile and LLM model.
  - [x] Test coverage and property‑test status.
- [x] Emit JSONL traces per run via `src/utils/run_log.py` (used by both `optimization_loop.jac` and `benchmarks/optimize_and_bench.py`).
- [ ] Add higher-level summaries (e.g. `runs.jsonl` aggregation, benchmark leaderboards).

### 4. Deep Diagnostics and Multi‑Agent Analysis

- [x] Implement `deep_profile` in `src/core/deep_profiler.jac` with unit tests.
- [ ] Expose `deep_profile` through CLI/web for on‑demand hotspot analysis.
- [ ] Add a dedicated analysis agent that:
  - [ ] Consumes deep profile, complexity, and coverage data.
  - [ ] Suggests algorithmic changes or refactors beyond simple micro‑optimizations.

### 5. Interfaces and Benchmarks

- [ ] Flesh out CLI, web, decorator, and GitHub interfaces as described above.
- [x] Stand up benchmark harness and a curated suite of LeetCode targets to compare:
  - [x] Baseline LeetCode solutions vs LLM‑optimized versions (via `optimize_and_bench.py`).
  - [ ] Single strong LLM vs future multi‑agent workflows.
  - [ ] Different optimization criteria/config profiles.

## Key Features to Implement

### Agent Loop Workflow
1. **Determine** what function to optimize
2. **Think/Prep**: Agent analyzes and estimates best optimization
3. **Write**: Agent generates optimized code
4. **Test**: Unit test the optimized code
5. **Profile**: Analyze performance metrics
6. **Compare**: Check against estimated limit
7. **Iterate**: Loop back if not satisfactory

### Optimization Criteria
- Performance (execution time, memory usage)
- Code quality (readability, maintainability)
- Functionality (correctness via unit tests)

### User Interfaces
- **CLI**: Direct function optimization from command line
- **Web**: Paste function, define criteria, view results
- **Decorator**: `@optimize` decorator for Python functions
- **GitHub**: Batch optimization for repositories

## Notes
- Using Jaseci full-stack framework (jaclang, byllm, jac-client)
- Leveraging Meaning Typed Programming for agent reasoning
- Graph-based Object-Spatial Programming for state management
