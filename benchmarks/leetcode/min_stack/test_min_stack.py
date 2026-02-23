"""
Tests for Min Stack. Load solution from BENCHMARK_SOLUTION or same-dir solution.py.
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
    this_dir = os.path.dirname(os.path.abspath(__file__))
    default_solution = os.path.join(this_dir, "solution.py")
    spec = importlib.util.spec_from_file_location("solution", default_solution)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

solution = _load_solution()
MinStack = getattr(solution, 'MinStack')

def test_example():
    s = MinStack(); s.push(-2); s.push(0); s.push(-3); assert s.get_min() == -3; s.pop(); assert s.top() == 0
