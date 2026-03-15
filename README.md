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

### Local-first install

```bash
git clone <repository-url>
cd ringtail

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

For a user-tool style install, `pipx install .` and `uv tool install .` also work once your environment has Jaseci available.

### Verify prerequisites

```bash
ringtail config doctor
```

This checks the local `jac`, `git`, and `openssl` binaries, plus the Ringtail and Blaxel env config.

## Quick Start

### 1. Set env vars

```bash
export RINGTAIL_ANTHROPIC_API_KEY="your-key-here"
export RINGTAIL_REPO_AGENT_CONFIG='{"app_id":"123456","app_slug":"your-app-slug","private_key_path":"/path/to/github-app.pem","installation_id":12345678}'
export BLAXEL_API_KEY="your-blaxel-key"
```

You normally only need:
- `RINGTAIL_REPO_AGENT_CONFIG` for Ringtail GitHub auth/config
- `BLAXEL_API_KEY` for Blaxel-backed remote execution

### 2. Start the local product

```bash
ringtail serve
```

The local UI runs at `http://localhost:8000`.

### 3. Use either surface

Web UI:
- Open `http://localhost:8000`
- Use `Repo Agent` for async repo jobs
- Use `Function Optimize` for direct file/function runs

CLI:

```bash
ringtail repo submit /path/to/repo "make this faster"
ringtail repo status <job-id>
ringtail file optimize /abs/path/to/file.py function_name --function-call "function_name(10)"
```


## Project Structure

```
ringtail/
├── main.jac                    # Main application entry point
├── jac.toml                    # Jaseci project configuration
├── pyproject.toml              # Packaged Python CLI entrypoint
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
│   ├── ringtail_cli.py         # Packaged `ringtail` CLI
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
export RINGTAIL_ANTHROPIC_API_KEY="your-key-here"
# Optional: override the shipped Anthropic model default
export RINGTAIL_DEFAULT_LLM_MODEL="claude-opus-4-6"
# Repo-agent auth/config: one env var for Ringtail
export RINGTAIL_REPO_AGENT_CONFIG='{"app_id":"123456","app_slug":"your-app-slug","private_key_path":"/path/to/github-app.pem","installation_id":12345678}'
# Or token mode:
# export RINGTAIL_REPO_AGENT_CONFIG='{"token":"your-github-token"}'
# Blaxel execution: one env var for Blaxel
export BLAXEL_API_KEY="your-blaxel-key"
```

Legacy `RINGTAIL_GITHUB_*` / `GITHUB_*` env vars still work as fallbacks, but the intended setup is now one Ringtail env plus one Blaxel env.

### Config doctor

The packaged CLI exposes a lightweight setup check:

```bash
ringtail config doctor
ringtail config doctor --json
```

Use it before demos to verify:
- local binaries (`jac`, `git`, `openssl`)
- Ringtail env config
- GitHub App install readiness
- Blaxel availability
- async jobs directory location

## API Endpoints

When running `jac start main.jac`, the following endpoints are automatically available:

### Health Check
- **GET** `/health` - Returns service health status and version

### Test Endpoints
- **GET** `/hello?name=Ringtail` - Test endpoint with personalized greeting
- **POST** `/walker/test_walker` - Demonstrates graph traversal capabilities

### Planned Endpoints

With the current `jac start` server shape, public functions are exposed under `/function/...`.

- **POST** `/function/optimize_sync` - Run a synchronous optimization request
- **POST** `/function/submit_optimization_job` - Start an async optimization job
- **POST** `/function/get_optimization_job` - Poll async job status/result
- **POST** `/function/run_repo_agent_sync` - Run the CLI-first repo agent synchronously
- **POST** `/function/submit_repo_agent_job` - Start an async repo-agent job
- **POST** `/function/get_repo_agent_job` - Poll repo-agent status/result
- **POST** `/function/get_auth_readiness` - Return GitHub/Blaxel readiness summary for CLI/web UX
- **POST** `/function/get_config_doctor` - Return local prerequisite/config doctor data
- **POST** `/function/get_recent_jobs` - Return recent persisted async jobs
- **POST** `/function/get_github_app_install_info` - Return GitHub App install URL/config state
- **POST** `/function/handle_github_app_install_callback` - Validate a GitHub App installation callback payload
- **POST** `/function/verify_github_repo_access` - Verify auth can access a repo before starting a job

