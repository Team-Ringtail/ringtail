"""Sub-optimal: loop until single digit instead of O(1) formula."""
def add_digits(num: int) -> int:
    while num >= 10:
        num = sum(int(d) for d in str(num))
    return num
