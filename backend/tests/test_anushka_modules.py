"""Focused tests for Anushka Samad's array, graph, and BFS modules."""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.bfs import breadth_first_search
from backend.ai.counter_assignment import assign_best_counter
from backend.ai.graph_model import SERVICE_ROUTE_STAGES, ServiceStateGraph
from backend.ds.custom_array import CounterArray, TokenArray


@dataclass(frozen=True)
class Token:
    token_id: str


def test_token_array_shifts_and_resizes() -> None:
    tokens = TokenArray[Token](capacity=2, maximum_capacity=4)
    tokens.append(Token("Q101"))
    tokens.append(Token("Q103"))
    tokens.insert_at(1, Token("Q102"))

    assert [token.token_id for token in tokens.traverse()] == ["Q101", "Q102", "Q103"]
    assert tokens.delete_at(1).token_id == "Q102"
    assert [token.token_id for token in tokens.traverse()] == ["Q101", "Q103"]
    assert tokens.binary_search_by_id("Q103") == 1


def test_counter_array_is_fixed_at_three_slots() -> None:
    counters = CounterArray[dict[str, str]]()
    counters.append({"counter_id": "counter_1"})
    counters.append({"counter_id": "counter_2"})
    counters.append({"counter_id": "counter_3"})

    assert counters.find_counter("counter_2") == 1
    try:
        counters.append({"counter_id": "counter_4"})
    except OverflowError:
        pass
    else:
        raise AssertionError("CounterArray accepted a fourth counter")


def test_service_graph_contains_only_the_diagnostic_stage_route() -> None:
    graph = ServiceStateGraph()
    first_stage_edges = graph.neighbors(SERVICE_ROUTE_STAGES[0])

    assert len(first_stage_edges) == 1
    assert first_stage_edges[0].target == SERVICE_ROUTE_STAGES[1]
    assert first_stage_edges[0].cost == 5.0
    assert len(graph.export_visualization()["nodes"]) == 4


def test_bfs_returns_full_diagnostic_service_route() -> None:
    graph = ServiceStateGraph()
    result = breadth_first_search(graph, SERVICE_ROUTE_STAGES[0], SERVICE_ROUTE_STAGES[-1])

    assert result["algorithm"] == "BFS"
    assert result["optimal_path"] == list(SERVICE_ROUTE_STAGES)
    assert result["total_cost"] == 16.0
    assert result["nodes_expanded"] == 4
    assert result["trace_steps"][-1]["action"] == "goal_test"


def test_counter_assignment_is_compatible_and_deterministic() -> None:
    counters = [
        {"counter_id": "2", "status": "OPEN", "supported_services": ["SVC-1"]},
        {"counter_id": "1", "status": "OPEN", "supported_services": ["SVC-1"]},
        {"counter_id": "3", "status": "CLOSED", "supported_services": ["SVC-1"]},
    ]

    selected = assign_best_counter(
        "SVC-1",
        counters,
        {"1": 4.0, "2": 4.0, "3": 0.0},
        10.0,
    )

    assert selected["counter_id"] == "1"
    assert selected["estimated_wait_min"] == 4.0
    try:
        assign_best_counter("SVC-2", counters, {}, 10.0)
    except ValueError:
        pass
    else:
        raise AssertionError("counter assignment ignored service compatibility")
