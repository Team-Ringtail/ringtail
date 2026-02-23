"""Loop over bits O(32)."""
def hamming_weight(n: int) -> int:
    n = n & 0xFFFFFFFF
    c = 0
    while n:
        c += n & 1
        n >>= 1
    return c
