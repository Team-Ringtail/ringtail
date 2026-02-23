"""Generate row by row - standard."""
def generate(num_rows: int) -> list[list[int]]:
    if num_rows <= 0:
        return []
    out = [[1]]
    for _ in range(num_rows - 1):
        prev = out[-1]
        row = [1] + [prev[i] + prev[i+1] for i in range(len(prev)-1)] + [1]
        out.append(row)
    return out
