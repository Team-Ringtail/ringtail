"""BFS remove one char at a time - standard."""
def remove_invalid_parentheses(s: str) -> list[str]:
    def valid(t):
        c = 0
        for x in t:
            if x == "(": c += 1
            elif x == ")": c -= 1
            if c < 0: return False
        return c == 0
    level = {s}
    while level:
        ok = [t for t in level if valid(t)]
        if ok:
            return list(set(ok))
        level = {t[:i] + t[i+1:] for t in level for i in range(len(t)) if t[i] in "()"}
    return [""]
