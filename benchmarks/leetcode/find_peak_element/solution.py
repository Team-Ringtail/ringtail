"""Sub-optimal: linear scan O(n) instead of binary search O(log n)."""
def find_peak_element(nums: list[int]) -> int:
    for i in range(len(nums)):
        left = nums[i-1] if i > 0 else float("-inf")
        right = nums[i+1] if i < len(nums)-1 else float("-inf")
        if nums[i] >= left and nums[i] >= right:
            return i
    return 0
