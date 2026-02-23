"""Convert to string and reverse."""
def reverse(x: int) -> int:
    sign = -1 if x < 0 else 1
    s = str(abs(x))[::-1]
    out = sign * int(s)
    return out if -2**31 <= out <= 2**31 - 1 else 0
