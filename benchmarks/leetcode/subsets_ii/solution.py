"""Backtrack with sort and skip duplicates."""
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
