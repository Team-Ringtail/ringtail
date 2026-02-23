"""Sub-optimal: linear scan O(n) instead of binary search."""
def search(nums: list[int], target: int) -> int:
    for i, x in enumerate(nums):
        if x == target:
            return i
    return -1
