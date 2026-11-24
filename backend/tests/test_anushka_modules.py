"""Focused tests for Anushka Samad's array, graph, and BFS modules."""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.bfs import breadth_first_search
from backend.ai.graph_model import ServiceStateGraph
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


def test_graph_builds_weighted_counter_branches() -> None:
    graph = ServiceStateGraph()
    assignment_edges = graph.neighbors("waiting_queue")

    assert len(assignment_edges) == 3
    assert assignment_edges[0].cost == 21.0
    assert len(graph.export_visualization()["nodes"]) == 11


def test_bfs_returns_path_cost_and_trace() -> None:
    graph = ServiceStateGraph()
    result = breadth_first_search(graph, "waiting_queue", "service_completion")

    assert result["algorithm"] == "BFS"
    assert result["optimal_path"][0] == "waiting_queue"
    assert result["optimal_path"][-1] == "service_completion"
    assert result["total_cost"] == 34.0
    assert result["nodes_expanded"] == 11
    assert result["trace_steps"][-1]["action"] == "goal_test"
