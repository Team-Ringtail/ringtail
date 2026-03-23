# CLAUDE.md — Ringtail

EECS 449 project. AI agent-based code optimizer. Orchestrates think-prep-write-test-profile loops. Key goal: compare multi-agent optimization vs single top-tier agent with verifiable metrics (unit tests + profiling).

**CRITICAL**: LLM API calls cost money. Batch requests, cache results, estimate costs before implementing features that call LLMs. If a feature requires 100+ LLM calls, stop and find a way to reduce that.

## Dev Environment
- Python 3.11+, virtual environment recommended.
- Install: `pip install -r requirements.txt && pip install -e .`

## Build / Test
- Python tests: `pytest tests/` or `python -m pytest tests/`
- Profile: `python -m cProfile script.py`
- **All optimizations must pass original unit tests** — correctness is non-negotiable.
- Measure before and after every optimization — never optimize without profiling first.

## API Keys & Secrets
- Managed via [Infisical](https://app.infisical.com/). Keys injected as env vars.
- **Never hardcode API keys.** Read from environment only.
- Env vars:
  - `RINGTAIL_OPENAI_API_KEY` — OpenAI
  - `RINGTAIL_ANTHROPIC_API_KEY` — Anthropic

## Cost Management
- Batch LLM requests instead of sequential calls.
- Cache results — don't re-optimize the same code.
- Use cheaper models for iteration, expensive models only for final runs.
- Track and log all API usage.

## Benchmark Sources
- LeetCode problems (well-defined, built-in tests).
- GitHub repos with existing test suites.
- Focus on performance-critical functions with clear bottlenecks.
