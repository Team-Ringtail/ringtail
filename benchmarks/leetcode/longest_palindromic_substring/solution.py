"""Sub-optimal: try all substrings O(n^3) instead of expand O(n^2)."""
def longest_palindrome(s: str) -> str:
    n = len(s)
    best = ""
    for i in range(n):
        for j in range(i, n):
            sub = s[i:j+1]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best
