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
- Run unit tests: `pytest tests/` or `python -m pytest tests/`
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

---

When in doubt: check Jaseci docs rather than making assumptions.