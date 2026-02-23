"""Iterative swap pairs."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def swap_pairs(head: ListNode) -> ListNode:
    dummy = ListNode(0, head)
    prev = dummy
    while prev.next and prev.next.next:
        a, b = prev.next, prev.next.next
        prev.next = b
        a.next = b.next
        b.next = a
        prev = a
    return dummy.next
