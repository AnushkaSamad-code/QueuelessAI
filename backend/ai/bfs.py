"""Breadth-first search with deterministic visualizer trace output."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import TypedDict

from .graph_model import GraphEdge, ServiceStateGraph


class BFSTraceStep(TypedDict):
    """One observable BFS expansion step."""

    step: int
    current_node: str
    frontier: list[str]
    visited: list[str]
    action: str


class BFSResult(TypedDict):
    """Structured result consumed by the Graph Visualizer."""

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
    """Return a shallowest path and a step-by-step BFS execution trace.

    BFS optimizes edge count, not weighted cost. ``total_cost`` is the sum of
    edge costs along the returned path so the visualizer can compare BFS with
    UCS and A*. If no goal is reachable, the path is empty and cost is ``None``.
    """

    frontier: deque[str] = deque((start_state,))
    discovered: set[str] = {start_state}
    parent: dict[str, str | None] = {start_state: None}
    parent_edge: dict[str, GraphEdge] = {}
    visited: list[str] = []
    trace_steps: list[BFSTraceStep] = []
    nodes_expanded = 0

    while frontier:
        current = frontier.popleft()
        visited.append(current)
        nodes_expanded += 1
        if current == goal_state:
            trace_steps.append(
                _trace(
                    len(trace_steps),
                    current,
                    frontier,
                    visited,
                    "goal_test",
                )
            )
            path = _reconstruct_path(parent, goal_state)
            return {
                "algorithm": "BFS",
                "optimal_path": path,
                "total_cost": _path_cost(path, parent_edge),
                "nodes_expanded": nodes_expanded,
                "trace_steps": trace_steps,
            }

        for edge in _neighbors(graph, current):
            if edge.target in discovered:
                continue
            discovered.add(edge.target)
            parent[edge.target] = current
            parent_edge[edge.target] = edge
            frontier.append(edge.target)
        trace_steps.append(
            _trace(
                len(trace_steps),
                current,
                frontier,
                visited,
                "expand_neighbors",
            )
        )

    return {
        "algorithm": "BFS",
        "optimal_path": [],
        "total_cost": None,
        "nodes_expanded": nodes_expanded,
        "trace_steps": trace_steps,
    }


def _neighbors(graph: GraphInput, node: str) -> Sequence[GraphEdge]:
    if isinstance(graph, ServiceStateGraph):
        return graph.neighbors(node)
    return graph.get(node, ())


def _trace(
    step: int,
    current: str,
    frontier: deque[str],
    visited: list[str],
    action: str,
) -> BFSTraceStep:
    return {
        "step": step,
        "current_node": current,
        "frontier": list(frontier),
        "visited": list(visited),
        "action": action,
    }


def _reconstruct_path(
    parent: Mapping[str, str | None],
    goal_state: str,
) -> list[str]:
    path: list[str] = []
    current: str | None = goal_state
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def _path_cost(path: list[str], parent_edge: Mapping[str, GraphEdge]) -> float:
    total = 0.0
    for node in path[1:]:
        total += parent_edge[node].cost
    return total
