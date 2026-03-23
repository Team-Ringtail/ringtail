"""
Parallel post-test checks for candidate evaluation.

Runs property testing and profiling concurrently once unit tests pass.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any

from src.core.profiler import profile_code
from src.core.property_tester import run_property_tests


def run_post_test_checks(
    *,
    optimized_code: str,
    function_name: str,
    original_source_code: str,
    function_call: str,
    benchmark_min_rounds: int,
    benchmark_warmup: bool,
    enable_property_tests: bool,
    property_test_max_examples: int,
) -> dict[str, Any]:
    prop_results: dict[str, Any] = {
        "passed": True,
        "total": 0,
        "passed_count": 0,
        "failed_count": 0,
        "examples_run": 0,
        "falsifying_example": "",
        "error": "skipped",
    }

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2 if enable_property_tests else 1) as pool:
        profile_started = time.perf_counter()
        profile_future = pool.submit(
            profile_code,
            optimized_code,
            function_call,
            benchmark_min_rounds,
            benchmark_warmup,
        )
        prop_future = None
        if enable_property_tests:
            property_started = time.perf_counter()
            prop_future = pool.submit(
                run_property_tests,
                optimized_code,
                function_name,
                reference_code=original_source_code,
                max_examples=property_test_max_examples,
            )

        profile = profile_future.result()
        profile_elapsed_ms = (time.perf_counter() - profile_started) * 1000.0
        if prop_future is not None:
            prop_results = prop_future.result()
            property_elapsed_ms = (time.perf_counter() - property_started) * 1000.0
        else:
            property_elapsed_ms = 0.0

    return {
        "profile": profile,
        "property_tests": prop_results,
        "timings_ms": {
            "post_checks_total": (time.perf_counter() - started) * 1000.0,
            "profile_elapsed": profile_elapsed_ms,
            "property_elapsed": property_elapsed_ms,
        },
    }
