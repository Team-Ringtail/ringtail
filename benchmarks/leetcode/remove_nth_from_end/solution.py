"""Two passes: count then remove."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def remove_nth_from_end(head: ListNode, n: int) -> ListNode:
    dummy = ListNode(0, head)
    cur = head
    L = 0
    while cur:
        L += 1
        cur = cur.next
    cur = dummy
    for _ in range(L - n):
        cur = cur.next
    cur.next = cur.next.next
    return dummy.next
