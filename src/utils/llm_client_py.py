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
_DEFAULT_MODEL = "claude-opus-4-6"


def _get_api_key() -> str:
    for name in _ANTHROPIC_ENV_NAMES:
        val = os.environ.get(name, "")
        if val:
            return val
    return ""


def _resolve_model(model: str | None = None) -> str:
    if model:
        return model
    env_model = os.environ.get("RINGTAIL_DEFAULT_LLM_MODEL", "")
    if env_model:
        return env_model
    return _DEFAULT_MODEL


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
    model: str | None = None,
    feedback: dict | None = None,
    run_log=None,
) -> dict:
    """Ask Claude to analyze code and return a structured optimization plan.

    Returns a dict with keys:
      estimated_time_sec, estimated_memory_mb, steps, analysis, test_cases
    """
    resolved_model = _resolve_model(model)
    client = _get_client()

    criteria_str = json.dumps(criteria, indent=2) if criteria else "{}"
    tests_str = json.dumps(test_cases, indent=2) if test_cases else "[]"
    feedback_section = format_feedback_section(feedback)

    prompt = textwrap.dedent(f"""\
        You are a Python performance optimization expert.

        Analyze the following Python function and produce a JSON optimization plan.
        Any optimization must preserve the original function's exact behavior for all
        valid inputs, including edge cases implied by Python semantics. Do not assume
        the profiler call or existing tests cover the full input domain.
        The plan must include:
        - "estimated_time_sec": your estimate of the optimized runtime in seconds
        - "estimated_memory_mb": your estimate of peak memory in MB
        - "steps": a list of concrete optimization steps you will apply
        - "analysis": a brief analysis of the current code's bottlenecks
        - "test_cases": any additional test cases you recommend (list of dicts with "call" and "expected")

        Before proposing a closed-form rewrite, reason through edge cases such as
        empty inputs, negative integers, zero values, duplicates, and ordering
        constraints whenever they are relevant to the original code.

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

        {feedback_section}

        Respond ONLY with valid JSON (no markdown fences, no explanation outside the JSON).
    """)

    response = client.messages.create(
        model=resolved_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    usage = response.usage

    if run_log:
        run_log.llm_call(
            model=resolved_model,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            phase="analyze_and_plan",
        )

    text = _strip_markdown_fences(text)

    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"LLM returned invalid JSON plan: {text[:500]}")

    for key in ("estimated_time_sec", "estimated_memory_mb", "steps"):
        plan.setdefault(key, {"estimated_time_sec": 0.05, "estimated_memory_mb": 10.0, "steps": []}[key])
    if feedback:
        plan["_feedback"] = feedback

    return plan


def generate_optimized_code(
    source_code: str,
    plan: dict,
    *,
    model: str | None = None,
    run_log=None,
) -> str:
    """Ask Claude to produce the optimized version of the code.

    Returns a Python source string (no markdown fences).
    """
    resolved_model = _resolve_model(model)
    client = _get_client()

    steps_str = "\n".join(f"  - {s}" for s in plan.get("steps", []))
    analysis = plan.get("analysis", "")
    feedback_section = format_feedback_section(plan.get("_feedback", None))

    prompt = textwrap.dedent(f"""\
        You are a Python performance optimization expert.

        Apply the following optimization plan to the source code below and return
        ONLY the complete, runnable Python source code.  Do NOT include markdown
        fences, explanations, or comments that are not part of the code.
        Preserve the original function's exact behavior for all inputs supported by
        the original code, including Python edge-case semantics. If a mathematically
        equivalent-looking rewrite would change behavior for cases like negative
        integers, keep the behavior-correct version instead.

        ### Optimization plan
        Analysis: {analysis}
        Steps:
        {steps_str}

        ### Original source code
        ```python
        {source_code}
        ```

        {feedback_section}

        Return ONLY the optimized Python code.
    """)

    response = client.messages.create(
        model=resolved_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    usage = response.usage

    if run_log:
        run_log.llm_call(
            model=resolved_model,
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


def format_feedback_section(feedback: dict | None) -> str:
    if not isinstance(feedback, dict) or not feedback:
        return "### Previous attempt feedback\nNone"

    lines = ["### Previous attempt feedback"]
    feedback_type = str(feedback.get("type", "")).strip()
    error = str(feedback.get("error", "")).strip()
    falsifying_example = str(feedback.get("falsifying_example", "")).strip()
    previous_code = str(feedback.get("previous_code", "")).rstrip()
    failures = feedback.get("failures", [])

    if feedback_type:
        lines.append(f"- Failure type: {feedback_type}")
    if error:
        lines.append(f"- Error: {error}")
    if falsifying_example:
        lines.append("- Falsifying example:")
        lines.append("```text")
        lines.append(falsifying_example)
        lines.append("```")
    if isinstance(failures, list) and failures:
        lines.append("- Failure details:")
        for failure in failures[:3]:
            if not isinstance(failure, dict):
                continue
            message = str(failure.get("message", "") or failure.get("test", "")).strip()
            if message:
                lines.append(f"  - {message}")
    if previous_code:
        lines.append("- Previous failing candidate code:")
        lines.append("```python")
        lines.append(previous_code)
        lines.append("```")
    lines.append(
        "- Use this feedback to produce a behavior-preserving optimization and include a regression test case covering the reported failure when possible."
    )
    return "\n".join(lines)
