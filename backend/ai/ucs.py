"""Uniform-cost search implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from .graph_model import GraphEdge, ServiceStateGraph
except ImportError:
    from ai.graph_model import GraphEdge, ServiceStateGraph


def uniform_cost_search(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    start_state: str,
    goal_state: str,
) -> dict[str, object]:
    """Run Uniform-Cost Search and emit trace and expansion telemetry."""

    heap: list[tuple[float, int, str]] = [(0.0, 0, start_state)]
    insertion_order = 1
    best_cost: dict[str, float] = {start_state: 0.0}
    parent: dict[str, str | None] = {start_state: None}
    nodes_expanded = 0
    trace_steps: list[dict[str, object]] = []
    heuristic_values: dict[str, float] = {start_state: 0.0}

    while heap:
        cost, _, node = heap.pop(0)
        if cost != best_cost.get(node):
            continue
        nodes_expanded += 1
        if node == goal_state:
            path: list[str] = []
            current: str | None = node
            while current is not None:
                path.append(current)
                current = parent[current]
            path.reverse()
            trace_steps.append(
                {
                    "step": len(trace_steps),
                    "current_node": node,
                    "frontier": [item[2] for item in heap],
                    "visited": list(best_cost),
                    "action": "goal_test",
                }
            )
            return {
                "algorithm": "UCS",
                "optimal_path": path,
                "total_cost": cost,
                "nodes_expanded": nodes_expanded,
                "heuristic_values": heuristic_values,
                "trace_steps": trace_steps,
            }
        for edge in _neighbors(graph, node):
            if edge.cost < 0:
                raise ValueError("negative edge cost")
            new_cost = cost + edge.cost
            if new_cost < best_cost.get(edge.target, float("inf")):
                best_cost[edge.target] = new_cost
                parent[edge.target] = node
                heuristic_values[edge.target] = 0.0
                heap.append((new_cost, insertion_order, edge.target))
                insertion_order += 1
                heap.sort()
        trace_steps.append(
            {
                "step": len(trace_steps),
                "current_node": node,
                "frontier": [item[2] for item in heap],
                "visited": list(best_cost),
                "action": "expand_neighbors",
            }
        )
    return {
        "algorithm": "UCS",
        "optimal_path": [],
        "total_cost": None,
        "nodes_expanded": nodes_expanded,
        "heuristic_values": heuristic_values,
        "trace_steps": trace_steps,
    }


def _neighbors(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    node: str,
) -> Sequence[GraphEdge]:
    if isinstance(graph, ServiceStateGraph):
        return graph.neighbors(node)
    return graph.get(node, ())
