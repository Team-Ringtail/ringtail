"""Skyline: use list as multiset for active heights O(n^2) per event."""
def get_skyline(buildings: list[list[int]]) -> list[list[int]]:
    events = []
    for L, R, H in buildings:
        events.append((L, -H))
        events.append((R, H))
    events.sort(key=lambda x: (x[0], x[1]))
    active = [0]
    prev = 0
    out = []
    for x, h in events:
        if h < 0:
            active.append(-h)
        else:
            active.remove(h)
        cur = max(active) if active else 0
        if cur != prev:
            out.append([x, cur])
            prev = cur
    return out
