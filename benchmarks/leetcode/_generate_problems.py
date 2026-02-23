#!/usr/bin/env python3
"""
One-off script to generate spec.json, solution.py, and test file for each LeetCode problem.
Run from repo root: python benchmarks/leetcode/_generate_problems.py
"""
import json
import os

# (title, slug, leetcode_id, difficulty, entry_function, expected_time, expected_space)
# entry_function must be valid Python identifier (no leading digit)
PROBLEMS = [
    ("3Sum", "three_sum", 15, "medium", "three_sum", "O(n^2)", "O(1)"),
    ("3Sum Closest", "three_sum_closest", 16, "medium", "three_sum_closest", "O(n^2)", "O(1)"),
    ("4Sum", "four_sum", 18, "medium", "four_sum", "O(n^3)", "O(1)"),
    ("Add Digits", "add_digits", 258, "easy", "add_digits", "O(1)", "O(1)"),
    ("Additive Number", "additive_number", 306, "medium", "is_additive_number", "O(n^2)", "O(n)"),
    ("Burst Balloons", "burst_balloons", 312, "hard", "max_coins", "O(n^3)", "O(n^2)"),
    ("Combination Sum II", "combination_sum_ii", 40, "medium", "combination_sum2", "O(2^n)", "O(n)"),
    ("Container With Most Water", "container_with_most_water", 11, "medium", "max_area", "O(n)", "O(1)"),
    ("Convert Sorted List to Binary Search Tree", "convert_sorted_list_to_bst", 109, "medium", "sorted_list_to_bst", "O(n log n)", "O(log n)"),
    ("Count of Smaller Numbers After Self", "count_smaller_after_self", 315, "hard", "count_smaller", "O(n^2)", "O(n)"),
    ("Delete Node in a Linked List", "delete_node_in_linked_list", 237, "easy", "delete_node", "O(1)", "O(1)"),
    ("Divide Two Integers", "divide_two_integers", 29, "medium", "divide", "O(log n)", "O(1)"),
    ("Find First and Last Position of Element in Sorted Array", "search_range", 34, "medium", "search_range", "O(n)", "O(1)"),
    ("Find Minimum in Rotated Sorted Array", "find_min_rotated", 153, "medium", "find_min", "O(log n)", "O(1)"),
    ("Find Peak Element", "find_peak_element", 162, "medium", "find_peak_element", "O(log n)", "O(1)"),
    ("Gray Code", "gray_code", 89, "medium", "gray_code", "O(2^n)", "O(1)"),
    ("Integer to Roman", "integer_to_roman", 12, "medium", "int_to_roman", "O(1)", "O(1)"),
    ("Kth Smallest Element in a Sorted Matrix", "kth_smallest_sorted_matrix", 378, "medium", "kth_smallest", "O(n^2 log n)", "O(n)"),
    ("Largest Number", "largest_number", 179, "medium", "largest_number", "O(n log n)", "O(n)"),
    ("Longest Increasing Subsequence", "longest_increasing_subsequence", 300, "medium", "length_of_lis", "O(n^2)", "O(n)"),
    ("Longest Palindromic Substring", "longest_palindromic_substring", 5, "medium", "longest_palindrome", "O(n^2)", "O(1)"),
    ("Longest Substring Without Repeating Characters", "longest_substring_no_repeat", 3, "medium", "length_of_longest_substring", "O(n)", "O(min(n,k))"),
    ("LRU Cache", "lru_cache", 146, "medium", "LRUCache", "O(1)", "O(capacity)"),
    ("Merge Intervals", "merge_intervals", 56, "medium", "merge", "O(n log n)", "O(n)"),
    ("Min Stack", "min_stack", 155, "easy", "MinStack", "O(1)", "O(n)"),
    ("Nim Game", "nim_game", 292, "easy", "can_win_nim", "O(1)", "O(1)"),
    ("N-Queens", "n_queens", 51, "hard", "solve_n_queens", "O(n!)", "O(n^2)"),
    ("N-Queens II", "n_queens_ii", 52, "hard", "total_n_queens", "O(n!)", "O(n)"),
    ("Number of 1 Bits", "number_of_1_bits", 191, "easy", "hamming_weight", "O(1)", "O(1)"),
    ("Palindrome Number", "palindrome_number", 9, "easy", "is_palindrome", "O(log n)", "O(1)"),
    ("Pascal's Triangle", "pascals_triangle", 118, "easy", "generate", "O(n^2)", "O(1)"),
    ("Permutation Sequence", "permutation_sequence", 60, "hard", "get_permutation", "O(n^2)", "O(n)"),
    ("Permutations", "permutations", 46, "medium", "permute", "O(n!)", "O(n)"),
    ("Permutations II", "permutations_ii", 47, "medium", "permute_unique", "O(n!)", "O(n)"),
    ("Pow(x, n)", "pow_x_n", 50, "medium", "my_pow", "O(log n)", "O(log n)"),
    ("Power of Two", "power_of_two", 231, "easy", "is_power_of_two", "O(1)", "O(1)"),
    ("Rectangle Area", "rectangle_area", 223, "medium", "compute_area", "O(1)", "O(1)"),
    ("Remove Invalid Parentheses", "remove_invalid_parentheses", 301, "hard", "remove_invalid_parentheses", "O(2^n)", "O(n)"),
    ("Remove Nth Node From End of List", "remove_nth_from_end", 19, "medium", "remove_nth_from_end", "O(n)", "O(1)"),
    ("Restore IP Addresses", "restore_ip_addresses", 93, "medium", "restore_ip_addresses", "O(1)", "O(1)"),
    ("Reverse Bits", "reverse_bits", 190, "easy", "reverse_bits", "O(1)", "O(1)"),
    ("Reverse Integer", "reverse_integer", 7, "easy", "reverse", "O(log n)", "O(1)"),
    ("Reverse Nodes in k-Group", "reverse_nodes_k_group", 25, "hard", "reverse_k_group", "O(n)", "O(1)"),
    ("Roman to Integer", "roman_to_integer", 13, "easy", "roman_to_int", "O(n)", "O(1)"),
    ("Rotate Image", "rotate_image", 48, "medium", "rotate", "O(n^2)", "O(1)"),
    ("Russian Doll Envelopes", "russian_doll_envelopes", 354, "hard", "max_envelopes", "O(n^2)", "O(n)"),
    ("Search in Rotated Sorted Array", "search_rotated_sorted_array", 33, "medium", "search", "O(log n)", "O(1)"),
    ("Search Insert Position", "search_insert_position", 35, "easy", "search_insert", "O(log n)", "O(1)"),
    ("Sort List", "sort_list", 148, "medium", "sort_list", "O(n log n)", "O(log n)"),
    ("Spiral Matrix II", "spiral_matrix_ii", 59, "medium", "generate_matrix", "O(n^2)", "O(1)"),
    ("Sqrt(x)", "sqrt_x", 69, "easy", "my_sqrt", "O(log x)", "O(1)"),
    ("String to Integer (atoi)", "string_to_integer_atoi", 8, "medium", "my_atoi", "O(n)", "O(1)"),
    ("Subsets", "subsets", 78, "medium", "subsets", "O(2^n)", "O(2^n)"),
    ("Subsets II", "subsets_ii", 90, "medium", "subsets_with_dup", "O(2^n)", "O(2^n)"),
    ("Swap Nodes in Pairs", "swap_nodes_in_pairs", 24, "medium", "swap_pairs", "O(n)", "O(1)"),
    ("The Skyline Problem", "skyline_problem", 218, "hard", "get_skyline", "O(n log n)", "O(n)"),
    ("Two Sum", "two_sum", 1, "easy", "two_sum", "O(n)", "O(n)"),  # exists
    ("Valid Parentheses", "valid_parentheses", 20, "easy", "is_valid", "O(n)", "O(n)"),
    ("Valid Sudoku", "valid_sudoku", 36, "medium", "is_valid_sudoku", "O(1)", "O(1)"),
    ("Zigzag Conversion", "zigzag_conversion", 6, "medium", "convert", "O(n)", "O(n)"),
]

