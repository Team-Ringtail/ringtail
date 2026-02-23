"""Stack - standard."""
def is_valid(s: str) -> bool:
    st = []
    m = {")": "(", "}": "{", "]": "["}
    for c in s:
        if c in "({[":
            st.append(c)
        else:
            if not st or st[-1] != m.get(c):
                return False
            st.pop()
    return len(st) == 0
