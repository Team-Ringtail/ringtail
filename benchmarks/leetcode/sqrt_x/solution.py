"""Sub-optimal: linear search O(x) instead of binary search O(log x)."""
def my_sqrt(x: int) -> int:
    if x <= 1:
        return x
    r = 1
    while r * r <= x:
        r += 1
    return r - 1
