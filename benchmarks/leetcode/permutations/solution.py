"""Backtrack - standard."""
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
