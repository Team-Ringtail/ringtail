def slow_sum(n: int = 50000) -> int:
    if n <= 0:
        return 0
    return n * (n - 1) // 2


def clamp_step(value: int = 3, low: int = 0, high: int = 10) -> int:
    if value < low:
        return low
    if value > high:
        return high
    return value
