"""Sub-optimal: try all orders O(n!) with memo on (tuple of remaining)."""
def max_coins(nums: list[int]) -> int:
    from functools import lru_cache
    A = [1] + [x for x in nums] + [1]
    @lru_cache(maxsize=None)
    def dp(i: int, j: int) -> int:
        if i > j:
            return 0
        best = 0
        for k in range(i, j + 1):
            best = max(best, A[i-1] * A[k] * A[j+1] + dp(i, k-1) + dp(k+1, j))
        return best
    return dp(1, len(A) - 2)
