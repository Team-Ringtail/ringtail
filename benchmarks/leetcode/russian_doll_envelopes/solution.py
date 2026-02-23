"""Sub-optimal: DP O(n^2) instead of LIS O(n log n)."""
def max_envelopes(envelopes: list[list[int]]) -> int:
    if not envelopes:
        return 0
    envelopes.sort(key=lambda x: (x[0], -x[1]))
    dp = [1] * len(envelopes)
    for i in range(1, len(envelopes)):
        for j in range(i):
            if envelopes[j][0] < envelopes[i][0] and envelopes[j][1] < envelopes[i][1]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
