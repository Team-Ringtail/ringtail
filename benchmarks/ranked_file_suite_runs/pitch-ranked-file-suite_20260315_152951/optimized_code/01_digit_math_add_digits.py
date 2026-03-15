def add_digits(num: int) -> int:
    if num <= 0:
        return num
    return 1 + (num - 1) % 9
