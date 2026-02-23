"""Sub-optimal: try all triples O(n^3)."""
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
