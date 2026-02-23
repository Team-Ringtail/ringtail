"""Parse with strip and sign."""
def my_atoi(s: str) -> int:
    s = s.strip()
    if not s:
        return 0
    sign = 1
    if s[0] in "+-":
        sign = -1 if s[0] == "-" else 1
        s = s[1:]
    out = 0
    for c in s:
        if not c.isdigit():
            break
        out = out * 10 + int(c)
    out *= sign
    return max(-2**31, min(2**31 - 1, out))
