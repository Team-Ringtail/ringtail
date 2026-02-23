"""
Tests for Two Sum. Import solution from BENCHMARK_SOLUTION env (default: solution.py in same dir).
Run from repo root: pytest benchmarks/leetcode/two_sum/test_two_sum.py -v
Or use: python benchmarks/run_benchmark.py two_sum
"""
import os
import importlib.util


def _load_solution():
    module_path = os.environ.get("BENCHMARK_SOLUTION", "")
    if module_path and os.path.isfile(module_path):
        spec = importlib.util.spec_from_file_location("solution", module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    # Default: solution.py in the same directory as this test file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    default_solution = os.path.join(this_dir, "solution.py")
    spec = importlib.util.spec_from_file_location("solution", default_solution)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


solution = _load_solution()
two_sum = solution.two_sum


def test_two_sum_basic():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]


def test_two_sum_small():
    assert two_sum([3, 2, 4], 6) == [1, 2]


def test_two_sum_pair_same():
    assert two_sum([3, 3], 6) == [0, 1]


def test_two_sum_no_solution():
    assert two_sum([1, 2, 3], 10) == []
