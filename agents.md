# AGENTS.md - Ringtail

## Project context
This is a code optimization harness using Jaseci to orchestrate AI agents. Goal: compare multi-agent optimization vs single top-tier agent performance with verifiable metrics (unit tests + profiling).

**CRITICAL**: LLM API calls cost money. This is our primary constraint. Always batch requests, cache results, and estimate costs before implementing features that call LLMs.

---

## Dev environment tips
- Install Jaseci: `pip install jaseci`
- Verify installation: `jac --version`
- Install VS Code Jac extension for syntax highlighting
- Run Jac scripts: `jac run main.jac` (simple execution)
- Start Jaseci server: `jac start main.jac` (web server at localhost:8000)
- **Don't try to run `.jac` files with `python`** - use `jac` command

## Jaseci/Jac syntax reminders
- Import syntax: `import from module { function_name }` (NOT Python's `from module import`)
- Nodes use `has` for properties: `node MyNode { has property: type; }`
- Walkers use `can` for abilities: `walker MyWalker { can action with NodeType entry { } }`
- Persist nodes by connecting to root: `root ++> MyNode();` (correct) vs `root spawn MyNode();` (wrong)
- When unsure: check https://docs.jaseci.org - don't guess

## Testing instructions
- Run Jac unit tests: `jac test tests/unit/`
- (Legacy) Python tests: If you add any `.py` tests later, run `pytest tests/` or `python -m pytest tests/`
- Profile performance: `python -m cProfile script.py`
- **All optimizations must pass original unit tests** - correctness is non-negotiable
- Measure before and after every optimization - never optimize without profiling first
- Verify improvements are statistically significant, not just noise

## Benchmark sources
- LeetCode problems (well-defined, built-in tests)
- GitHub repos with existing test suites
- Focus on performance-critical functions with clear bottlenecks

## Cost management
- Batch LLM requests instead of sequential calls
- Cache results - don't re-optimize the same code
- Use cheaper models for iteration, expensive models only for final runs
- If a feature requires 100+ LLM calls, stop and find a way to reduce that
- Track and log all API usage

## API keys and Infisical
- We use [Infisical](https://app.infisical.com/) to manage API keys. Keys are injected into the process as environment variables (e.g. via Infisical CLI or Kubernetes integration).
- **Never hardcode API keys** in Jac or Python. All LLM/API code must read credentials from the environment only.
- Standard env var names (used by the optimizer agent and byllm when enabled):
  - `RINGTAIL_OPENAI_API_KEY` — OpenAI API key
  - `RINGTAIL_ANTHROPIC_API_KEY` — Anthropic API key
- In production, run the app with env vars set by Infisical; the optimizer agent's LLM path (e.g. `_think_and_prep_llm`) should use `os.environ.get("RINGTAIL_OPENAI_API_KEY")` or the byllm default env vars that Infisical can populate.

---

When in doubt: check Jaseci docs rather than making assumptions.