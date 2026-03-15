def slow_sum(n: int = 50000) -> int:
    if n <= 0:
        return 0
    return n * (n - 1) // 2
