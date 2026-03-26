"""
Anthropic (Claude) client for code optimization -- Jac facade.

Delegates to the canonical Python implementation in src/utils/llm_client_py.py
(which must be a distinct import path from this module; loading ``src.utils.llm_client``
would resolve to this Jac file and recurse). Jac modules use
``import from src.utils.llm_client { ... }`` syntax.
"""

import importlib;


def analyze_and_plan(
    source_code: str,
    criteria: dict,
    function_call: str,
    test_cases: list,
    feedback: dict | None = None,
    *,
    model: str | None = None,
    run_log: object | None = None
) -> dict {
    mod = importlib.import_module("src.utils.llm_client_py");
    func = getattr(mod, "analyze_and_plan");
    return func(
        source_code,
        criteria,
        function_call,
        test_cases,
        model=model,
        feedback=feedback,
        run_log=run_log
    );
}


def generate_optimized_code(
    source_code: str,
    plan: dict,
    *,
    model: str | None = None,
    run_log: object | None = None
) -> str {
    mod = importlib.import_module("src.utils.llm_client_py");
    func = getattr(mod, "generate_optimized_code");
    return func(
        source_code,
        plan,
        model=model,
        run_log=run_log
    );
}
