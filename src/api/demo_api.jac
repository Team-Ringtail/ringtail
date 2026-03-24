"""
Ranked demo suite and benchmark catalog endpoints.
"""

import importlib;


def:pub get_ranked_demo_suite_catalog(benchmark_id: str = "") -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_suite_catalog");
    if benchmark_id != "" {
        return func(benchmark_id);
    }
    return func(None);
}


def:pub get_ranked_demo_benchmarks -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_benchmarks");
    return func();
}


def:pub get_latest_ranked_demo_suite -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_latest_demo_suite_result");
    return func();
}


def:pub get_ranked_demo_job_progress(job_id: str) -> dict {
    mod = importlib.import_module("src.core.ranked_demo_suite");
    func = getattr(mod, "get_demo_job_progress");
    return func(job_id);
}
