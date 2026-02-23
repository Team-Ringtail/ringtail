"""Sub-optimal: for each index scan right O(n^2) instead of merge sort / BST."""
def count_smaller(nums: list[int]) -> list[int]:
    n = len(nums)
    out = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            if nums[j] < nums[i]:
                out[i] += 1
    return out
