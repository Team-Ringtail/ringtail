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

Ringtail currently supports four public interfaces:

- **Web UI** (`main.jac` client app)
- **HTTP API** (`POST /function/<name>`)
- **CLI** (`ringtail ...`)
- **Python SDK** (`src/sdk.py`)

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
