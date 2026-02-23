"""Two stacks: one for values, one for minimums. O(1) ops."""
class MinStack:
    def __init__(self):
        self.stk = []
        self.mn = []
    def push(self, val: int) -> None:
        self.stk.append(val)
        self.mn.append(val if not self.mn else min(self.mn[-1], val))
    def pop(self) -> None:
        self.stk.pop()
        self.mn.pop()
    def top(self) -> int:
        return self.stk[-1]
    def get_min(self) -> int:
        return self.mn[-1]
