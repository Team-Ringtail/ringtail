"""Sub-optimal: brute force O(n^4)."""
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
