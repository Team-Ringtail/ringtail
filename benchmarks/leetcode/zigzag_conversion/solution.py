"""Simulate row by row - standard."""
def convert(s: str, num_rows: int) -> str:
    if num_rows == 1:
        return s
    rows = [""] * num_rows
    r, step = 0, 1
    for c in s:
        rows[r] += c
        r += step
        if r == 0 or r == num_rows - 1:
            step = -step
    return "".join(rows)
