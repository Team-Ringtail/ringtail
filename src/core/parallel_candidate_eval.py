"""
Parallel candidate evaluation bridge for optimization_loop.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


def evaluate_candidates(payloads: list[dict[str, Any]], max_workers: int = 1) -> list[dict[str, Any]]:
    if max_workers <= 1 or len(payloads) <= 1:
        return [_evaluate_single(payload) for payload in payloads]

    results: list[dict[str, Any] | None] = [None] * len(payloads)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_index = {pool.submit(_evaluate_single, payload): idx for idx, payload in enumerate(payloads)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            results[idx] = future.result()
    return [result for result in results if isinstance(result, dict)]


def _evaluate_single(payload: dict[str, Any]) -> dict[str, Any]:
    mod = __import__("src.core.optimization_loop", fromlist=["_evaluate_candidate"])
    evaluate = getattr(mod, "_evaluate_candidate")
    return evaluate(**payload)
