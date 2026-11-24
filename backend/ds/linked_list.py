"""Singly linked counter queue and completed-history implementation."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar


T = TypeVar("T")


class LinkedNode(Generic[T]):
    def __init__(self, item: T) -> None:
        self.item = item
        self.next: LinkedNode[T] | None = None


class ServiceLinkedList(Generic[T]):
    def __init__(self) -> None:
        self.head: LinkedNode[T] | None = None
        self.tail: LinkedNode[T] | None = None
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def append(self, item: T) -> None:
        node = LinkedNode(item)
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._size += 1

    def prepend(self, item: T) -> None:
        node = LinkedNode(item)
        node.next = self.head
        self.head = node
        if self.tail is None:
            self.tail = node
        self._size += 1

    def insert_at(self, index: int, item: T) -> None:
        if index < 0 or index > self._size:
            raise IndexError("linked-list index out of range")
        if index == 0:
            self.prepend(item)
            return
        if index == self._size:
            self.append(item)
            return
        previous = self.head
        position = 0
        while previous is not None and position < index - 1:
            previous = previous.next
            position += 1
        if previous is None:
            raise RuntimeError("linked-list invariant violated")
        node = LinkedNode(item)
        node.next = previous.next
        previous.next = node
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
