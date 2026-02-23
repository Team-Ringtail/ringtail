"""Standard O(1) copy-next approach (problem is inherently O(1))."""
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None

def delete_node(node: ListNode) -> None:
    node.val = node.next.val
    node.next = node.next.next
