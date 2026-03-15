from duplicate_scan import first_value, has_duplicates
from digit_math import add_digits, is_even
from fast_math import clamp
from slow_math import clamp_step, slow_sum


def test_slow_sum():
    assert slow_sum(0) == 0
    assert slow_sum(4) == 6
    assert slow_sum(-2) == 0


def test_clamp_step():
    assert clamp_step(5, 0, 10) == 5
    assert clamp_step(-1, 0, 10) == 0


def test_has_duplicates():
    assert has_duplicates([1, 2, 3, 1]) is True
    assert has_duplicates([1, 2, 3]) is False


def test_first_value():
    assert first_value([9, 8, 7]) == 9
    assert first_value([]) == -1


def test_add_digits():
    assert add_digits(38) == 2
    assert add_digits(0) == 0


def test_is_even():
    assert is_even(4) is True
    assert is_even(5) is False


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
