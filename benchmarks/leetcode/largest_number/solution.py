"""Correct but compare as string concatenation (standard approach)."""
def largest_number(nums: list[int]) -> str:
    from functools import cmp_to_key
    def cmp(a: str, b: str):
        return -1 if a + b > b + a else (1 if a + b < b + a else 0)
    s = sorted([str(x) for x in nums], key=cmp_to_key(cmp))
    out = "".join(s).lstrip("0")
    return out or "0"
