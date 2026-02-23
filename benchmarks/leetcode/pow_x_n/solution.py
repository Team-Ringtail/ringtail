"""Sub-optimal: linear multiply O(n) instead of binary exponentiation O(log n)."""
def my_pow(x: float, n: int) -> float:
    if n < 0:
        x, n = 1/x, -n
    out = 1.0
    for _ in range(n):
        out *= x
    return out
