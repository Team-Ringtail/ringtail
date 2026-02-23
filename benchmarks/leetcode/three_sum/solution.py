"""Sub-optimal: brute force O(n^3) instead of two-pointer O(n^2)."""
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
