"""
Anthropic (Claude) client for code optimization -- Jac facade.

Delegates to the canonical Python implementation in src/utils/llm_client.py
which has richer prompts and feedback handling. This file exists so Jac
modules can use ``import from src.utils.llm_client { ... }`` syntax.
"""

import importlib;

glob _py_mod = None;


def _mod -> object {
    if _py_mod is None {
        _py_mod = importlib.import_module("src.utils.llm_client");
    }
    return _py_mod;
}


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
    func = getattr(_mod(), "analyze_and_plan");
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
    func = getattr(_mod(), "generate_optimized_code");
    return func(
        source_code,
        plan,
        model=model,
        run_log=run_log
    );
}
