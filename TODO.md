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
- [ ] Implement `src/core/optimization_loop.jac` with main agent loop:
  - [ ] Determine function to optimize
  - [ ] Agent think/prep phase (estimate best optimization)
  - [ ] Agent write code phase
  - [ ] Unit test and profile
  - [ ] Compare to estimated limit
  - [ ] Loop back if not satisfactory
- [ ] Create `src/agents/optimizer_agent.jac` with byllm integration
- [ ] Create `src/core/profiler.jac` for code profiling
- [ ] Create `src/core/tester.jac` for unit testing

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
- [ ] Unit tests for core components
- [ ] Integration tests
- [ ] Complete README with usage examples
- [ ] API documentation

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
