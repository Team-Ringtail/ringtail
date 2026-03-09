# Ringtail Project TODO

## Project Structure

```
ringtail/
├── app.jac                    # Main application entry point
├── jac.toml                   # Jaseci configuration
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Git ignore patterns
│
├── src/                       # Core application logic
│   ├── agents/                # Agent implementations
│   │   ├── optimizer_agent.jac    # Main optimization agent
│   │   └── analysis_agent.jac     # Code analysis agent
│   ├── core/                  # Core optimization logic
│   │   ├── optimization_loop.jac  # Main optimization loop
│   │   ├── profiler.jac           # Code profiling utilities
│   │   └── tester.jac             # Unit testing utilities
│   ├── models/                # Data models and types
│   │   └── types.jac              # Type definitions
│   └── utils/                 # Utility functions
│       ├── code_parser.jac        # Code parsing utilities
│       └── metrics.jac            # Performance metrics
│
├── interfaces/                # User interface implementations
│   ├── cli/                   # Command-line interface
│   │   └── cli.jac                # CLI entry point
│   ├── web/                   # Web interface (jac-client)
│   │   ├── components/            # React-like components
│   │   │   ├── CodeEditor.jac
│   │   │   ├── OptimizationPanel.jac
│   │   │   └── ResultsView.jac
│   │   └── pages/                # Page components
│   │       └── MainPage.jac
│   ├── decorators/            # Python decorator interface
│   │   └── decorators.py          # Python decorator implementation
│   └── github/                # GitHub integration
│       └── github_integration.jac
│
├── benchmarks/                # Benchmarking infrastructure
│   ├── leetcode/              # LeetCode problem benchmarks
│   ├── github_repos/          # GitHub repository benchmarks
│   ├── harness/               # Benchmark harness boilerplate
│   │   └── benchmark_harness.jac
│   └── metrics/               # Benchmark metrics and comparison
│       └── comparison.jac
│
├── tests/                     # Test files
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
│
└── config/                    # Configuration files
    ├── optimization_criteria.jac  # Default optimization criteria
    └── agent_config.jac           # Agent configuration
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
- [ ] Web interface (`interfaces/web/`) with jac-client:
  - [ ] Code editor component
  - [ ] Optimization criteria input
  - [ ] Results visualization
  - [ ] GitHub repo linking
- [ ] Python decorator interface (`interfaces/decorators/decorators.py`)
- [ ] GitHub integration (`interfaces/github/github_integration.jac`)

### Phase 4: Benchmarking Infrastructure
- [ ] Create benchmark harness (`benchmarks/harness/benchmark_harness.jac`)
- [ ] Implement metrics comparison (`benchmarks/metrics/comparison.jac`)
- [ ] Set up LeetCode problem benchmarks
- [ ] Set up GitHub repository benchmarks

### Phase 5: Testing & Documentation
- [x] Unit tests for core components (`src/utils/metrics.jac`, `src/utils/code_parser.jac`, `src/models/types.jac`)
- [x] Integration tests for optimization loop (`tests/unit/test_optimization_loop.jac`)
- [ ] Additional integration tests for failure modes and edge cases
- [ ] Complete README with usage examples
- [ ] API documentation

---

## Next Steps (Prioritized)

### 1. LLM‑Driven Optimization Path

- [ ] Implement `_think_and_prep_llm` in `optimizer_agent.jac`:
  - [ ] Read API keys from environment (`RINGTAIL_OPENAI_API_KEY`, `RINGTAIL_ANTHROPIC_API_KEY`).
  - [ ] Send source code, parsed metadata, criteria, and existing tests to the LLM.
  - [ ] Return a structured `OptimizationPlan` with concrete steps and optional new test cases.
- [ ] Upgrade `write_optimized_code` so that, when an `llm_model` is set:
  - [ ] It calls the LLM to rewrite the code according to the plan.
  - [ ] It preserves the public API and uses tests/property tests as the safety net.

### 2. Named Profiles and Config Presets

- [ ] Define a small set of `AgentConfig` / `OptimizationCriteria` presets:
  - [ ] `"fast-iter"`: fewer iterations, cheaper models.
  - [ ] `"quality-first"`: more iterations, stricter thresholds, higher‑quality models.
- [ ] Wire `criteria_name` and `config_name` in `run_optimization` to look up these profiles.

### 3. Observability and Run Logs

- [ ] Extend run logging (Jac + Python) to record per‑iteration:
  - [ ] Metrics and improvement ratios.
  - [ ] Agent `signal` and `reason`.
  - [ ] Chosen profile and LLM model.
  - [ ] Test coverage and property‑test status.
- [ ] Optionally emit a JSONL trace per run for offline analysis/benchmarking.

### 4. Deep Diagnostics and Multi‑Agent Analysis

- [ ] Expose `deep_profile` through CLI/web for on‑demand hotspot analysis.
- [ ] Add a dedicated analysis agent that:
  - [ ] Consumes deep profile, complexity, and coverage data.
  - [ ] Suggests algorithmic changes or refactors beyond simple micro‑optimizations.

### 5. Interfaces and Benchmarks

- [ ] Flesh out CLI, web, decorator, and GitHub interfaces as described above.
- [ ] Stand up benchmark harness and a small curated suite of LeetCode/GitHub targets to compare:
  - [ ] Single strong LLM vs multi‑agent workflow.
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
