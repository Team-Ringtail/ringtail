"""Bit by bit."""
def reverse_bits(n: int) -> int:
    n = n & 0xFFFFFFFF
    out = 0
    for _ in range(32):
        out = (out << 1) | (n & 1)
        n >>= 1
    return out
