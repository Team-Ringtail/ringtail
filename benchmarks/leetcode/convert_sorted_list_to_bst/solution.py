"""Sub-optimal: build list to array then recursive O(n log n) instead of in-order O(n)."""
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def sorted_list_to_bst(head: ListNode) -> TreeNode:
    arr = []
    while head:
        arr.append(head.val)
        head = head.next
    def build(l: int, r: int) -> TreeNode:
        if l > r:
            return None
        mid = (l + r) // 2
        node = TreeNode(arr[mid])
        node.left = build(l, mid - 1)
        node.right = build(mid + 1, r)
        return node
    return build(0, len(arr) - 1) if arr else None
