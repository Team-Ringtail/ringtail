"""Sub-optimal: copy to list, sort, rebuild O(n log n) time but O(n) extra space."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def sort_list(head: ListNode) -> ListNode:
    arr = []
    while head:
        arr.append(head.val)
        head = head.next
    arr.sort()
    dummy = ListNode(0)
    cur = dummy
    for v in arr:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next
