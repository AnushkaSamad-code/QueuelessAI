"""Comprehensive UT-01 through UT-12 unit tests for QueueLess AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.ai.astar import a_star_search
from backend.ai.bfs import breadth_first_search
from backend.ai.graph_model import GraphEdge
from backend.ai.ucs import uniform_cost_search
from backend.ds.custom_array import TokenArray
from backend.ds.linked_list import ServiceLinkedList
from backend.ds.priority_queue import ScheduledToken, SchedulingPriorityQueue
from backend.ds.token_bst import TokenBST


@dataclass(frozen=True)
class ArrayToken:
    token_id: str
    customer_name: str = ""


def test_ut_01_token_array_resizes_at_capacity_and_preserves_order() -> None:
    """UT-01: append to capacity, then resize and preserve index order."""

    tokens = TokenArray[ArrayToken](capacity=2, maximum_capacity=8)
    tokens.append(ArrayToken("Q101", "Ayesha"))
    tokens.append(ArrayToken("Q102", "Hamza"))

    assert tokens.size == 2
    assert tokens.capacity == 2
    tokens.append(ArrayToken("Q103", "Sana"))

    assert tokens.capacity == 4
    assert [item.token_id for item in tokens.traverse()] == ["Q101", "Q102", "Q103"]
    assert tokens.get(0).customer_name == "Ayesha"

    try:
        bounded = TokenArray[ArrayToken](capacity=2, maximum_capacity=2)
        bounded.append(ArrayToken("Q101"))
        bounded.append(ArrayToken("Q102"))
        bounded.append(ArrayToken("Q103"))
    except OverflowError:
        pass
    else:
        raise AssertionError("append accepted a record beyond maximum_capacity")


def test_ut_02_token_array_deletes_middle_with_left_shift() -> None:
    """UT-02: middle deletion shifts every following record left once."""

    tokens = TokenArray[ArrayToken](capacity=5)
    tokens.append(ArrayToken("Q101"))
    tokens.append(ArrayToken("Q102"))
    tokens.append(ArrayToken("Q103"))
    tokens.append(ArrayToken("Q104"))

    removed = tokens.delete_at(1)

    assert removed.token_id == "Q102"
    assert tokens.size == 3
    assert [item.token_id for item in tokens.traverse()] == ["Q101", "Q103", "Q104"]
    assert tokens.to_dict()["elements"][1]["token_id"] == "Q103"
    try:
        tokens.get(tokens.size)
    except IndexError:
        pass
    else:
        raise AssertionError("get accepted the first empty post-size index")


def test_ut_03_service_linked_list_head_operations() -> None:
    """UT-03: head insertion/removal updates head, tail, and size."""

    queue = ServiceLinkedList[str]()
    queue.prepend("Q102")
    queue.prepend("Q101")

    assert queue.size == 2
    assert queue.peek_front() == "Q101"
    assert queue.pop_front() == "Q101"
    assert queue.head is not None
    assert queue.head.item == "Q102"
    assert queue.tail is not None
    assert queue.tail.item == "Q102"
    assert queue.size == 1
    assert queue.pop_front() == "Q102"
    assert queue.head is None
    assert queue.tail is None
    assert queue.size == 0


def test_ut_04_service_linked_list_middle_operations() -> None:
    """UT-04: middle insertion and deletion reconnect all successor links."""

    queue = ServiceLinkedList[str]()
    queue.append("Q101")
    queue.append("Q103")
    queue.insert_at(1, "Q102")

    assert list(queue.traverse()) == ["Q101", "Q102", "Q103"]
    assert queue.delete_at(1) == "Q102"
    assert list(queue.traverse()) == ["Q101", "Q103"]
    assert queue.head is not None
    assert queue.head.next is not None
    assert queue.head.next.item == "Q103"


def test_ut_05_service_linked_list_tail_and_empty_operations() -> None:
    """UT-05: tail insertion/deletion and the final node maintain invariants."""

    queue = ServiceLinkedList[str]()
    queue.append("Q101")
    queue.append("Q102")
    queue.insert_at(2, "Q103")

    assert queue.tail is not None
    assert queue.tail.item == "Q103"
    assert queue.delete_at(2) == "Q103"
    assert queue.tail is not None
    assert queue.tail.item == "Q102"
    assert queue.delete_at(1) == "Q102"
    assert queue.delete_at(0) == "Q101"
    assert queue.head is None
    assert queue.tail is None
    assert queue.size == 0
    try:
        queue.pop_front()
    except LookupError:
        pass
    else:
        raise AssertionError("pop_front accepted an empty linked list")


def test_ut_06_priority_queue_heap_order_and_ties() -> None:
    """UT-06: lower priority keys and then older arrival timestamps win."""

    now = datetime(2026, 1, 1, 9, 0)
    queue = SchedulingPriorityQueue[ArrayToken]()
    queue.insert(ScheduledToken(ArrayToken("Q103"), "Q103", 1, now - timedelta(minutes=5)))
    queue.insert(ScheduledToken(ArrayToken("Q101"), "Q101", 0, now - timedelta(minutes=3)))
    queue.insert(ScheduledToken(ArrayToken("Q102"), "Q102", 0, now - timedelta(minutes=2)))

    assert queue.extract_min(now).token_id == "Q101"
    assert queue.extract_min(now).token_id == "Q102"
    assert queue.extract_min(now).token_id == "Q103"

    same_arrival_queue = SchedulingPriorityQueue[ArrayToken]()
    same_arrival_queue.insert(ScheduledToken(ArrayToken("Q102"), "Q102", 2, now))
    same_arrival_queue.insert(ScheduledToken(ArrayToken("Q101"), "Q101", 2, now))
    assert same_arrival_queue.extract_min(now).token_id == "Q101"
    assert same_arrival_queue.extract_min(now).token_id == "Q102"

    duplicate_queue = SchedulingPriorityQueue[ArrayToken]()
    duplicate_queue.insert(ScheduledToken(ArrayToken("Q101"), "Q101", 0, now))
    try:
        duplicate_queue.insert(ScheduledToken(ArrayToken("Q101"), "Q101", 1, now))
    except ValueError:
        pass
    else:
        raise AssertionError("priority queue accepted duplicate token_id")


def test_ut_07_priority_queue_aging_boost() -> None:
    """UT-07: 15 minutes of aging improves an older token before a newer token."""

    start = datetime(2026, 1, 1, 9, 0)
    now = start + timedelta(minutes=30)
    queue = SchedulingPriorityQueue[ArrayToken](aging_interval_minutes=15)
    queue.insert(
        ScheduledToken(ArrayToken("Q101"), "Q101", 1, start)
    )
    queue.insert(
        ScheduledToken(ArrayToken("Q102"), "Q102", 0, start + timedelta(minutes=25))
    )

    assert queue.effective_priority(queue._heap[0].item and ScheduledToken(ArrayToken("Q101"), "Q101", 1, start), now) == -1
    queue.refresh_aging(now)
    first = queue.extract_min(now)

    assert first.token_id == "Q101"


def test_ut_08_token_bst_leaf_one_child_and_two_child_deletion() -> None:
    """UT-08: deletion cases for leaf, one-child, and two-child nodes."""

    bst = TokenBST[ArrayToken]()
    bst.insert("Q104", ArrayToken("Q104"))
    bst.insert("Q102", ArrayToken("Q102"))
    bst.insert("Q106", ArrayToken("Q106"))
    bst.insert("Q101", ArrayToken("Q101"))
    bst.insert("Q103", ArrayToken("Q103"))
    bst.insert("Q105", ArrayToken("Q105"))
    bst.insert("Q107", ArrayToken("Q107"))

    assert bst.delete("Q101").token_id == "Q101"
    assert bst.search("Q101") is None

    assert bst.delete("Q103").token_id == "Q103"
    assert bst.search("Q103") is None

    assert bst.delete("Q104").token_id == "Q104"
    assert bst.search("Q104") is None

    assert [item.token_id for item in bst.inorder()] == [
        "Q102",
        "Q105",
        "Q106",
        "Q107",
    ]

    try:
        bst.insert("Q102", ArrayToken("Q102"))
    except ValueError:
        pass
    else:
        raise AssertionError("BST accepted duplicate token_id")


def test_ut_09_token_bst_traversal_orders() -> None:
    """UT-09: inorder, preorder, and postorder traversal visit in exact order."""

    bst = TokenBST[str]()
    bst.insert("Q104", "Q104")
    bst.insert("Q102", "Q102")
    bst.insert("Q106", "Q106")
    bst.insert("Q101", "Q101")
    bst.insert("Q103", "Q103")
    bst.insert("Q105", "Q105")
    bst.insert("Q107", "Q107")

    assert list(bst.inorder()) == ["Q101", "Q102", "Q103", "Q104", "Q105", "Q106", "Q107"]
    assert list(bst.preorder()) == ["Q104", "Q102", "Q101", "Q103", "Q106", "Q105", "Q107"]
    assert list(bst.postorder()) == ["Q101", "Q103", "Q102", "Q105", "Q107", "Q106", "Q104"]


def test_ut_10_bfs_shallowest_path_and_unreachable_goal() -> None:
    """UT-10: BFS minimizes edge count and explicitly reports unreachable goals."""

    graph: dict[str, tuple[GraphEdge, ...]] = {
        "start": (
            GraphEdge("b", "to_b", 1.0),
            GraphEdge("c", "to_c", 1.0),
        ),
        "b": (GraphEdge("goal", "to_goal", 1.0),),
        "c": (GraphEdge("goal", "to_goal", 1.0),),
        "goal": (),
        "unreachable": (),
    }

    result = breadth_first_search(graph, "start", "goal")
    assert result["optimal_path"] == ["start", "b", "goal"]
    assert result["total_cost"] == 2.0

    missing = breadth_first_search(graph, "start", "unreachable")
    assert missing["optimal_path"] == []
    assert missing["total_cost"] is None
    missing_ucs = uniform_cost_search(graph, "start", "unreachable")
    assert missing_ucs["optimal_path"] == []
    assert missing_ucs["total_cost"] is None
    missing_astar = a_star_search(
        graph,
        "start",
        "unreachable",
        lambda _node: 0.0,
    )
    assert missing_astar["optimal_path"] == []
    assert missing_astar["total_cost"] is None


def test_ut_11_ucs_returns_weighted_optimal_route() -> None:
    """UT-11: UCS chooses a more expensive shallow route over a cheaper long route."""

    graph: dict[str, tuple[GraphEdge, ...]] = {
        "start": (
            GraphEdge("fast", "fast_route", 9.0),
            GraphEdge("slow", "slow_route", 2.0),
        ),
        "fast": (GraphEdge("goal", "finish", 1.0),),
        "slow": (GraphEdge("middle", "continue", 2.0),),
        "middle": (GraphEdge("goal", "finish", 2.0),),
        "goal": (),
    }

    result = uniform_cost_search(graph, "start", "goal")
    assert result["optimal_path"] == ["start", "slow", "middle", "goal"]
    assert result["total_cost"] == 6.0


def test_ut_12_astar_matches_ucs_and_heuristic_is_admissible_consistent() -> None:
    """UT-12: A* cost equals UCS, h(n) <= h*(n), and consistency holds."""

    graph: dict[str, tuple[GraphEdge, ...]] = {
        "waiting_queue": (
            GraphEdge("counter_1.registration", "assign_1", 16.0),
            GraphEdge("counter_2.registration", "assign_2", 13.0),
            GraphEdge("counter_3.registration", "assign_3", 11.0),
        ),
        "counter_1.registration": (
            GraphEdge("counter_1.sample_collection", "sample", 9.0),
        ),
        "counter_1.sample_collection": (
            GraphEdge("service_completion", "finish", 3.0),
        ),
        "counter_2.registration": (
            GraphEdge("counter_2.sample_collection", "sample", 8.0),
        ),
        "counter_2.sample_collection": (
            GraphEdge("service_completion", "finish", 3.0),
        ),
        "counter_3.registration": (
            GraphEdge("counter_3.sample_collection", "sample", 7.0),
        ),
        "counter_3.sample_collection": (
            GraphEdge("service_completion", "finish", 2.0),
        ),
        "service_completion": (),
    }

    ucs = uniform_cost_search(graph, "waiting_queue", "service_completion")

    true_remaining = {
        "waiting_queue": 11.0,
        "counter_1.registration": 12.0,
        "counter_1.sample_collection": 3.0,
        "counter_2.registration": 11.0,
        "counter_2.sample_collection": 3.0,
        "counter_3.registration": 9.0,
        "counter_3.sample_collection": 2.0,
        "service_completion": 0.0,
    }
    minimum_remaining_stage_estimate = {
        "waiting_queue": 7.0,
        "counter_1.registration": 9.0,
        "counter_1.sample_collection": 2.0,
        "counter_2.registration": 8.0,
        "counter_2.sample_collection": 2.0,
        "counter_3.registration": 7.0,
        "counter_3.sample_collection": 1.0,
        "service_completion": 0.0,
    }

    astar = a_star_search(
        graph,
        "waiting_queue",
        "service_completion",
        lambda node: minimum_remaining_stage_estimate[node],
    )

    assert astar["total_cost"] == ucs["total_cost"] == 20.0
    assert astar["optimal_path"] == ["waiting_queue", "counter_3.registration", "counter_3.sample_collection", "service_completion"]

    for node, heuristic in minimum_remaining_stage_estimate.items():
        assert heuristic <= true_remaining[node]
        for edge in graph[node]:
            assert heuristic <= edge.cost + minimum_remaining_stage_estimate[edge.target]
