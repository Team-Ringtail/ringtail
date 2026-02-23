"""Reverse k at a time - standard."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_k_group(head: ListNode, k: int) -> ListNode:
    def rev(start, end):
        prev, cur = end, start
        while cur != end:
            nxt = cur.next
            cur.next = prev
            prev, cur = cur, nxt
        return prev
    dummy = ListNode(0, head)
    gprev = dummy
    while True:
        kth = gprev
        for _ in range(k):
            kth = kth.next
            if not kth:
                return dummy.next
        gnext = kth.next
        old_start = gprev.next
        gprev.next = rev(gprev.next, kth.next)
        old_start.next = gnext
        gprev = old_start
