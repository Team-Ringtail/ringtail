"""Convert to string O(log n) - sub-optimal vs reverse half."""
def is_palindrome(x: int) -> bool:
    if x < 0:
        return False
    s = str(x)
    return s == s[::-1]
