"""Scan left to right add/subtract."""
def roman_to_int(s: str) -> int:
    m = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    out = 0
    for i in range(len(s)):
        v = m[s[i]]
        if i + 1 < len(s) and m[s[i+1]] > v:
            out -= v
        else:
            out += v
    return out
