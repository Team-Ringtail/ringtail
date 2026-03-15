def add_digits(num: int = 987654321) -> int:
    while num >= 10:
        num = sum(int(d) for d in str(num))
    return num


def is_even(num: int = 2) -> bool:
    return num % 2 == 0
