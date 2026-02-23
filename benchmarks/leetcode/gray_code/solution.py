"""Sub-optimal: generate all 2^n and convert to Gray (still O(2^n) time)."""
def gray_code(n: int) -> list[int]:
    if n == 0:
        return [0]
    out = []
    for i in range(2**n):
        g = i ^ (i >> 1)
        out.append(g)
    return out
