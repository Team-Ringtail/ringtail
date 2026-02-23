"""Count only - same backtrack."""
def total_n_queens(n: int) -> int:
    count = 0
    col, diag1, diag2 = set(), set(), set()
    def place(row: int):
        nonlocal count
        if row == n:
            count += 1
            return
        for c in range(n):
            if c in col or (row - c) in diag1 or (row + c) in diag2:
                continue
            col.add(c); diag1.add(row - c); diag2.add(row + c)
            place(row + 1)
            col.discard(c); diag1.discard(row - c); diag2.discard(row + c)
    place(0)
    return count
