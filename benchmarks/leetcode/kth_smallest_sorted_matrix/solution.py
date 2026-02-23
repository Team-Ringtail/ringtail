"""Sub-optimal: flatten and sort O(n^2 log n) instead of heap/binary search."""
def kth_smallest(matrix: list[list[int]], k: int) -> int:
    flat = []
    for row in matrix:
        flat.extend(row)
    flat.sort()
    return flat[k - 1]
