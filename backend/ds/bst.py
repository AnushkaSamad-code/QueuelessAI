"""Public BST module for QueueLess AI token identifiers."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar


T = TypeVar("T")


class BSTNode(Generic[T]):
    """A binary search tree node keyed by token identifier."""

    def __init__(
        self,
        token_id: str,
        payload: T,
        left: "BSTNode[T] | None" = None,
        right: "BSTNode[T] | None" = None,
    ) -> None:
        self.token_id = token_id
        self.payload = payload
        self.left = left
        self.right = right


class TokenBST(Generic[T]):
    """Binary search tree storing one payload per token identifier."""

    def __init__(self) -> None:
        self.root: BSTNode[T] | None = None
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def insert(self, token_id: str, payload: T) -> None:
        if self._find_node(token_id)[0] is not None:
            raise ValueError("duplicate token_id")
        new_node = BSTNode(token_id, payload)
        if self.root is None:
            self.root = new_node
            self._size = 1
            return
        current = self.root
        while True:
            if token_id < current.token_id:
                if current.left is None:
                    current.left = new_node
                    break
                current = current.left
            else:
                if current.right is None:
                    current.right = new_node
                    break
                current = current.right
        self._size += 1

    def search(self, token_id: str) -> T | None:
        current = self.root
        while current is not None:
            if token_id == current.token_id:
                return current.payload
            if token_id < current.token_id:
                current = current.left
            else:
                current = current.right
        return None

    def delete(self, token_id: str) -> T:
        """Delete a node, using its inorder successor for two-child nodes."""

        node, parent = self._find_node(token_id)
        if node is None:
            raise KeyError(token_id)
        removed_payload = node.payload

        if node.left is not None and node.right is not None:
            successor_parent = node
            successor = node.right
            while successor.left is not None:
                successor_parent = successor
                successor = successor.left
            node.token_id = successor.token_id
            node.payload = successor.payload
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
        return removed_payload

    def inorder(self) -> Iterator[T]:
        yield from self._inorder(self.root)

    def preorder(self) -> Iterator[T]:
        yield from self._preorder(self.root)

    def postorder(self) -> Iterator[T]:
        yield from self._postorder(self.root)

    def height(self) -> int:
        return self._height(self.root)

    def _find_node(
        self,
        token_id: str,
    ) -> tuple[BSTNode[T] | None, BSTNode[T] | None]:
        current = self.root
        parent: BSTNode[T] | None = None
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
            yield node.payload
            yield from self._inorder(node.right)

    def _preorder(self, node: BSTNode[T] | None) -> Iterator[T]:
        if node is not None:
            yield node.payload
            yield from self._preorder(node.left)
            yield from self._preorder(node.right)

    def _postorder(self, node: BSTNode[T] | None) -> Iterator[T]:
        if node is not None:
            yield from self._postorder(node.left)
            yield from self._postorder(node.right)
            yield node.payload

    def _height(self, node: BSTNode[T] | None) -> int:
        if node is None:
            return 0
        return 1 + max(self._height(node.left), self._height(node.right))
