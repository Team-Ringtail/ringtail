"""Backtrack row by row - standard."""
def solve_n_queens(n: int) -> list[list[str]]:
    out = []
    col, diag1, diag2 = set(), set(), set()
    def place(row: int, board: list):
        if row == n:
            qs = set((i, board[i]) for i in range(n))
            out.append(["".join("Q" if (r, c) in qs else "." for c in range(n)) for r in range(n)])
            return
        for c in range(n):
            if c in col or (row - c) in diag1 or (row + c) in diag2:
                continue
            col.add(c); diag1.add(row - c); diag2.add(row + c)
            board.append(c)
            place(row + 1, board)
            board.pop()
            col.discard(c); diag1.discard(row - c); diag2.discard(row + c)
    place(0, [])
    return out
