# QueueLess AI — Data Structures Design and Implementation

## 1. Implementation Policy

QueueLess AI implements its four core abstract data types in `backend/ds/`. Python `list`, `dict`, `set`, `heapq`, and equivalent container shortcuts are forbidden for core storage, insertion, deletion, search, ordering, and traversal operations. Built-in containers may be used at API boundaries for serialization, configuration, or test fixtures only.

The structures operate on records and references owned by the application service. SQLite remains the durable source of truth; these structures are reconstructed as runtime indexes and queues during startup hydration.

## 2. `TokenArray`

`TokenArray` is a bounded or resizable contiguous record store for active tokens and the three counters. It uses a manually managed array with a logical size and capacity.

### ADT Interface

```text
TokenArray(capacity: int = 16, maximum_capacity: int = 999)
append(record: TokenRecord) -> int
get(index: int) -> TokenRecord
set(index: int, record: TokenRecord) -> None
remove(index: int) -> TokenRecord
find_token(token_id: str) -> int | None
find_counter(counter_id: str) -> int | None
resize(new_capacity: int) -> None
size() -> int
capacity() -> int
```

### Invariants

1. `0 <= size <= capacity <= maximum_capacity`.
2. Occupied records are stored in indices `[0, size)`.
3. Every active token identifier is unique.
4. Counter identifiers are exactly `counter_1`, `counter_2`, and `counter_3`.
5. After removal, records above the removed index shift left exactly once; no occupied slot is skipped.
6. A resize copies records in index order and does not change logical size.
7. An append beyond `maximum_capacity` fails explicitly rather than silently dropping a record.

### Operations and Complexity

Append is amortized \(O(1)\) when capacity remains and \(O(n)\) when resizing. Indexed access and update are \(O(1)\). Token and counter lookup are \(O(n)\). Removal is \(O(n)\) because the contiguous suffix shifts. Space is \(O(n)\).

## 3. `ServiceLinkedList`

`ServiceLinkedList` is a singly linked structure used for counter-wise waiting queues and the completed-service history log. Each node owns one service record and a reference to the next node.

### ADT Interface

```text
ServiceLinkedList()
append(record: ServiceRecord) -> None
prepend(record: ServiceRecord) -> None
insert_after(token_id: str, record: ServiceRecord) -> None
remove(token_id: str) -> ServiceRecord
pop_front() -> ServiceRecord
peek_front() -> ServiceRecord
find(token_id: str) -> ServiceRecord | None
iterate() -> Iterator[ServiceRecord]
size() -> int
clear() -> None
```

Each counter has one waiting-list instance. A separate instance stores completed history in completion order.

### Pointer Invariants

1. `head` is `None` exactly when `size == 0`.
2. `tail` is `None` exactly when `size == 0`; otherwise `tail.next is None`.
3. Following `next` from `head` reaches `tail` after exactly `size - 1` links.
4. No node points to itself.
5. A node belongs to at most one list.
6. Removal updates both `head` and `tail` and decrements size exactly once.
7. `pop_front` is \(O(1)\); arbitrary search/removal is \(O(n)\).

### Complexity

| Operation | Time | Extra space |
|---|---:|---:|
| Append with tail pointer | \(O(1)\) | \(O(1)\) |
| Prepend | \(O(1)\) | \(O(1)\) |
| Pop front | \(O(1)\) | \(O(1)\) |
| Find/remove by token | \(O(n)\) | \(O(1)\) |
| Iterate | \(O(n)\) | \(O(1)\) |
| Complete list | - | \(O(n)\) |

## 4. `SchedulingPriorityQueue`

`SchedulingPriorityQueue` is a manually implemented binary min-heap. The minimum key is:

$$
K(t)=\bigl(\text{effective\_priority}(t),\text{arrival\_timestamp}(t)\bigr).
$$

Lower values are dequeued first. The second component provides deterministic FIFO ordering among equal effective priorities.

### Fifteen-Minute Anti-Starvation Aging

For a token waiting \(w\) minutes, with configured base priority \(p_0\):

$$
\text{effective\_priority}(t)
=p_0-\left\lfloor\frac{w}{15}\right\rfloor.
$$

Every completed 15-minute interval improves the token's priority by one. Recomputing keys before dequeue and after a timer tick prevents a continuously arriving stream of new tokens from permanently bypassing an older token.

### ADT Interface

