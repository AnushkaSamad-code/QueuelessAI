"""Binary min-heap priority queue with 15-minute aging."""

from __future__ import annotations

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
        self._heap: list[ScheduledToken[T] | None] = [None] * 16
        self._capacity = 16
        self._size = 0
        self._positions: dict[str, int] = {}

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
        if item.token_id in self._positions:
            raise ValueError("duplicate scheduled token")
        self._ensure_capacity(self._size + 1)
        self._heap[self._size] = item
        self._positions[item.token_id] = self._size
        self._sift_up(self._size)
        self._size += 1

    def peek(self, now: datetime | None = None) -> ScheduledToken[T]:
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
        del self._positions[minimum.token_id]
        if self._size == 1:
            self._heap[0] = None
            self._size = 0
            return minimum
        last = self._heap[self._size - 1]
        self._heap[0] = last
        self._heap[self._size - 1] = None
        self._size -= 1
        if last is not None:
            self._positions[last.token_id] = 0
        self._sift_down(0)
        return minimum

    def update_priority(self, token_id: str, new_base_priority: int) -> None:
        """Change a token's base priority and restore heap order."""

        index = self._positions.get(token_id)
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
        self._sift_up(index)
        self._sift_down(index)

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
        if self._size < 2:
            return
        for index in range(self._size // 2 - 1, -1, -1):
            self._sift_down(index, now)
        self._rebuild_positions()

    def contains(self, token_id: str) -> bool:
        return token_id in self._positions

    def remove(self, token_id: str) -> ScheduledToken[T]:
        """Remove a token by identifier and restore heap order."""

        index = self._positions.get(token_id)
        if index is None:
            raise KeyError(token_id)
        removed = self._heap[index]
        if removed is None:
            raise RuntimeError("priority queue invariant violated")
        del self._positions[token_id]
        last_index = self._size - 1
        if index == last_index:
            self._heap[index] = None
            self._size -= 1
            self._rebuild_positions()
            return removed
        last = self._heap[last_index]
        self._heap[index] = last
        self._heap[last_index] = None
        self._size -= 1
        if last is not None:
            self._positions[last.token_id] = index
        self._sift_down(index)
        self._sift_up(index)
        self._rebuild_positions()
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

    def _key(self, item: ScheduledToken[T], now: datetime | None) -> tuple[int, datetime]:
        effective = item.base_priority
        if now is not None:
            elapsed = max(0.0, (now - item.arrival_timestamp).total_seconds() / 60.0)
            effective -= int(elapsed // self.aging_interval_minutes)
        return effective, item.arrival_timestamp

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
            self._positions[child_item.token_id] = parent
            self._positions[parent_item.token_id] = index
            index = parent

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
            if current_item is not None:
                self._positions[current_item.token_id] = smallest
            if smallest_item is not None:
                self._positions[smallest_item.token_id] = index
            index = smallest

    def _ensure_capacity(self, required_size: int) -> None:
        if required_size <= self._capacity:
            return
        new_capacity = self._capacity * 2
        new_storage: list[ScheduledToken[T] | None] = [None] * new_capacity
        index = 0
        while index < self._size:
            new_storage[index] = self._heap[index]
            index += 1
        self._heap = new_storage
        self._capacity = new_capacity

    def _rebuild_positions(self) -> None:
        self._positions.clear()
        index = 0
        while index < self._size:
            item = self._heap[index]
            if item is not None:
                self._positions[item.token_id] = index
            index += 1
