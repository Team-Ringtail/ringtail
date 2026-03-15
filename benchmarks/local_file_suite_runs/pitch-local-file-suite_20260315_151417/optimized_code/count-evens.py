def count_evens(nums: list[int]) -> int:
    return sum(1 for value in nums if value & 1 == 0)
