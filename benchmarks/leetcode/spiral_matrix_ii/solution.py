"""Layer by layer - standard."""
def generate_matrix(n: int) -> list[list[int]]:
    m = [[0] * n for _ in range(n)]
    v, top, bottom, left, right = 1, 0, n - 1, 0, n - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            m[top][c] = v; v += 1
        top += 1
        for r in range(top, bottom + 1):
            m[r][right] = v; v += 1
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                m[bottom][c] = v; v += 1
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                m[r][left] = v; v += 1
            left += 1
    return m
