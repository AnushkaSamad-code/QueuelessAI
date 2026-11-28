"""Isolated educational operations over QueueLess' manual data structures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from backend.ds.bst import BSTNode, TokenBST
from backend.ds.custom_array import TokenArray
from backend.ds.linked_list import ServiceLinkedList
from backend.ds.priority_queue import ScheduledToken, SchedulingPriorityQueue


@dataclass(frozen=True)
class PlaygroundItem:
    token_id: str
    value: str


class DuplicateStructureItem(ValueError):
    """Raised when an operation would introduce a duplicate key."""


class DataStructurePlayground:
    """Owns disposable structures separate from live operational queue state."""

    def __init__(self) -> None:
        self.array: TokenArray[PlaygroundItem] = TokenArray(
            capacity=4,
            maximum_capacity=128,
        )
        self.linked_list: ServiceLinkedList[PlaygroundItem] = ServiceLinkedList()
        self.priority_queue: SchedulingPriorityQueue[PlaygroundItem] = (
            SchedulingPriorityQueue()
        )
        self.bst: TokenBST[PlaygroundItem] = TokenBST()
        self._next_array_id = 1
        self._next_linked_id = 1
        self._next_priority_id = 1

    def array_operation(
        self,
        operation: str,
        value: str | None = None,
        index: int | None = None,
    ) -> dict[str, object]:
        if operation == "insert":
            item_value = _required_value(value)
            insert_index = self.array.size if index is None else index
            item = self._new_item("A", self._next_array_id, item_value)
            self.array.insert_at(insert_index, item)
            self._next_array_id += 1
            message = f"Inserted {item.value} at index {insert_index}."
            complexity = "O(n)"
        elif operation == "delete":
            if index is None:
                raise ValueError("An index is required to delete an array item.")
            removed = self.array.delete_at(index)
            message = f"Deleted {removed.value} at index {index}."
            complexity = "O(n)"
        elif operation == "search":
            item_value = _required_value(value)
            found_index = self.array.linear_search(
                lambda item: item.value.casefold() == item_value.casefold()
            )
            message = (
                f"Found {item_value} at index {found_index}."
                if found_index is not None
                else f"{item_value} was not found."
            )
            complexity = "O(n)"
        elif operation == "update":
            if index is None:
                raise ValueError("An index is required to update an array item.")
            item_value = _required_value(value)
            current = self.array.get(index)
            self.array.update_at(
                index,
                PlaygroundItem(token_id=current.token_id, value=item_value),
            )
            message = f"Updated index {index} to {item_value}."
            complexity = "O(1)"
        elif operation == "traverse":
            message = "Array traversed from index 0 to the final occupied slot."
            complexity = "O(n)"
        else:
            raise ValueError("Unsupported array operation.")
        return self._result("Array", operation, message, complexity)

    def linked_list_operation(
        self,
        operation: str,
        value: str | None = None,
        position: int | None = None,
        item_id: str | None = None,
    ) -> dict[str, object]:
        if operation in ("insert_beginning", "insert_end", "insert_position"):
            item_value = _required_value(value)
            item = self._new_item("L", self._next_linked_id, item_value)
            if operation == "insert_beginning":
                self.linked_list.insert_head(item)
                location = "beginning"
            elif operation == "insert_end":
                self.linked_list.insert_tail(item)
                location = "end"
            else:
                if position is None:
                    raise ValueError("A position is required for positional insertion.")
                self.linked_list.insert_at(position, item)
                location = f"position {position}"
            self._next_linked_id += 1
            message = f"Inserted {item.value} ({item.token_id}) at the {location}."
            complexity = "O(1)" if operation != "insert_position" else "O(n)"
        elif operation == "delete":
            key = _required_value(item_id, "Item ID")
            removed = self.linked_list.delete_by_token_id(key)
            message = f"Deleted {removed.value} ({removed.token_id})."
            complexity = "O(n)"
        elif operation == "search":
            item_value = _required_value(value)
            found = self.linked_list.find(
                lambda item: item.value.casefold() == item_value.casefold()
            )
            message = (
                f"Found {found.value} ({found.token_id})."
                if found is not None
                else f"{item_value} was not found."
            )
            complexity = "O(n)"
        elif operation == "traverse":
            message = "Linked list traversed from head to tail."
            complexity = "O(n)"
        else:
            raise ValueError("Unsupported linked-list operation.")
        return self._result("Linked List", operation, message, complexity)

    def priority_queue_operation(
        self,
        operation: str,
        value: str | None = None,
        priority: int | None = None,
        item_id: str | None = None,
    ) -> dict[str, object]:
        if operation == "enqueue":
            item_value = _required_value(value)
            if priority is None:
                raise ValueError("A priority from 0 to 9 is required.")
            item = self._new_item("P", self._next_priority_id, item_value)
            self.priority_queue.enqueue(
                item,
                item.token_id,
                priority,
                datetime.now(timezone.utc),
            )
            self._next_priority_id += 1
            message = f"Enqueued {item.value} ({item.token_id}) at priority {priority}."
            complexity = "O(n) including duplicate-key validation; heap insertion is O(log n)."
        elif operation == "dequeue":
            removed = self.priority_queue.dequeue(datetime.now(timezone.utc))
            message = f"Dequeued {removed.item.value} ({removed.token_id})."
            complexity = "O(log n)"
        elif operation == "peek":
            item = self.priority_queue.peek(datetime.now(timezone.utc))
            message = f"Next item is {item.item.value} ({item.token_id})."
            complexity = "O(1)"
        elif operation == "update_priority":
            key = _required_value(item_id, "Item ID")
            if priority is None:
                raise ValueError("A priority from 0 to 9 is required.")
            self.priority_queue.update_priority(key, priority)
            message = f"Updated {key} to priority {priority}."
            complexity = "O(n) lookup plus O(log n) heap repair."
        elif operation == "display":
            message = "Displayed the current heap in level-order storage."
            complexity = "O(n)"
        else:
            raise ValueError("Unsupported priority-queue operation.")
        return self._result("Priority Queue", operation, message, complexity)

    def bst_operation(
        self,
        operation: str,
        key: str | None = None,
        value: str | None = None,
    ) -> dict[str, object]:
        if operation == "insert":
            item_key = _required_value(key, "Key")
            item_value = _required_value(value, "Value")
            item = PlaygroundItem(token_id=item_key, value=item_value)
            try:
                self.bst.insert(item_key, item)
            except ValueError as exc:
                raise DuplicateStructureItem(f"Key {item_key} already exists.") from exc
            message = f"Inserted key {item_key}."
            complexity = "O(log n) average; O(n) worst case."
        elif operation == "search":
            item_key = _required_value(key, "Key")
            found = self.bst.search(item_key)
            message = (
                f"Found {item_key}: {found.value}."
                if found is not None
                else f"Key {item_key} was not found."
            )
            complexity = "O(log n) average; O(n) worst case."
        elif operation == "delete":
            item_key = _required_value(key, "Key")
            try:
                removed = self.bst.delete(item_key)
            except KeyError as exc:
                raise KeyError(f"Key {item_key} was not found.") from exc
            message = f"Deleted key {item_key} ({removed.value})."
            complexity = "O(log n) average; O(n) worst case."
        elif operation in ("inorder", "preorder", "postorder"):
            message = f"Completed {operation} traversal."
            complexity = "O(n)"
        else:
            raise ValueError("Unsupported BST operation.")
        return self._result("BST", operation, message, complexity)

    def snapshot(self) -> dict[str, object]:
        array_elements = [asdict(item) for item in self.array.traverse()]
        now = datetime.now(timezone.utc)
        priority_items = [
            {
                "index": index,
                "token_id": entry.token_id,
                "value": entry.item.value,
                "base_priority": entry.base_priority,
                "effective_priority": self.priority_queue.effective_priority(
                    entry,
                    now,
                ),
                "arrival_timestamp": entry.arrival_timestamp.isoformat(),
            }
            for index, entry in enumerate(self.priority_queue.traverse_heap())
        ]
        return {
            "array": {
                "size": self.array.size,
                "capacity": self.array.capacity,
                "elements": array_elements,
            },
            "linked_list": [asdict(item) for item in self.linked_list.traverse()],
            "priority_queue": priority_items,
            "bst": {
                "size": self.bst.size,
                "root": self._tree_snapshot(self.bst.root),
                "inorder": [asdict(item) for item in self.bst.inorder()],
                "preorder": [asdict(item) for item in self.bst.preorder()],
                "postorder": [asdict(item) for item in self.bst.postorder()],
            },
        }

    def _result(
        self,
        structure: str,
        operation: str,
        message: str,
        complexity: str,
    ) -> dict[str, object]:
        return {
            "structure": structure,
            "operation": operation,
            "message": message,
            "complexity": complexity,
            "snapshot": self.snapshot(),
        }

    @staticmethod
    def _new_item(prefix: str, sequence: int, value: str) -> PlaygroundItem:
        return PlaygroundItem(token_id=f"{prefix}{sequence:03d}", value=value)

    @classmethod
    def _tree_snapshot(
        cls,
        node: BSTNode[PlaygroundItem] | None,
    ) -> dict[str, object] | None:
        if node is None:
            return None
        return {
            "key": node.token_id,
            "value": node.payload.value,
            "left": cls._tree_snapshot(node.left),
            "right": cls._tree_snapshot(node.right),
        }


def _required_value(value: str | None, field_name: str = "Value") -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} is required.")
    return value.strip()
