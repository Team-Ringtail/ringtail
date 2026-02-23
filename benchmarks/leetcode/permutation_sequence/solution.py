"""Build by computing next digit - can be O(n) with factorial."""
def get_permutation(n: int, k: int) -> str:
    from itertools import permutations
    perms = list(permutations(range(1, n + 1)))
    return "".join(str(x) for x in perms[k - 1])
