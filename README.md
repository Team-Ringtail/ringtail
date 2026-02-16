# Ringtail

AI agent-based code optimizer that iteratively improves code through think-prep-write-test-profile loops.

## Overview

Ringtail is an intelligent code optimization system that uses AI agents in an iterative loop to improve code quality, performance, and maintainability. The system analyzes your code, generates optimized versions, validates them through unit testing and profiling, and iterates until optimal results are achieved.

### Optimization Loop

1. **Determine** what function to optimize
2. **Think/Prep**: Agent analyzes and estimates best optimization
3. **Write**: Agent generates optimized code
4. **Test**: Unit test the optimized code
5. **Profile**: Analyze performance metrics
6. **Compare**: Check against estimated limit
7. **Iterate**: Loop back if not satisfactory

## Features

- Support for functions, codebases, and entire repositories
- Define custom optimization criteria (performance, code quality, functionality)
- Unit testing to ensure functionality
- Profiling to analyze performance
- Compare metrics to standalone agents (Claude, GPT-4, etc.)
- Multiple interfaces: CLI, web UI, decorators, GitHub integration
- Benchmarking against GitHub repositories and LeetCode problems

## Requirements

- Python 3.12 or higher
- Virtual environment (recommended)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ringtail
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Jaseci, which includes all required plugins (jaclang, byllm, jac-client, jac-scale, jac-super).

### 4. Verify Installation

```bash
jac --version
```

## Quick Start

### Start the Development Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
jac start main.jac
```

The server will start on `http://localhost:8000` by default.

### Access the Application

Open your browser and navigate to http://localhost:8000/


## Project Structure

```
ringtail/
├── main.jac                    # Main application entry point
├── jac.toml                    # Jaseci project configuration
├── requirements.txt            # Python dependencies
├── styles.css                  # Client-side CSS styles
├── README.md                   # This file
├── todo.md                     # Development TODO and progress
├── .gitignore                  # Git ignore patterns
│
├── src/                        # Core application logic
│   ├── agents/                 # Agent implementations
│   │   ├── optimizer_agent.jac    # Main optimization agent
│   │   └── analysis_agent.jac     # Code analysis agent
│   ├── core/                   # Core optimization logic
│   │   ├── optimization_loop.jac  # Main optimization loop
│   │   ├── profiler.jac           # Code profiling utilities
│   │   └── tester.jac             # Unit testing utilities
│   ├── models/                 # Data models and types
│   │   └── types.jac              # Type definitions
│   └── utils/                  # Utility functions
│       ├── code_parser.jac        # Code parsing utilities
│       └── metrics.jac            # Performance metrics
│
├── interfaces/                 # User interface implementations
│   ├── cli/                    # Command-line interface
│   │   └── cli.jac                 # CLI entry point
│   ├── web/                    # Web interface (jac-client)
│   │   ├── components/             # React-like components
│   │   └── pages/                  # Page components
│   ├── decorators/             # Python decorator interface
│   │   └── decorators.py          # Python decorator implementation
│   └── github/                 # GitHub integration
│       └── github_integration.jac
│
├── benchmarks/                 # Benchmarking infrastructure
│   ├── leetcode/               # LeetCode problem benchmarks
│   ├── github_repos/           # GitHub repository benchmarks
│   ├── harness/               # Benchmark harness boilerplate
│   │   └── benchmark_harness.jac
│   └── metrics/                # Benchmark metrics and comparison
│       └── comparison.jac
│
├── tests/                      # Test files
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
│
└── config/                     # Configuration files
    ├── optimization_criteria.jac  # Default optimization criteria
    └── agent_config.jac           # Agent configuration
```

## Configuration

### Environment Variables

For AI features, set LLM API keys:

```bash
export ANTHROPIC_API_KEY="your-key-here"
# or
export OPENAI_API_KEY="your-key-here"
```

## API Endpoints

When running `jac start main.jac`, the following endpoints are automatically available:

### Health Check
- **GET** `/health` - Returns service health status and version

### Test Endpoints
- **GET** `/hello?name=Ringtail` - Test endpoint with personalized greeting
- **POST** `/walker/test_walker` - Demonstrates graph traversal capabilities

### Planned Endpoints
- **POST** `/optimize` - Optimize a function or codebase
- **GET** `/optimization/{id}` - Get optimization status
- **POST** `/benchmark` - Run benchmark comparison

## Development

### Running in Development Mode

```bash
# Start with hot module replacement
jac start main.jac --dev

# Start on custom port
jac start main.jac --port 3000
```

### Common Commands

```bash
# Type check code
jac check main.jac

# Format code
jac format main.jac

# Run tests
jac test
```

## Troubleshooting

**Bytecode cache errors:**
```bash
jac purge
```

**Port already in use:**
```bash
jac start main.jac --port 8001
```

**Always activate virtual environment:**
```bash
source venv/bin/activate
```

## Contributing

See `TODO.md` for current development progress and TODO items.

## License

TODO
