"""
Tests for Reverse Nodes in k-Group. Load solution from BENCHMARK_SOLUTION or same-dir solution.py.
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
reverse_k_group = getattr(solution, 'reverse_k_group')

def test_example():
    h = solution.ListNode(1); h.next = solution.ListNode(2); h.next.next = solution.ListNode(3); h.next.next.next = solution.ListNode(4); r = reverse_k_group(h, 2); assert r.val == 2 and r.next.val == 1
