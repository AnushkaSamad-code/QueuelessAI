"""Breadth-first search implementation."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import TypedDict

try:
    from .graph_model import GraphEdge, ServiceStateGraph
except ImportError:
    from ai.graph_model import GraphEdge, ServiceStateGraph


class BFSTraceStep(TypedDict):
    step: int
    current_node: str
    frontier: list[str]
    visited: list[str]
    action: str


class BFSResult(TypedDict):
    algorithm: str
    optimal_path: list[str]
    total_cost: float | None
    nodes_expanded: int
    trace_steps: list[BFSTraceStep]


GraphInput = ServiceStateGraph | Mapping[str, Sequence[GraphEdge]]


def breadth_first_search(
    graph: GraphInput,
    start_state: str,
    goal_state: str,
) -> BFSResult:
    frontier: deque[str] = deque((start_state,))
    discovered: set[str] = {start_state}
    parent: dict[str, str | None] = {start_state: None}
    parent_edge: dict[str, GraphEdge] = {}
    visited: list[str] = []
    trace: list[BFSTraceStep] = []
    nodes_expanded = 0

    while frontier:
        current = frontier.popleft()
        visited.append(current)
        nodes_expanded += 1
        if current == goal_state:
            trace.append(
                {
                    "step": len(trace),
                    "current_node": current,
                    "frontier": list(frontier),
                    "visited": list(visited),
                    "action": "goal_test",
                }
            )
            path = _reconstruct(parent, goal_state)
            cost = sum(parent_edge[node].cost for node in path[1:])
            return {
                "algorithm": "BFS",
                "optimal_path": path,
                "total_cost": cost,
                "nodes_expanded": nodes_expanded,
                "trace_steps": trace,
            }
        for edge in _neighbors(graph, current):
            if edge.target in discovered:
                continue
            discovered.add(edge.target)
            parent[edge.target] = current
            parent_edge[edge.target] = edge
            frontier.append(edge.target)
        trace.append(
            {
                "step": len(trace),
                "current_node": current,
                "frontier": list(frontier),
                "visited": list(visited),
                "action": "expand_neighbors",
            }
        )
    return {
        "algorithm": "BFS",
        "optimal_path": [],
        "total_cost": None,
        "nodes_expanded": nodes_expanded,
        "trace_steps": trace,
    }


def _neighbors(graph: GraphInput, node: str) -> Sequence[GraphEdge]:
    if isinstance(graph, ServiceStateGraph):
        return graph.neighbors(node)
    return graph.get(node, ())


def _reconstruct(parent: Mapping[str, str | None], goal: str) -> list[str]:
    path: list[str] = []
    current: str | None = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path
