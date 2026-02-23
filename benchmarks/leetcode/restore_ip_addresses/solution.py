"""Backtrack try 1,2,3 digit segments."""
def restore_ip_addresses(s: str) -> list[str]:
    out = []
    def bt(start: int, parts: list):
        if len(parts) == 4:
            if start == len(s):
                out.append(".".join(parts))
            return
        for w in (1, 2, 3):
            if start + w > len(s):
                break
            seg = s[start:start+w]
            if (seg[0] == "0" and len(seg) > 1) or int(seg) > 255:
                continue
            parts.append(seg)
            bt(start + w, parts)
            parts.pop()
    bt(0, [])
    return out
