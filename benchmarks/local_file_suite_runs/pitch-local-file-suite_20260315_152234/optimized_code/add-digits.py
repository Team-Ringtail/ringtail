def add_digits(num: int) -> int:
    if num < 10:
        return num
    if num == 0:
        return 0
    return 1 + (num - 1) % 9
