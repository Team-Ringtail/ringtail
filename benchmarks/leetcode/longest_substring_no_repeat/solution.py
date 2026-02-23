"""Sub-optimal: check all substrings O(n^2) instead of sliding window O(n)."""
def length_of_longest_substring(s: str) -> int:
    n = len(s)
    best = 0
    for i in range(n):
        seen = set()
        for j in range(i, n):
            if s[j] in seen:
                break
            seen.add(s[j])
            best = max(best, j - i + 1)
    return best
