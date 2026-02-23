"""
Tests for Convert Sorted List to Binary Search Tree. Load solution from BENCHMARK_SOLUTION or same-dir solution.py.
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
sorted_list_to_bst = getattr(solution, 'sorted_list_to_bst')

def test_example():
    h = solution.ListNode(-10); h.next = solution.ListNode(-3); h.next.next = solution.ListNode(0); h.next.next.next = solution.ListNode(5); h.next.next.next.next = solution.ListNode(9); t = sorted_list_to_bst(h); assert t is not None and t.val == 0