```text
SchedulingPriorityQueue(aging_interval_minutes: int = 15)
insert(item: ScheduledToken) -> None
peek() -> ScheduledToken
extract_min(now: datetime) -> ScheduledToken
decrease_priority(token_id: str, new_base_priority: int) -> None
remove(token_id: str) -> ScheduledToken
refresh_aging(now: datetime) -> None
contains(token_id: str) -> bool
size() -> int
```

### Heap Invariants

1. The heap is stored in a manually managed contiguous array.
2. For zero-based index \(i\), children are \(2i+1\) and \(2i+2\); parent is \(\lfloor(i-1)/2\rfloor\).
3. Every parent key is less than or equal to each child key.
4. `token_id` occurs at most once.
5. `refresh_aging` updates keys without losing any item.
6. Tie comparison always evaluates effective priority first, then arrival timestamp.

### Complexity

| Operation | Time | Extra space |
|---|---:|---:|
| Insert | \(O(\log n)\) | \(O(1)\) amortized |
| Peek | \(O(1)\) | \(O(1)\) |
| Extract minimum | \(O(\log n)\) | \(O(1)\) |
| Remove by maintained index | \(O(\log n)\) | \(O(1)\) |
| Refresh all aging keys | \(O(n\log n)\) | \(O(1)\) |
| Heap storage | - | \(O(n)\) |

## 5. `TokenBST`

`TokenBST` is a binary search tree keyed lexicographically by `token_id`. `Q101 < Q102 < ... < Q999` under the fixed token format.

### ADT Interface

```text
TokenBST()
insert(token: TokenRecord) -> None
search(token_id: str) -> TokenRecord | None
delete(token_id: str) -> TokenRecord
inorder() -> Iterator[TokenRecord]
preorder() -> Iterator[TokenRecord]
postorder() -> Iterator[TokenRecord]
height() -> int
size() -> int
```

### Pointer Invariants

1. Every node has zero, one, or two child references.
2. Every key in the left subtree is less than the node key.
3. Every key in the right subtree is greater than the node key.
4. Duplicate token identifiers are rejected.
5. Deletion of a two-child node replaces it with its inorder successor and preserves ordering.
6. Traversals visit each stored node exactly once.

Average insert, search, and delete are \(O(\log n)\); worst-case time is \(O(n)\) for a skewed tree. Each traversal is \(O(n)\), recursive stack space is \(O(h)\), and storage is \(O(n)\).

## 6. Complexity Summary

| Structure | Primary use | Access/search | Insert | Delete/dequeue | Space |
|---|---|---:|---:|---:|---:|
| `TokenArray` | Active token and counter records | \(O(1)/O(n)\) | \(O(1)\) amortized | \(O(n)\) | \(O(n)\) |
| `ServiceLinkedList` | Counter queues and completed history | \(O(n)\) | \(O(1)\) at tail | \(O(1)\) front, \(O(n)\) by token | \(O(n)\) |
| `SchedulingPriorityQueue` | Fair next-token scheduling | \(O(1)\) peek | \(O(\log n)\) | \(O(\log n)\) | \(O(n)\) |
| `TokenBST` | Token identifier lookup and ordered reports | \(O(\log n)\) average | \(O(\log n)\) average | \(O(\log n)\) average | \(O(n)\) |

## 7. Q101 Integration Walkthrough

1. **Booking:** FastAPI validates the appointment and appends the `Q101` record to `TokenArray`. The array stores its active status and counter fields.
2. **Indexing:** The same record is inserted into `TokenBST`, making exact token lookup independent of queue position.
3. **Scheduling:** The record is inserted into `SchedulingPriorityQueue` with its base priority and arrival timestamp. The heap computes its effective priority using the 15-minute aging interval.
4. **Assignment:** The AI `SearchEngine` obtains the current counter-aware graph, compares feasible counter branches, and selects the least-cost route. The record is removed from the scheduling heap and appended to the selected counter's `ServiceLinkedList`.
5. **Service:** Staff dequeue the list head, update the `TokenArray` record to `S5(c_i)`, and append stage events to SQLite.
6. **Completion:** After the final stage, the token is removed from the counter waiting list, marked `S6` in `TokenArray`, remains searchable in `TokenBST`, and is appended to the completed-service history list.
7. **Recovery:** On restart, SQLite records rebuild all four structures in token, arrival, counter, and completion order.

The structures have separate responsibilities: the array is the mutable record store, linked lists preserve service order, the heap chooses the next fair token, and the BST provides ordered identifier lookup.