SOLUTIONS = {
    "three_sum": '''"""Sub-optimal: brute force O(n^3) instead of two-pointer O(n^2)."""
def three_sum(nums: list[int]) -> list[list[int]]:
    n = len(nums)
    seen = set()
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if nums[i] + nums[j] + nums[k] == 0:
                    t = tuple(sorted([nums[i], nums[j], nums[k]]))
                    if t not in seen:
                        seen.add(t)
                        out.append(sorted([nums[i], nums[j], nums[k]]))
    return sorted(out)
''',
    "three_sum_closest": '''"""Sub-optimal: try all triples O(n^3)."""
def three_sum_closest(nums: list[int], target: int) -> int:
    n = len(nums)
    best = sum(nums[:3])
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                s = nums[i] + nums[j] + nums[k]
                if abs(s - target) < abs(best - target):
                    best = s
    return best
''',
    "four_sum": '''"""Sub-optimal: brute force O(n^4)."""
def four_sum(nums: list[int], target: int) -> list[list[int]]:
    n = len(nums)
    seen = set()
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                for l in range(k + 1, n):
                    if nums[i] + nums[j] + nums[k] + nums[l] == target:
                        t = tuple(sorted([nums[i], nums[j], nums[k], nums[l]]))
                        if t not in seen:
                            seen.add(t)
                            out.append(sorted([nums[i], nums[j], nums[k], nums[l]]))
    return sorted(out)
''',
    "add_digits": '''"""Sub-optimal: loop until single digit instead of O(1) formula."""
def add_digits(num: int) -> int:
    while num >= 10:
        num = sum(int(d) for d in str(num))
    return num
''',
    "additive_number": '''"""Sub-optimal: try all first two segment lengths O(n^2) then validate."""
def is_additive_number(num: str) -> bool:
    n = len(num)
    for i in range(1, n):
        for j in range(i + 1, n):
            a, b = num[:i], num[i:j]
            if (a[0] == "0" and len(a) > 1) or (b[0] == "0" and len(b) > 1):
                continue
            x, y = int(a), int(b)
            k = j
            while k < n:
                z = x + y
                s = str(z)
                if not num[k:].startswith(s):
                    break
                x, y = y, z
                k += len(s)
            if k == n:
                return True
    return False
''',
    "burst_balloons": '''"""Sub-optimal: try all orders O(n!) with memo on (tuple of remaining)."""
def max_coins(nums: list[int]) -> int:
    from functools import lru_cache
    A = [1] + [x for x in nums] + [1]
    @lru_cache(maxsize=None)
    def dp(i: int, j: int) -> int:
        if i > j:
            return 0
        best = 0
        for k in range(i, j + 1):
            best = max(best, A[i-1] * A[k] * A[j+1] + dp(i, k-1) + dp(k+1, j))
        return best
    return dp(1, len(A) - 2)
''',
    "combination_sum_ii": '''"""Sub-optimal: generate all subsets then filter duplicates (still correct)."""
def combination_sum2(candidates: list[int], target: int) -> list[list[int]]:
    out = []
    candidates.sort()
    def bt(start: int, path: list, s: int):
        if s == target:
            out.append(path[:])
            return
        if s > target:
            return
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i-1]:
                continue
            path.append(candidates[i])
            bt(i + 1, path, s + candidates[i])
            path.pop()
    bt(0, [], 0)
    return out
''',
    "container_with_most_water": '''"""Sub-optimal: try all pairs O(n^2) instead of two pointers O(n)."""
def max_area(height: list[int]) -> int:
    best = 0
    for i in range(len(height)):
        for j in range(i + 1, len(height)):
            best = max(best, min(height[i], height[j]) * (j - i))
    return best
''',
    "convert_sorted_list_to_bst": '''"""Sub-optimal: build list to array then recursive O(n log n) instead of in-order O(n)."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def sorted_list_to_bst(head: ListNode) -> TreeNode:
    arr = []
    while head:
        arr.append(head.val)
        head = head.next
    def build(l: int, r: int) -> TreeNode:
        if l > r:
            return None
        mid = (l + r) // 2
        node = TreeNode(arr[mid])
        node.left = build(l, mid - 1)
        node.right = build(mid + 1, r)
        return node
    return build(0, len(arr) - 1) if arr else None
''',
    "count_smaller_after_self": '''"""Sub-optimal: for each index scan right O(n^2) instead of merge sort / BST."""
def count_smaller(nums: list[int]) -> list[int]:
    n = len(nums)
    out = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            if nums[j] < nums[i]:
                out[i] += 1
    return out
''',
    "delete_node_in_linked_list": '''"""Standard O(1) copy-next approach (problem is inherently O(1))."""
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

def delete_node(node: ListNode) -> None:
    node.val = node.next.val
    node.next = node.next.next
''',
    "divide_two_integers": '''"""Sub-optimal: subtract divisor repeatedly O(dividend/divisor) instead of bit shift O(log n)."""
def divide(dividend: int, divisor: int) -> int:
    neg = (dividend < 0) != (divisor < 0)
    a, b = abs(dividend), abs(divisor)
    q = 0
    while a >= b:
        a -= b
        q += 1
    q = -q if neg else q
    return max(-2**31, min(2**31 - 1, q))
''',
    "search_range": '''"""Sub-optimal: linear scan O(n) instead of two binary searches O(log n)."""
def search_range(nums: list[int], target: int) -> list[int]:
    lo, hi = -1, -1
    for i, x in enumerate(nums):
        if x == target:
            if lo == -1:
                lo = i
            hi = i
    return [lo, hi]
''',
    "find_min_rotated": '''"""Sub-optimal: linear scan O(n) instead of binary search O(log n)."""
def find_min(nums: list[int]) -> int:
    return min(nums)
''',
    "find_peak_element": '''"""Sub-optimal: linear scan O(n) instead of binary search O(log n)."""
def find_peak_element(nums: list[int]) -> int:
    for i in range(len(nums)):
        left = nums[i-1] if i > 0 else float("-inf")
        right = nums[i+1] if i < len(nums)-1 else float("-inf")
        if nums[i] >= left and nums[i] >= right:
            return i
    return 0
''',
    "gray_code": '''"""Sub-optimal: generate all 2^n and convert to Gray (still O(2^n) time)."""
def gray_code(n: int) -> list[int]:
    if n == 0:
        return [0]
    out = []
    for i in range(2**n):
        g = i ^ (i >> 1)
        out.append(g)
    return out
''',
    "integer_to_roman": '''"""Sub-optimal: many conditionals; optimal is table-driven."""
def int_to_roman(num: int) -> str:
    sym = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
    out = []
    for v, s in sym:
        while num >= v:
            out.append(s)
            num -= v
    return "".join(out)
''',
    "kth_smallest_sorted_matrix": '''"""Sub-optimal: flatten and sort O(n^2 log n) instead of heap/binary search."""
def kth_smallest(matrix: list[list[int]], k: int) -> int:
    flat = []
    for row in matrix:
        flat.extend(row)
    flat.sort()
    return flat[k - 1]
''',
    "largest_number": '''"""Correct but compare as string concatenation (standard approach)."""
def largest_number(nums: list[int]) -> str:
    from functools import cmp_to_key
    def cmp(a: str, b: str):
        return -1 if a + b > b + a else (1 if a + b < b + a else 0)
    s = sorted([str(x) for x in nums], key=cmp_to_key(cmp))
    out = "".join(s).lstrip("0")
    return out or "0"
''',
    "longest_increasing_subsequence": '''"""Sub-optimal: DP O(n^2) instead of binary search O(n log n)."""
def length_of_lis(nums: list[int]) -> int:
    if not nums:
        return 0
    dp = [1] * len(nums)
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
''',
    "longest_palindromic_substring": '''"""Sub-optimal: try all substrings O(n^3) instead of expand O(n^2)."""
def longest_palindrome(s: str) -> str:
    n = len(s)
    best = ""
    for i in range(n):
        for j in range(i, n):
            sub = s[i:j+1]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best
''',
    "longest_substring_no_repeat": '''"""Sub-optimal: check all substrings O(n^2) instead of sliding window O(n)."""
def length_of_longest_substring(s: str) -> int:
    n = len(s)
    best = 0
    for i in range(n):
        seen = set()
        for j in range(i, n):
            if s[j] in seen:
                break
            seen.add(s[j])
            best = max(best, j - i + 1)
    return best
''',
    "lru_cache": '''"""LRU with ordered dict (correct; could use dict + doubly linked list for same big-O)."""
from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = OrderedDict()
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]
    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)
''',
    "merge_intervals": '''"""Sort then merge O(n log n) - standard approach."""
def merge(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    out = [intervals[0][:]]
    for a, b in intervals[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
''',
    "min_stack": '''"""Two stacks: one for values, one for minimums. O(1) ops."""
class MinStack:
    def __init__(self):
        self.stk = []
        self.mn = []
    def push(self, val: int) -> None:
        self.stk.append(val)
        self.mn.append(val if not self.mn else min(self.mn[-1], val))
    def pop(self) -> None:
        self.stk.pop()
        self.mn.pop()
    def top(self) -> int:
        return self.stk[-1]
    def get_min(self) -> int:
        return self.mn[-1]
''',
    "nim_game": '''"""O(1) math."""
def can_win_nim(n: int) -> bool:
    return n % 4 != 0
''',
    "n_queens": '''"""Backtrack row by row - standard."""
def solve_n_queens(n: int) -> list[list[str]]:
    out = []
    col, diag1, diag2 = set(), set(), set()
    def place(row: int, board: list):
        if row == n:
            qs = set((i, board[i]) for i in range(n))
            out.append(["".join("Q" if (r, c) in qs else "." for c in range(n)) for r in range(n)])
            return
        for c in range(n):
            if c in col or (row - c) in diag1 or (row + c) in diag2:
                continue
            col.add(c); diag1.add(row - c); diag2.add(row + c)
            board.append(c)
            place(row + 1, board)
            board.pop()
            col.discard(c); diag1.discard(row - c); diag2.discard(row + c)
    place(0, [])
    return out
''',
    "n_queens_ii": '''"""Count only - same backtrack."""
def total_n_queens(n: int) -> int:
    count = 0
    col, diag1, diag2 = set(), set(), set()
    def place(row: int):
        nonlocal count
        if row == n:
            count += 1
            return
        for c in range(n):
            if c in col or (row - c) in diag1 or (row + c) in diag2:
                continue
            col.add(c); diag1.add(row - c); diag2.add(row + c)
            place(row + 1)
            col.discard(c); diag1.discard(row - c); diag2.discard(row + c)
    place(0)
    return count
''',
    "number_of_1_bits": '''"""Loop over bits O(32)."""
def hamming_weight(n: int) -> int:
    n = n & 0xFFFFFFFF
    c = 0
    while n:
        c += n & 1
        n >>= 1
    return c
''',
    "palindrome_number": '''"""Convert to string O(log n) - sub-optimal vs reverse half."""
def is_palindrome(x: int) -> bool:
    if x < 0:
        return False
    s = str(x)
    return s == s[::-1]
''',
    "pascals_triangle": '''"""Generate row by row - standard."""
def generate(num_rows: int) -> list[list[int]]:
    if num_rows <= 0:
        return []
    out = [[1]]
    for _ in range(num_rows - 1):
        prev = out[-1]
        row = [1] + [prev[i] + prev[i+1] for i in range(len(prev)-1)] + [1]
        out.append(row)
    return out
''',
    "permutation_sequence": '''"""Build by computing next digit - can be O(n) with factorial."""
def get_permutation(n: int, k: int) -> str:
    from itertools import permutations
    perms = list(permutations(range(1, n + 1)))
    return "".join(str(x) for x in perms[k - 1])
''',
    "permutations": '''"""Backtrack - standard."""
def permute(nums: list[int]) -> list[list[int]]:
    out = []
    def bt(path, left):
        if not left:
            out.append(path[:])
            return
        for i, x in enumerate(left):
            bt(path + [x], left[:i] + left[i+1:])
    bt([], list(nums))
    return out
''',
    "permutations_ii": '''"""Backtrack with sort and skip duplicates."""
def permute_unique(nums: list[int]) -> list[list[int]]:
    out = []
    nums.sort()
    used = [False] * len(nums)
    def bt(path):
        if len(path) == len(nums):
            out.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            if i > 0 and nums[i] == nums[i-1] and not used[i-1]:
                continue
            used[i] = True
            path.append(nums[i])
            bt(path)
            path.pop()
            used[i] = False
    bt([])
    return out
''',
    "pow_x_n": '''"""Sub-optimal: linear multiply O(n) instead of binary exponentiation O(log n)."""
def my_pow(x: float, n: int) -> float:
    if n < 0:
        x, n = 1/x, -n
    out = 1.0
    for _ in range(n):
        out *= x
    return out
''',
    "power_of_two": '''"""Single bit check."""
def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0
''',
    "rectangle_area": '''"""Area formula."""
def compute_area(ax1: int, ay1: int, ax2: int, ay2: int, bx1: int, by1: int, bx2: int, by2: int) -> int:
    a = (ax2 - ax1) * (ay2 - ay1)
    b = (bx2 - bx1) * (by2 - by1)
    overlap = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
    return a + b - overlap
''',
    "remove_invalid_parentheses": '''"""BFS remove one char at a time - standard."""
def remove_invalid_parentheses(s: str) -> list[str]:
    def valid(t):
        c = 0
        for x in t:
            if x == "(": c += 1
            elif x == ")": c -= 1
            if c < 0: return False
        return c == 0
    level = {s}
    while level:
        ok = [t for t in level if valid(t)]
        if ok:
            return list(set(ok))
        level = {t[:i] + t[i+1:] for t in level for i in range(len(t)) if t[i] in "()"}
    return [""]
''',
    "remove_nth_from_end": '''"""Two passes: count then remove."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def remove_nth_from_end(head: ListNode, n: int) -> ListNode:
    dummy = ListNode(0, head)
    cur = head
    L = 0
    while cur:
        L += 1
        cur = cur.next
    cur = dummy
    for _ in range(L - n):
        cur = cur.next
    cur.next = cur.next.next
    return dummy.next
''',
    "restore_ip_addresses": '''"""Backtrack try 1,2,3 digit segments."""
def restore_ip_addresses(s: str) -> list[str]:
    out = []
    def bt(start: int, parts: list):
        if len(parts) == 4:
            if start == len(s):
                out.append(".".join(parts))
            return
        for w in (1, 2, 3):
            if start + w > len(s):
                break
            seg = s[start:start+w]
            if (seg[0] == "0" and len(seg) > 1) or int(seg) > 255:
                continue
            parts.append(seg)
            bt(start + w, parts)
            parts.pop()
    bt(0, [])
    return out
''',
    "reverse_bits": '''"""Bit by bit."""
def reverse_bits(n: int) -> int:
    n = n & 0xFFFFFFFF
    out = 0
    for _ in range(32):
        out = (out << 1) | (n & 1)
        n >>= 1
    return out
''',
    "reverse_integer": '''"""Convert to string and reverse."""
def reverse(x: int) -> int:
    sign = -1 if x < 0 else 1
    s = str(abs(x))[::-1]
    out = sign * int(s)
    return out if -2**31 <= out <= 2**31 - 1 else 0
''',
    "reverse_nodes_k_group": '''"""Reverse k at a time - standard."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_k_group(head: ListNode, k: int) -> ListNode:
    def rev(start, end):
        prev, cur = end, start
        while cur != end:
            nxt = cur.next
            cur.next = prev
            prev, cur = cur, nxt
        return prev
    dummy = ListNode(0, head)
    gprev = dummy
    while True:
        kth = gprev
        for _ in range(k):
            kth = kth.next
            if not kth:
                return dummy.next
        gnext = kth.next
        old_start = gprev.next
        gprev.next = rev(gprev.next, kth.next)
        old_start.next = gnext
        gprev = old_start
''',
    "roman_to_integer": '''"""Scan left to right add/subtract."""
def roman_to_int(s: str) -> int:
    m = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    out = 0
    for i in range(len(s)):
        v = m[s[i]]
        if i + 1 < len(s) and m[s[i+1]] > v:
            out -= v
        else:
            out += v
    return out
''',
    "rotate_image": '''"""Transpose then reverse each row - standard O(n^2)."""
def rotate(matrix: list[list[int]]) -> None:
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:
        row.reverse()
''',
    "russian_doll_envelopes": '''"""Sub-optimal: DP O(n^2) instead of LIS O(n log n)."""
def max_envelopes(envelopes: list[list[int]]) -> int:
    if not envelopes:
        return 0
    envelopes.sort(key=lambda x: (x[0], -x[1]))
    dp = [1] * len(envelopes)
    for i in range(1, len(envelopes)):
        for j in range(i):
            if envelopes[j][0] < envelopes[i][0] and envelopes[j][1] < envelopes[i][1]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
''',
    "search_rotated_sorted_array": '''"""Sub-optimal: linear scan O(n) instead of binary search."""
def search(nums: list[int], target: int) -> int:
    for i, x in enumerate(nums):
        if x == target:
            return i
    return -1
''',
    "search_insert_position": '''"""Binary search - standard."""
def search_insert(nums: list[int], target: int) -> int:
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
''',
    "sort_list": '''"""Sub-optimal: copy to list, sort, rebuild O(n log n) time but O(n) extra space."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def sort_list(head: ListNode) -> ListNode:
    arr = []
    while head:
        arr.append(head.val)
        head = head.next
    arr.sort()
    dummy = ListNode(0)
    cur = dummy
    for v in arr:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next
''',
    "spiral_matrix_ii": '''"""Layer by layer - standard."""
def generate_matrix(n: int) -> list[list[int]]:
    m = [[0] * n for _ in range(n)]
    v, top, bottom, left, right = 1, 0, n - 1, 0, n - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            m[top][c] = v; v += 1
        top += 1
        for r in range(top, bottom + 1):
            m[r][right] = v; v += 1
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                m[bottom][c] = v; v += 1
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                m[r][left] = v; v += 1
            left += 1
    return m
''',
    "sqrt_x": '''"""Sub-optimal: linear search O(x) instead of binary search O(log x)."""
def my_sqrt(x: int) -> int:
    if x <= 1:
        return x
    r = 1
    while r * r <= x:
        r += 1
    return r - 1
''',
    "string_to_integer_atoi": '''"""Parse with strip and sign."""
def my_atoi(s: str) -> int:
    s = s.strip()
    if not s:
        return 0
    sign = 1
    if s[0] in "+-":
        sign = -1 if s[0] == "-" else 1
        s = s[1:]
    out = 0
    for c in s:
        if not c.isdigit():
            break
        out = out * 10 + int(c)
    out *= sign
    return max(-2**31, min(2**31 - 1, out))
''',
    "subsets": '''"""Backtrack - standard."""
def subsets(nums: list[int]) -> list[list[int]]:
    out = [[]]
    def bt(start, path):
        for i in range(start, len(nums)):
            path.append(nums[i])
            out.append(path[:])
            bt(i + 1, path)
            path.pop()
    bt(0, [])
    return out
''',
    "subsets_ii": '''"""Backtrack with sort and skip duplicates."""
def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    nums.sort()
    out = [[]]
    def bt(start, path):
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i-1]:
                continue
            path.append(nums[i])
            out.append(path[:])
            bt(i + 1, path)
            path.pop()
    bt(0, [])
    return out
''',
    "swap_nodes_in_pairs": '''"""Iterative swap pairs."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def swap_pairs(head: ListNode) -> ListNode:
    dummy = ListNode(0, head)
    prev = dummy
    while prev.next and prev.next.next:
        a, b = prev.next, prev.next.next
        prev.next = b
        a.next = b.next
        b.next = a
        prev = a
    return dummy.next
''',
    "skyline_problem": '''"""Sub-optimal: sweep and check all key points O(n^2) or use heap O(n log n)."""
def get_skyline(buildings: list[list[int]]) -> list[list[int]]:
    events = []
    for L, R, H in buildings:
        events.append((L, -H))
        events.append((R, H))
    events.sort(key=lambda x: (x[0], x[1]))
    from sortedcontainers import SortedDict
    try:
        from sortedcontainers import SortedDict
        active = SortedDict()
    except ImportError:
        active = {}
    active[0] = 1
    prev = 0
    out = []
    for x, h in events:
        if h < 0:
            active[-h] = active.get(-h, 0) + 1
        else:
            active[h] -= 1
            if active[h] == 0:
                del active[h]
        cur = max(active.keys()) if active else 0
        if cur != prev:
            out.append([x, cur])
            prev = cur
    return out
''',
    "two_sum": "",  # exists
    "valid_parentheses": '''"""Stack - standard."""
def is_valid(s: str) -> bool:
    st = []
    m = {")": "(", "}": "{", "]": "["}
    for c in s:
        if c in "({[":
            st.append(c)
        else:
            if not st or st[-1] != m.get(c):
                return False
            st.pop()
    return len(st) == 0
''',
    "valid_sudoku": '''"""Check rows, cols, boxes - standard."""
def is_valid_sudoku(board: list[list[str]]) -> bool:
    for r in range(9):
        seen = set()
        for c in range(9):
            x = board[r][c]
            if x != "." and x in seen:
                return False
            seen.add(x)
    for c in range(9):
        seen = set()
        for r in range(9):
            x = board[r][c]
            if x != "." and x in seen:
                return False
            seen.add(x)
    for box in range(9):
        br, bc = (box // 3) * 3, (box % 3) * 3
        seen = set()
        for i in range(3):
            for j in range(3):
                x = board[br+i][bc+j]
                if x != "." and x in seen:
                    return False
                seen.add(x)
    return True
''',
    "zigzag_conversion": '''"""Simulate row by row - standard."""
def convert(s: str, num_rows: int) -> str:
    if num_rows == 1:
        return s
    rows = [""] * num_rows
    r, step = 0, 1
    for c in s:
        rows[r] += c
        r += step
        if r == 0 or r == num_rows - 1:
            step = -step
    return "".join(rows)
''',
}

