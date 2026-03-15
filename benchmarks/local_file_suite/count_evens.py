def count_evens(nums: list[int]) -> int:
    total = 0
    for value in nums:
        if value % 2 == 0:
            total += 1
    return total
