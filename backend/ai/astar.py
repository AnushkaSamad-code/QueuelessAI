"""A* search implementation."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

try:
    from .graph_model import GraphEdge, ServiceStateGraph
except ImportError:
    from ai.graph_model import GraphEdge, ServiceStateGraph


def a_star_search(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    start_state: str,
    goal_state: str,
    heuristic: Callable[[str], float] | None = None,
) -> dict[str, object]:
    """Run A* using an admissible minimum-remaining-stage heuristic."""

    if heuristic is None:
        heuristic = _minimum_remaining_stage_duration
    heuristic_values: dict[str, float] = {}
    trace_steps: list[dict[str, object]] = []
    heuristic_values[start_state] = heuristic(start_state)
    heap: list[tuple[float, float, int, str]] = [
        (heuristic_values[start_state], 0.0, 0, start_state)
    ]
    insertion_order = 1
    best_cost: dict[str, float] = {start_state: 0.0}
    parent: dict[str, str | None] = {start_state: None}
    nodes_expanded = 0

    while heap:
        _, cost, _, node = heap.pop(0)
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
                    "frontier": [
                        item[3] for item in heap
                    ],
                    "visited": list(best_cost),
                    "action": "goal_test",
                }
            )
            return {
                "algorithm": "A*",
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
                edge_heuristic = heuristic(edge.target)
                heuristic_values[edge.target] = edge_heuristic
                heap.append(
                    (
                        new_cost + edge_heuristic,
                        new_cost,
                        insertion_order,
                        edge.target,
                    )
                )
                insertion_order += 1
                heap.sort()
        trace_steps.append(
            {
                "step": len(trace_steps),
                "current_node": node,
                "frontier": [item[3] for item in heap],
                "visited": list(best_cost),
                "action": "expand_neighbors",
            }
        )
    return {
        "algorithm": "A*",
        "optimal_path": [],
        "total_cost": None,
        "nodes_expanded": nodes_expanded,
        "heuristic_values": heuristic_values,
        "trace_steps": trace_steps,
    }


def _minimum_remaining_stage_duration(node: str) -> float:
    """Estimate cost as the fastest remaining laboratory stages.

    The default values correspond to Counter 3, whose specified durations are
    minimum for Registration, Sample Collection, and Report Collection.
    """

    if node == "service_completion":
        return 0.0
    if node == "waiting_queue":
        return 3.0 + 6.0 + 1.0
    if node.endswith(".registration"):
        return 6.0 + 1.0
    if node.endswith(".sample_collection"):
        return 1.0
    if node.endswith(".report_collection"):
        return 0.0
    return 0.0


def _neighbors(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    node: str,
) -> Sequence[GraphEdge]:
    if isinstance(graph, ServiceStateGraph):
        return graph.neighbors(node)
    return graph.get(node, ())
