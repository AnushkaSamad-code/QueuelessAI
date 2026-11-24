"""Manual array implementations used by QueueLess AI runtime indexes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import asdict, is_dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


class _ManualArray(Generic[T]):
    """A contiguous, manually shifted array with explicit capacity limits."""

    def __init__(self, capacity: int = 16, maximum_capacity: int | None = 999) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if maximum_capacity is not None and maximum_capacity < capacity:
            raise ValueError("maximum_capacity cannot be smaller than capacity")
        self._maximum_capacity = maximum_capacity
        self._storage: list[T | None] = [None] * capacity
        self._size = 0

    @property
    def size(self) -> int:
        """Return the number of occupied slots."""

        return self._size

    @property
    def capacity(self) -> int:
        """Return the allocated slot count."""

        return len(self._storage)

    def insert_at(self, index: int, item: T) -> None:
        """Insert ``item`` at ``index`` and shift the suffix right."""

        self._validate_item(item)
        if index < 0 or index > self._size:
            raise IndexError("insert index out of range")
        self._ensure_capacity(self._size + 1)
        position = self._size
        while position > index:
            self._storage[position] = self._storage[position - 1]
            position -= 1
        self._storage[index] = item
        self._size += 1

    def append(self, item: T) -> None:
        """Append ``item`` after the final occupied slot."""

        self.insert_at(self._size, item)

    def delete_at(self, index: int) -> T:
        """Delete a slot and shift every following item one position left."""

        self._validate_index(index)
        item = self._storage[index]
        if item is None:
            raise RuntimeError("array invariant violated: occupied slot is empty")
        position = index
        while position < self._size - 1:
            self._storage[position] = self._storage[position + 1]
            position += 1
        self._storage[self._size - 1] = None
        self._size -= 1
        return item

    def get(self, index: int) -> T:
        """Return the item at ``index``."""

        self._validate_index(index)
        item = self._storage[index]
        if item is None:
            raise RuntimeError("array invariant violated: occupied slot is empty")
        return item

    def update_at(self, index: int, item: T) -> None:
        """Replace the item at ``index`` without changing array size."""

        self._validate_item(item)
        self._validate_index(index)
        self._storage[index] = item

    def linear_search(self, predicate: Callable[[T], bool]) -> int | None:
        """Return the first matching index, or ``None`` when no item matches."""

        index = 0
        while index < self._size:
            if predicate(self.get(index)):
                return index
            index += 1
        return None

    def traverse(self) -> Iterator[T]:
        """Yield occupied items from left to right."""

        index = 0
        while index < self._size:
            yield self.get(index)
            index += 1

    def to_dict(self) -> dict[str, object]:
        """Return a telemetry snapshot without exposing unused storage slots."""

        elements = [self._serialize(item) for item in self.traverse()]
        return {
            "capacity": self.capacity,
            "size": self.size,
            "elements": elements,
        }

    def _ensure_capacity(self, required_size: int) -> None:
        if required_size <= self.capacity:
            return
        new_capacity = self.capacity * 2
        if new_capacity < required_size:
            new_capacity = required_size
        if (
            self._maximum_capacity is not None
            and new_capacity > self._maximum_capacity
        ):
            new_capacity = self._maximum_capacity
        if new_capacity < required_size:
            raise OverflowError("array maximum capacity exceeded")
        new_storage: list[T | None] = [None] * new_capacity
        index = 0
        while index < self._size:
            new_storage[index] = self._storage[index]
            index += 1
        self._storage = new_storage

    def _validate_index(self, index: int) -> None:
        if index < 0 or index >= self._size:
            raise IndexError("array index out of range")

    @staticmethod
    def _validate_item(item: T) -> None:
        if item is None:
            raise ValueError("None cannot be stored in a manual array")

    @staticmethod
    def _serialize(item: T) -> object:
        if is_dataclass(item):
            return asdict(item)
        if hasattr(item, "to_dict"):
            return item.to_dict()  # type: ignore[no-any-return]
        return item


class TokenArray(_ManualArray[T]):
    """Resizable contiguous store for active token records."""

    def binary_search_by_id(self, token_id: str) -> int | None:
        """Find ``token_id`` in records sorted by ``token_id``.

        The method intentionally performs binary search only on a sorted view;
        callers must preserve token-id ordering before invoking it.
        """

        low = 0
        high = self.size - 1
        while low <= high:
            middle = (low + high) // 2
            candidate = self.get(middle)
            candidate_id = getattr(candidate, "token_id", None)
            if candidate_id is None and isinstance(candidate, dict):
                candidate_id = candidate.get("token_id")
            if not isinstance(candidate_id, str):
                raise TypeError("records must expose a string token_id")
            if candidate_id == token_id:
                return middle
            if candidate_id < token_id:
                low = middle + 1
            else:
                high = middle - 1
        return None


class CounterArray(_ManualArray[T]):
    """Fixed-capacity contiguous store for the three service counters."""

    def __init__(self) -> None:
        super().__init__(capacity=3, maximum_capacity=3)

    def find_counter(self, counter_id: str) -> int | None:
        """Return the first counter index matching ``counter_id``."""

        return self.linear_search(
            lambda counter: getattr(counter, "counter_id", None) == counter_id
            or (
                isinstance(counter, dict)
                and counter.get("counter_id") == counter_id
            )
        )