Async jobs are intentionally minimal right now:
- Job state is persisted under `logs/async_jobs`.
- Finished jobs survive process restarts.
- Jobs that were in progress during a restart are recovered as `interrupted`.
- Completed job payloads include `run_id` and `run_log_path` so a CLI or web UI can link to detailed logs.

### Repo Agent Flow

The first repo-agent milestone is CLI-first and request-driven:

```json
{
  "repo_url": "https://github.com/org/repo.git",
  "base_branch": "main",
  "prompt": "make this faster",
  "replay_script": "scripts/drive_hot_path.py",
  "max_targets": 3,
  "publish_pr": true,
  "auth": {"installation_id": 12345678},
  "backend_config": {"backend": "blaxel"}
}
```

Current behavior:
- Clones the repo to a working checkout.
- Supports either env token auth or GitHub App installation auth.
- Ranks likely targets from replay evidence when `replay_script` is provided, otherwise from repo-wide directory ranking.
- Fans out optimization across the top targets in parallel.
- Can orchestrate candidate work as durable child jobs when backend fan-out is enabled.
- Can run ranking/evaluation workers inside Blaxel sandboxes when `backend_config.backend` is `blaxel`.
- Auto-detects basic Python setup/test commands when the caller does not supply them.
- Validates the winning result with the detected or supplied repo test command.
- Opens one best PR when `publish_pr` is true and GitHub auth is available.
- Returns a PR preview instead of publishing when `publish_pr` is false.

Optional live GitHub App smoke test:

```bash
RINGTAIL_REPO_AGENT_CONFIG='{"app_id":"...","private_key_path":"/path/to/key.pem","installation_id":12345678}' \
RINGTAIL_GITHUB_SMOKE_REPO_URL=https://github.com/org/repo.git \
python -m pytest tests/optimization/with_llm/test_github_app_smoke.py
```

### GitHub Testing Checklist

If you want to help test the GitHub flow today, the fastest useful path is:

1. Pick a small public Python repo with a simple `pytest` command.
2. Install the Ringtail GitHub App onto that repo or org.
3. Set:
   - `RINGTAIL_REPO_AGENT_CONFIG`
   - `BLAXEL_API_KEY` if you want true remote execution
4. First verify auth only:

```bash
jac start main.jac
# then call /get_github_app_install_info and /verify_github_repo_access
```

5. Then run a dry repo-agent job with `publish_pr: false` against that repo.
6. Once that succeeds, rerun with `publish_pr: true` so we can validate branch push + PR creation.

### Repo Benchmark Scaffold

For pitch/demo graphs across a repo suite, use `benchmarks/repo_suite_runner.py` with `benchmarks/repo_suite_template.json`.

Example manifest:

```json
{
  "repos": [
    {
      "name": "sample-python-repo",
      "repo_url": "https://github.com/org/repo.git",
      "prompt": "make this faster",
      "base_branch": "main",
      "test_command": "python -m pytest tests",
      "backend_config": {"backend": "blaxel"}
    }
  ]
}
```

Quick recipe for tomorrow:

```bash
cp benchmarks/repo_suite_template.json /tmp/repo_suite.json
python benchmarks/repo_suite_runner.py /tmp/repo_suite.json \
  --output-json benchmarks/repo_suite_results.json \
  --output-csv benchmarks/repo_suite_results.csv
```

The CSV now emits stable columns:
- `name`
- `repo_url`
- `prompt`
- `status`
- `selected_function`
- `selected_source_file`
- `improvement_ratio`
- `is_significant`
- `validation_success`
- `backend`
- `auth_mode`
- `phase`
- `error`

That is enough to make simple pitch graphs in Sheets, Numbers, or a notebook.

Run it with:

```bash
python benchmarks/repo_suite_runner.py path/to/repo_suite.json
```

This emits:
- `benchmarks/repo_suite_results.json`
- `benchmarks/repo_suite_results.csv`

The CSV is meant to be dropped directly into a plotting notebook or spreadsheet for graphs like:
- repo vs `improvement_ratio`
- repo vs validation pass/fail
- repo vs significant/non-significant result

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
