"""Check rows, cols, boxes - standard."""
def is_valid_sudoku(board: list[list[str]]) -> bool:
    for r in range(9):
        seen = set()
        for c in range(9):
            x = board[r][c]
            if x != "." and x in seen:
                return False
            seen.add(x)
    for c in range(9):
        seen = set()
        for r in range(9):
            x = board[r][c]
            if x != "." and x in seen:
                return False
            seen.add(x)
    for box in range(9):
        br, bc = (box // 3) * 3, (box % 3) * 3
        seen = set()
        for i in range(3):
            for j in range(3):
                x = board[br+i][bc+j]
                if x != "." and x in seen:
                    return False
                seen.add(x)
    return True
