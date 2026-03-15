def slow_sum(n: int = 50000) -> int:
    total = 0
    for i in range(n):
        total += i
    return total


def clamp_step(value: int = 3, low: int = 0, high: int = 10) -> int:
    if value < low:
        return low
    if value > high:
        return high
    return value
