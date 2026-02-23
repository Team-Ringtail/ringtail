"""Backtrack - standard."""
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
