"""
Anthropic (Claude) client for code optimization.

Reads the API key from RINGTAIL_ANTHROPIC_API_KEY (set by Infisical or .env).
Provides two main functions used by the optimizer agent:

  analyze_and_plan(source_code, criteria, function_call, test_cases) -> dict
  generate_optimized_code(source_code, plan) -> str

All calls are logged via RunLog if one is provided.
"""
import json
import os
import textwrap
from typing import Optional

_ANTHROPIC_ENV_NAMES = ("RINGTAIL_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _get_api_key() -> str:
    for name in _ANTHROPIC_ENV_NAMES:
        val = os.environ.get(name, "")
        if val:
            return val
    return ""


def _get_client():
    """Return an Anthropic client; raises if the key is missing."""
    import anthropic

    api_key = _get_api_key()
    if not api_key:
        raise EnvironmentError(
            f"No Anthropic API key found. Set one of: {', '.join(_ANTHROPIC_ENV_NAMES)}. "
            "Or use: infisical run -- python ..."
        )
    return anthropic.Anthropic(api_key=api_key)


def analyze_and_plan(
    source_code: str,
    criteria: dict,
    function_call: str,
    test_cases: list,
    *,
    model: str = _DEFAULT_MODEL,
    run_log=None,
) -> dict:
    """Ask Claude to analyze code and return a structured optimization plan.

    Returns a dict with keys:
      estimated_time_sec, estimated_memory_mb, steps, analysis, test_cases
    """
    client = _get_client()

    criteria_str = json.dumps(criteria, indent=2) if criteria else "{}"
    tests_str = json.dumps(test_cases, indent=2) if test_cases else "[]"

    prompt = textwrap.dedent(f"""\
        You are a Python performance optimization expert.

        Analyze the following Python function and produce a JSON optimization plan.
        The plan must include:
        - "estimated_time_sec": your estimate of the optimized runtime in seconds
        - "estimated_memory_mb": your estimate of peak memory in MB
        - "steps": a list of concrete optimization steps you will apply
        - "analysis": a brief analysis of the current code's bottlenecks
        - "test_cases": any additional test cases you recommend (list of dicts with "call" and "expected")

        ### Source code
        ```python
        {source_code}
        ```

        ### Profiler function call
        {function_call}

        ### Optimization criteria (weights)
        {criteria_str}

        ### Existing test cases
        {tests_str}

        Respond ONLY with valid JSON (no markdown fences, no explanation outside the JSON).
    """)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    usage = response.usage

    if run_log:
        run_log.llm_call(
            model=model,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            phase="analyze_and_plan",
        )

    text = _strip_markdown_fences(text)

    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        plan = {
            "estimated_time_sec": 0.05,
            "estimated_memory_mb": 10.0,
            "steps": ["LLM returned non-JSON; falling back"],
            "analysis": text[:500],
            "test_cases": [],
        }

    for key in ("estimated_time_sec", "estimated_memory_mb", "steps"):
        plan.setdefault(key, {"estimated_time_sec": 0.05, "estimated_memory_mb": 10.0, "steps": []}[key])

    return plan


def generate_optimized_code(
    source_code: str,
    plan: dict,
    *,
    model: str = _DEFAULT_MODEL,
    run_log=None,
) -> str:
    """Ask Claude to produce the optimized version of the code.

    Returns a Python source string (no markdown fences).
    """
    client = _get_client()

    steps_str = "\n".join(f"  - {s}" for s in plan.get("steps", []))
    analysis = plan.get("analysis", "")

    prompt = textwrap.dedent(f"""\
        You are a Python performance optimization expert.

        Apply the following optimization plan to the source code below and return
        ONLY the complete, runnable Python source code.  Do NOT include markdown
        fences, explanations, or comments that are not part of the code.

        ### Optimization plan
        Analysis: {analysis}
        Steps:
        {steps_str}

        ### Original source code
        ```python
        {source_code}
        ```

        Return ONLY the optimized Python code.
    """)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    usage = response.usage

    if run_log:
        run_log.llm_call(
            model=model,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            phase="generate_optimized_code",
        )

    return _strip_markdown_fences(text)


def _strip_markdown_fences(text: str) -> str:
    """Remove ```python ... ``` or ``` ... ``` wrappers if present."""
    lines = text.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
