"""Sub-optimal: linear scan O(n) instead of two binary searches O(log n)."""
def search_range(nums: list[int], target: int) -> list[int]:
    lo, hi = -1, -1
    for i, x in enumerate(nums):
        if x == target:
            if lo == -1:
                lo = i
            hi = i
    return [lo, hi]
