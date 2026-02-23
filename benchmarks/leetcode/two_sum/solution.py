"""
Reference (unoptimized) solution for LeetCode 1 - Two Sum.
Brute force O(n^2) so there is room to optimize to O(n) with a hash map.
"""


def two_sum(nums: list[int], target: int) -> list[int]:
    """Return indices of two numbers that add up to target."""
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
