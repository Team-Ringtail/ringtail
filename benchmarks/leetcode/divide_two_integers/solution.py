"""Sub-optimal: subtract divisor repeatedly O(dividend/divisor) instead of bit shift O(log n)."""
def divide(dividend: int, divisor: int) -> int:
    neg = (dividend < 0) != (divisor < 0)
    a, b = abs(dividend), abs(divisor)
    q = 0
    while a >= b:
        a -= b
        q += 1
    q = -q if neg else q
    return max(-2**31, min(2**31 - 1, q))
