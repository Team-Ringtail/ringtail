def add_digits(num: int = 987654321) -> int:
    if num < 10:
        return num
    return 1 + (num - 1) % 9
