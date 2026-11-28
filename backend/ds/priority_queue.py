"""Binary min-heap priority queue with 15-minute aging."""

from __future__ import annotations

import ctypes
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class ScheduledToken(Generic[T]):
    item: T
    token_id: str
    base_priority: int
    arrival_timestamp: datetime


class SchedulingPriorityQueue(Generic[T]):
    def __init__(self, aging_interval_minutes: int = 15) -> None:
        if aging_interval_minutes <= 0:
            raise ValueError("aging interval must be positive")
        self.aging_interval_minutes = aging_interval_minutes
        self._heap = self._allocate_storage(16)
        self._capacity = 16
        self._size = 0
        self._aging_time: datetime | None = None

    @property
    def size(self) -> int:
        return self._size

    def enqueue(
        self,
        item: T,
        token_id: str,
        base_priority: int,
        arrival_timestamp: datetime,
    ) -> None:
        """Add a scheduled token using the Ubaid queue API."""

        self.insert(
            ScheduledToken(
                item=item,
                token_id=token_id,
                base_priority=base_priority,
                arrival_timestamp=arrival_timestamp,
            )
        )

    def dequeue(self, current_time: datetime | None = None) -> ScheduledToken[T]:
        """Apply aging if requested, then remove the minimum."""

        return self.extract_min(current_time)

    def insert(self, item: ScheduledToken[T]) -> None:
        if self._find_index(item.token_id) is not None:
            raise ValueError("duplicate scheduled token")
        self._ensure_capacity(self._size + 1)
        self._heap[self._size] = item
        self._sift_up(self._size)
        self._size += 1

    def peek(self, now: datetime | None = None) -> ScheduledToken[T]:
        if now is not None:
            self.refresh_aging(now)
        if self._size == 0:
            raise LookupError("priority queue is empty")
        item = self._heap[0]
        if item is None:
            raise RuntimeError("priority queue invariant violated")
        return item

    def extract_min(self, now: datetime | None = None) -> ScheduledToken[T]:
        if now is not None:
            self.refresh_aging(now)
        if self._size == 0:
            raise LookupError("priority queue is empty")
        minimum = self._heap[0]
        if minimum is None:
            raise RuntimeError("priority queue invariant violated")
        if self._size == 1:
            self._heap[0] = None
            self._size = 0
            return minimum
        last = self._heap[self._size - 1]
        self._heap[0] = last
        self._heap[self._size - 1] = None
        self._size -= 1
        self._sift_down(0)
        return minimum

    def update_priority(self, token_id: str, new_base_priority: int) -> None:
        """Change a token's base priority and restore heap order."""

        index = self._find_index(token_id)
        if index is None:
            raise KeyError(token_id)
        item = self._heap[index]
        if item is None:
            raise RuntimeError("priority queue invariant violated")
        replacement = ScheduledToken(
            item=item.item,
            token_id=item.token_id,
            base_priority=new_base_priority,
            arrival_timestamp=item.arrival_timestamp,
        )
        self._heap[index] = replacement
        self._restore_heap(index)

    def apply_aging(
        self,
        current_time: datetime,
        threshold_min: int = 15,
    ) -> None:
        """Apply elapsed-threshold aging and restore heap ordering.

        ``threshold_min`` updates the aging interval for this operation.
        """

        if threshold_min <= 0:
            raise ValueError("threshold_min must be positive")
        self.aging_interval_minutes = threshold_min
        self.refresh_aging(current_time)

    def to_heap_snapshot(self, current_time: datetime | None = None) -> list[dict[str, object]]:
        """Return array-index heap contents for visualization."""

        now = current_time or datetime.now()
        self.refresh_aging(now)
        snapshot: list[dict[str, object]] = []
        index = 0
        while index < self._size:
            item = self._heap[index]
            if item is not None:
                snapshot.append(
                    {
                        "index": index,
                        "token_id": item.token_id,
                        "base_priority": item.base_priority,
                        "effective_priority": self.effective_priority(item, now),
                        "arrival_timestamp": item.arrival_timestamp.isoformat(),
                    }
                )
            index += 1
        return snapshot

    def effective_priority(self, item: ScheduledToken[T], now: datetime) -> int:
        elapsed_seconds = (now - item.arrival_timestamp).total_seconds()
        elapsed_minutes = max(0.0, elapsed_seconds / 60.0)
        boosts = int(elapsed_minutes // self.aging_interval_minutes)
        return item.base_priority - boosts

    def refresh_aging(self, now: datetime) -> None:
        self._aging_time = now
        for index in range(self._size // 2 - 1, -1, -1):
            self._sift_down(index, now)

    def contains(self, token_id: str) -> bool:
        return self._find_index(token_id) is not None

    def remove(self, token_id: str) -> ScheduledToken[T]:
        """Remove a token by identifier and restore heap order."""

        index = self._find_index(token_id)
        if index is None:
            raise KeyError(token_id)
        removed = self._heap[index]
        if removed is None:
            raise RuntimeError("priority queue invariant violated")
        last_index = self._size - 1
        if index == last_index:
            self._heap[index] = None
            self._size -= 1
            return removed
        last = self._heap[last_index]
        self._heap[index] = last
        self._heap[last_index] = None
        self._size -= 1
        self._restore_heap(index)
        return removed

    def heap_snapshot(self, now: datetime) -> list[tuple[str, int, datetime]]:
        snapshot: list[tuple[str, int, datetime]] = []
        index = 0
        while index < self._size:
            item = self._heap[index]
            if item is not None:
                snapshot.append(
                    (item.token_id, self.effective_priority(item, now), item.arrival_timestamp)
                )
            index += 1
        return snapshot

    def traverse_heap(self) -> Iterator[ScheduledToken[T]]:
        """Yield entries in their current heap-array order."""

        index = 0
        while index < self._size:
            item = self._heap[index]
            if item is None:
                raise RuntimeError("priority queue invariant violated")
            yield item
            index += 1

    def _key(
        self,
        item: ScheduledToken[T],
        now: datetime | None,
    ) -> tuple[int, datetime, str]:
        effective = item.base_priority
        comparison_time = now if now is not None else self._aging_time
        if comparison_time is not None:
            elapsed = max(
                0.0,
                (comparison_time - item.arrival_timestamp).total_seconds() / 60.0,
            )
            effective -= int(elapsed // self.aging_interval_minutes)
        return effective, item.arrival_timestamp, item.token_id

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            child_item = self._heap[index]
            parent_item = self._heap[parent]
            if child_item is None or parent_item is None:
                raise RuntimeError("priority queue invariant violated")
            if self._key(child_item, None) >= self._key(parent_item, None):
                break
            self._heap[index], self._heap[parent] = parent_item, child_item
            index = parent

    def _restore_heap(self, index: int) -> None:
        if index > 0:
            parent = (index - 1) // 2
            item = self._heap[index]
            parent_item = self._heap[parent]
            if item is None or parent_item is None:
                raise RuntimeError("priority queue invariant violated")
            if self._key(item, None) < self._key(parent_item, None):
                self._sift_up(index)
                return
        self._sift_down(index)

    def _sift_down(self, index: int, now: datetime | None = None) -> None:
        while True:
            left = 2 * index + 1
            right = 2 * index + 2
            smallest = index
            if left < self._size:
                left_item = self._heap[left]
                smallest_item = self._heap[smallest]
                if left_item is not None and smallest_item is not None:
                    if self._key(left_item, now) < self._key(smallest_item, now):
                        smallest = left
            if right < self._size:
                right_item = self._heap[right]
                smallest_item = self._heap[smallest]
                if right_item is not None and smallest_item is not None:
                    if self._key(right_item, now) < self._key(smallest_item, now):
                        smallest = right
            if smallest == index:
                break
            current_item = self._heap[index]
            smallest_item = self._heap[smallest]
            self._heap[index], self._heap[smallest] = smallest_item, current_item
            index = smallest

    def _ensure_capacity(self, required_size: int) -> None:
        if required_size <= self._capacity:
            return
        new_capacity = self._capacity * 2
        new_storage = self._allocate_storage(new_capacity)
        index = 0
        while index < self._size:
            new_storage[index] = self._heap[index]
            index += 1
        self._heap = new_storage
        self._capacity = new_capacity

    def _find_index(self, token_id: str) -> int | None:
        index = 0
        while index < self._size:
            item = self._heap[index]
            if item is not None and item.token_id == token_id:
                return index
            index += 1
        return None

    @staticmethod
    def _allocate_storage(capacity: int) -> ctypes.Array:
        storage_type = ctypes.py_object * capacity
        storage = storage_type()
        index = 0
        while index < capacity:
            storage[index] = None
            index += 1
        return storage
