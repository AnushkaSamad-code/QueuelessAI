"""Singly linked counter queue and completed-history implementation."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar


T = TypeVar("T")


class Node(Generic[T]):
    """Singly linked node."""

    def __init__(self, data: T, next: "Node[T] | None" = None) -> None:
        self.data = data
        self.next = next

    @property
    def item(self) -> T:
        return self.data


LinkedNode = Node


class ServiceLinkedList(Generic[T]):
    def __init__(self) -> None:
        self.head: LinkedNode[T] | None = None
        self.tail: LinkedNode[T] | None = None
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    @property
    def length(self) -> int:
        """Return the number of nodes in the list."""

        return self._size

    def insert_head(self, data: T) -> None:
        """Insert data before the current head."""

        node = Node(data, self.head)
        self.head = node
        if self.tail is None:
            self.tail = node
        self._size += 1

    def insert_tail(self, data: T) -> None:
        """Append data to the end of the list."""

        node = Node(data)
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._size += 1

    def search(self, token_id: str) -> T | None:
        """Return payload whose token_id matches."""

        current = self.head
        while current is not None:
            if self._token_id(current.data) == token_id:
                return current.data
            current = current.next
        return None

    def delete_by_token_id(self, token_id: str) -> T:
        """Delete and return the first node matching token_id."""

        if self.head is None:
            raise KeyError(token_id)
        if self._token_id(self.head.data) == token_id:
            return self.pop_front()
        previous = self.head
        while previous.next is not None:
            if self._token_id(previous.next.data) == token_id:
                removed = previous.next
                previous.next = removed.next
                if removed is self.tail:
                    self.tail = previous
                removed.next = None
                self._size -= 1
                return removed.data
            previous = previous.next
        raise KeyError(token_id)

    @staticmethod
    def _token_id(data: object) -> str | None:
        if hasattr(data, "token_id"):
            return str(getattr(data, "token_id"))
        if isinstance(data, dict):
            value = data.get("token_id")
            return str(value) if value is not None else None
        return None

    def append(self, item: T) -> None:
        self.insert_tail(item)

    def prepend(self, item: T) -> None:
        self.insert_head(item)

    def insert_at(self, index: int, item: T) -> None:
        """Insert ``item`` at a zero-based position."""

        if index < 0 or index > self._size:
            raise IndexError("linked-list index out of range")
        if index == 0:
            self.insert_head(item)
            return
        if index == self._size:
            self.insert_tail(item)
            return
        previous = self.head
        position = 0
        while previous is not None and position < index - 1:
            previous = previous.next
            position += 1
        if previous is None:
            raise RuntimeError("linked-list invariant violated")
        previous.next = Node(item, previous.next)
        self._size += 1

    def peek_front(self) -> T:
        if self.head is None:
            raise LookupError("linked list is empty")
        return self.head.item

    def pop_front(self) -> T:
        if self.head is None:
            raise LookupError("linked list is empty")
        node = self.head
        self.head = node.next
        if self.head is None:
            self.tail = None
        node.next = None
        self._size -= 1
        return node.item

    def delete_at(self, index: int) -> T:
        if index < 0 or index >= self._size:
            raise IndexError("linked-list index out of range")
        if index == 0:
            return self.pop_front()
        previous = self.head
        position = 0
        while previous is not None and position < index - 1:
            previous = previous.next
            position += 1
        if previous is None or previous.next is None:
            raise RuntimeError("linked-list invariant violated")
        removed = previous.next
        previous.next = removed.next
        if removed is self.tail:
            self.tail = previous
        removed.next = None
        self._size -= 1
        return removed.item

    def find(self, predicate: object) -> T | None:
        if not callable(predicate):
            raise TypeError("predicate must be callable")
        current = self.head
        while current is not None:
            if predicate(current.item):
                return current.item
            current = current.next
        return None

    def traverse(self) -> Iterator[T]:
        current = self.head
        while current is not None:
            yield current.item
            current = current.next
