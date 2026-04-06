# Ringtail

Ringtail is an AI-assisted Python optimization harness that runs a verifiable loop:

1. analyze and plan
2. generate candidate code
3. run tests + property checks
4. profile baseline vs candidate
5. accept/iterate based on measured results

## Quick Links

- Interface usage: `docs/interfaces.md`
- HTTP contract: `docs/API_DOCUMENTATION.md`
- Optimization operation contract: `docs/OPTIMIZATION_CONTRACT.md`
- Architecture: `docs/ARCHITECTURE.md`
- MCP product spec: `docs/MCP_PRODUCT_SPEC.md`
- Replay logical contract: `docs/REPLAY_API_CONTRACT.md`

## Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Start The Product

```bash
ringtail serve
# or
jac start main.jac --port 8000
```

Then open: `http://localhost:8000`.

## Interfaces

Ringtail currently supports five public interfaces:

- **Web UI** (`main.jac` client app)
- **HTTP API** (`POST /function/<name>`)
- **CLI** (`ringtail ...`)
- **Python SDK** (`src/sdk.py`)
- **MCP server** (`ringtail-mcp`)

See `docs/interfaces.md` for examples and troubleshooting.

## Core Commands

### Health / diagnostics

```bash
ringtail config doctor
curl -s -X POST http://localhost:8000/function/health -H 'Content-Type: application/json' -d '{}'
```

### File optimization (CLI local mode)

```bash
ringtail file optimize /abs/path/to/file.py function_name \
  --function-call "function_name(1000)" \
  --config-name test-fast \
  --local --json
```

### Repo agent flow

```bash
ringtail repo run /path/to/repo "make this faster" --local
ringtail repo submit /path/to/repo "make this faster" --wait --local
ringtail repo status <job_id> --local
ringtail repo logs <job_id> --local
```

### MCP server

```bash
ringtail-mcp
# or
python -m src.mcp.server
```

Recommended agent call order:

1. `profile_repo`
2. `optimize_hotspot`
3. `submit_optimize_repo_job` only if the fast path is not enough

### MCP verification suite

```bash
python benchmarks/run_profile_first_mcp_suite.py
python benchmarks/run_profile_first_mcp_suite.py --include-external
```

The external verification pass clones `https://github.com/pallets/click.git`, installs it editable, profiles a pinned Click parsing workload, and writes a machine-readable summary to `logs/profile_first_mcp_suite_summary.json`.

## Environment Variables

- `RINGTAIL_ANTHROPIC_API_KEY` - required for LLM-backed runs
- `RINGTAIL_DEFAULT_LLM_MODEL` - optional model override
- `RINGTAIL_REPO_AGENT_CONFIG` - required for GitHub App/token repo-agent auth
- `BLAXEL_API_KEY` - required only for Blaxel backend flows

## Testing

```bash
jac test tests/unit/
python -m pytest tests/
```

## Notes
