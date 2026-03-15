def add_digits(num: int = 987654321) -> int:
    if num == 0:
        return 0
    return 1 + (num - 1) % 9


def is_even(num: int = 2) -> bool:
    return num % 2 == 0