# Skyline uses sortedcontainers - avoid that dependency; use a simple multiset with list
SOLUTIONS["skyline_problem"] = '''"""Skyline: use list as multiset for active heights O(n^2) per event."""
def get_skyline(buildings: list[list[int]]) -> list[list[int]]:
    events = []
    for L, R, H in buildings:
        events.append((L, -H))
        events.append((R, H))
    events.sort(key=lambda x: (x[0], x[1]))
    active = [0]
    prev = 0
    out = []
    for x, h in events:
        if h < 0:
            active.append(-h)
        else:
            active.remove(h)
        cur = max(active) if active else 0
        if cur != prev:
            out.append([x, cur])
            prev = cur
    return out
'''

TEST_TEMPLATE = '''"""
Tests for {title}. Load solution from BENCHMARK_SOLUTION or same-dir solution.py.
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
{entry_attr}
'''

# One or more test lines per slug (indented for def test_example(): body)
EXAMPLE_TESTS = {
    "three_sum": "assert sorted([tuple(x) for x in three_sum([-1,0,1,2,-1,-4])]) == sorted([tuple(x) for x in [[-1,-1,2],[-1,0,1]]])",
    "three_sum_closest": "assert three_sum_closest([-1, 2, 1, -4], 1) == 2",
    "four_sum": "assert sorted([tuple(x) for x in four_sum([1,0,-1,0,-2,2], 0)]) == sorted([tuple(x) for x in [[-2,-1,1,2],[-2,0,0,2],[-1,0,0,1]]])",
    "add_digits": "assert add_digits(38) == 2",
    "additive_number": "assert is_additive_number('112358') is True",
    "burst_balloons": "assert max_coins([3, 1, 5, 8]) == 167",
    "combination_sum_ii": "assert combination_sum2([10,1,2,7,6,1,5], 8) == [[1,1,6],[1,2,5],[1,7],[2,6]]",
    "container_with_most_water": "assert max_area([1,8,6,2,5,4,8,3,7]) == 49",
    "convert_sorted_list_to_bst": "h = solution.ListNode(-10); h.next = solution.ListNode(-3); h.next.next = solution.ListNode(0); h.next.next.next = solution.ListNode(5); h.next.next.next.next = solution.ListNode(9); t = sorted_list_to_bst(h); assert t is not None and t.val == 0",
    "count_smaller_after_self": "assert count_smaller([5,2,6,1]) == [2,1,1,0]",
    "delete_node_in_linked_list": "n = solution.ListNode(5); n.next = solution.ListNode(1); delete_node(n); assert n.val == 1",
    "divide_two_integers": "assert divide(10, 3) == 3",
    "search_range": "assert search_range([5,7,7,8,8,10], 8) == [3,4]",
    "find_min_rotated": "assert find_min([3,4,5,1,2]) == 1",
    "find_peak_element": "assert find_peak_element([1,2,3,1]) in (2, 3)",
    "gray_code": "assert len(gray_code(2)) == 4 and set(gray_code(2)) == {0,1,2,3}",
    "integer_to_roman": "assert int_to_roman(3) == 'III'",
    "kth_smallest_sorted_matrix": "assert kth_smallest([[1,5,9],[10,11,13],[12,13,15]], 8) == 13",
    "largest_number": "assert largest_number([10,2]) == '210'",
    "longest_increasing_subsequence": "assert length_of_lis([10,9,2,5,3,7,101,18]) == 4",
    "longest_palindromic_substring": "assert longest_palindrome('babad') in ('bab', 'aba')",
    "longest_substring_no_repeat": "assert length_of_longest_substring('abcabcbb') == 3",
    "lru_cache": "c = LRUCache(2); c.put(1,1); c.put(2,2); assert c.get(1) == 1; c.put(3,3); assert c.get(2) == -1",
    "merge_intervals": "assert merge([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]",
    "min_stack": "s = MinStack(); s.push(-2); s.push(0); s.push(-3); assert s.get_min() == -3; s.pop(); assert s.top() == 0",
    "nim_game": "assert can_win_nim(4) is False",
    "n_queens": "assert len(solve_n_queens(4)) == 2",
    "n_queens_ii": "assert total_n_queens(4) == 2",
    "number_of_1_bits": "assert hamming_weight(11) == 3",
    "palindrome_number": "assert is_palindrome(121) is True",
    "pascals_triangle": "assert generate(5)[-1] == [1,4,6,4,1]",
    "permutation_sequence": "assert get_permutation(3, 3) == '213'",
    "permutations": "assert len(permute([1,2,3])) == 6",
    "permutations_ii": "assert len(permute_unique([1,1,2])) == 3",
    "pow_x_n": "assert abs(my_pow(2.0, 10) - 1024.0) < 1e-5",
    "power_of_two": "assert is_power_of_two(16) is True",
    "rectangle_area": "assert compute_area(-3,0,3,4,0,-1,9,2) == 45",
    "remove_invalid_parentheses": "out = remove_invalid_parentheses('()())()'); assert '()()()' in out and '(())()' in out",
    "remove_nth_from_end": "d = solution.ListNode(1); d.next = solution.ListNode(2); r = remove_nth_from_end(d, 2); assert r.val == 2",
    "restore_ip_addresses": "assert '255.255.11.135' in restore_ip_addresses('25525511135')",
    "reverse_bits": "assert reverse_bits(43261596) == 964176192",
    "reverse_integer": "assert reverse(123) == 321",
    "reverse_nodes_k_group": "h = solution.ListNode(1); h.next = solution.ListNode(2); h.next.next = solution.ListNode(3); h.next.next.next = solution.ListNode(4); r = reverse_k_group(h, 2); assert r.val == 2 and r.next.val == 1",
    "roman_to_integer": "assert roman_to_int('III') == 3",
    "rotate_image": "m = [[1,2,3],[4,5,6],[7,8,9]]; rotate(m); assert m[0] == [7,4,1]",
    "russian_doll_envelopes": "assert max_envelopes([[5,4],[6,4],[6,7],[2,3]]) == 3",
    "search_rotated_sorted_array": "assert search([4,5,6,7,0,1,2], 0) == 4",
    "search_insert_position": "assert search_insert([1,3,5,6], 5) == 2",
    "sort_list": "h = solution.ListNode(4); h.next = solution.ListNode(2); h.next.next = solution.ListNode(1); h.next.next.next = solution.ListNode(3); r = sort_list(h); assert r.val == 1 and r.next.val == 2",
    "spiral_matrix_ii": "assert generate_matrix(3) == [[1,2,3],[8,9,4],[7,6,5]]",
    "sqrt_x": "assert my_sqrt(8) == 2",
    "string_to_integer_atoi": "assert my_atoi('42') == 42",
    "subsets": "assert len(subsets([1,2,3])) == 8",
    "subsets_ii": "assert len(subsets_with_dup([1,2,2])) == 6",
    "swap_nodes_in_pairs": "h = solution.ListNode(1); h.next = solution.ListNode(2); h.next.next = solution.ListNode(3); r = swap_pairs(h); assert r.val == 2 and r.next.val == 1",
    "skyline_problem": "assert get_skyline([[2,9,10],[3,7,15],[5,12,12],[15,20,10],[19,24,8]]) == [[2,10],[3,15],[7,12],[12,0],[15,10],[20,8],[24,0]]",
    "valid_parentheses": "assert is_valid('()[]{}') is True",
    "valid_sudoku": "b = [['5','3','.','.','7','.','.','.','.'],['6','.','.','1','9','5','.','.','.'],['.','9','8','.','.','.','.','6','.'],['8','.','.','.','6','.','.','.','3'],['4','.','.','8','.','3','.','.','1'],['7','.','.','.','2','.','.','.','6'],['.','6','.','.','.','.','2','8','.'],['.','.','.','4','1','9','.','.','5'],['.','.','.','.','8','.','.','7','9']]; assert is_valid_sudoku(b) is True",
    "zigzag_conversion": "assert convert('PAYPALISHIRING', 3) == 'PAHNAPLSIIGYIR'",
}

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    for title, slug, leetcode_id, difficulty, entry_fn, exp_time, exp_space in PROBLEMS:
        if slug == "two_sum":
            continue  # already exists
        dirpath = os.path.join(root, slug)
        os.makedirs(dirpath, exist_ok=True)
        spec = {
            "slug": slug,
            "leetcode_id": leetcode_id,
            "title": title,
            "difficulty": difficulty,
            "expected_time": exp_time,
            "expected_space": exp_space,
            "entry_function": entry_fn,
        }
        with open(os.path.join(dirpath, "spec.json"), "w") as f:
            json.dump(spec, f, indent=2)
        sol = SOLUTIONS.get(slug)
        if sol:
            with open(os.path.join(dirpath, "solution.py"), "w") as f:
                f.write(sol)
            entry_attr = f"{entry_fn} = getattr(solution, '{entry_fn}')"
            test_content = TEST_TEMPLATE.format(title=title, entry_attr=entry_attr)
            test_body = EXAMPLE_TESTS.get(slug, "pass  # TODO add test")
            test_content += "\ndef test_example():\n    " + test_body.replace("\n", "\n    ") + "\n"
            with open(os.path.join(dirpath, f"test_{slug}.py"), "w") as f:
                f.write(test_content)
    print("Generated all problem folders. Add concrete test cases to each test_<slug>.py.")

if __name__ == "__main__":
    main()