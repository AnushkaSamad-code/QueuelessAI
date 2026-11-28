"""Binary search tree keyed by token_id."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar


T = TypeVar("T")


class BSTNode(Generic[T]):
    def __init__(self, token_id: str, item: T) -> None:
        self.token_id = token_id
        self.item = item
        self.left: BSTNode[T] | None = None
        self.right: BSTNode[T] | None = None


class TokenBST(Generic[T]):
    def __init__(self) -> None:
        self.root: BSTNode[T] | None = None
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def insert(self, token_id: str, item: T) -> None:
        if self.search(token_id) is not None:
            raise ValueError("duplicate token_id")
        node = BSTNode(token_id, item)
        if self.root is None:
            self.root = node
            self._size = 1
            return
        current = self.root
        while True:
            if token_id < current.token_id:
                if current.left is None:
                    current.left = node
                    break
                current = current.left
            else:
                if current.right is None:
                    current.right = node
                    break
                current = current.right
        self._size += 1

    def search(self, token_id: str) -> T | None:
        current = self.root
        while current is not None:
            if token_id == current.token_id:
                return current.item
            if token_id < current.token_id:
                current = current.left
            else:
                current = current.right
        return None

    def delete(self, token_id: str) -> T:
        node, parent = self._find_node(token_id)
        if node is None:
            raise KeyError(token_id)
        removed = node.item
        if node.left is not None and node.right is not None:
            successor_parent = node
            successor = node.right
            while successor.left is not None:
                successor_parent = successor
                successor = successor.left
            node.token_id = successor.token_id
            node.item = successor.item
            if successor_parent.left is successor:
                successor_parent.left = successor.right
            else:
                successor_parent.right = successor.right
        else:
            child = node.left if node.left is not None else node.right
            if parent is None:
                self.root = child
            elif parent.left is node:
                parent.left = child
            else:
                parent.right = child
        self._size -= 1
        return removed

    def inorder(self) -> Iterator[T]:
        yield from self._inorder(self.root)

    def preorder(self) -> Iterator[T]:
        yield from self._preorder(self.root)

    def postorder(self) -> Iterator[T]:
        yield from self._postorder(self.root)

    def height(self) -> int:
        return self._height(self.root)

    def _find_node(self, token_id: str) -> tuple[BSTNode[T] | None, BSTNode[T] | None]:
        current = self.root
        parent = None
        while current is not None:
            if token_id == current.token_id:
                return current, parent
            parent = current
            if token_id < current.token_id:
                current = current.left
            else:
                current = current.right
        return None, None

    def _inorder(self, node: BSTNode[T] | None) -> Iterator[T]:
        if node is not None:
            yield from self._inorder(node.left)
            yield node.item
            yield from self._inorder(node.right)

    def _preorder(self, node: BSTNode[T] | None) -> Iterator[T]:
        if node is not None:
            yield node.item
            yield from self._preorder(node.left)
            yield from self._preorder(node.right)

    def _postorder(self, node: BSTNode[T] | None) -> Iterator[T]:
        if node is not None:
            yield from self._postorder(node.left)
            yield from self._postorder(node.right)
            yield node.item

    def _height(self, node: BSTNode[T] | None) -> int:
        if node is None:
            return 0
        left_height = self._height(node.left)
        right_height = self._height(node.right)
        return 1 + max(left_height, right_height)
