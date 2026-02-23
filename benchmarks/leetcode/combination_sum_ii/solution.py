"""Sub-optimal: generate all subsets then filter duplicates (still correct)."""
def combination_sum2(candidates: list[int], target: int) -> list[list[int]]:
    out = []
    candidates.sort()
    def bt(start: int, path: list, s: int):
        if s == target:
            out.append(path[:])
            return
        if s > target:
            return
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i-1]:
                continue
            path.append(candidates[i])
            bt(i + 1, path, s + candidates[i])
            path.pop()
    bt(0, [], 0)
    return out
