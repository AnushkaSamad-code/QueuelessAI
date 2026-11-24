"""A* search implementation."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

try:
    from .graph_model import (
        DEFAULT_DURATIONS,
        SERVICE_STAGES,
        GraphEdge,
        ServiceStateGraph,
    )
except ImportError:
    from ai.graph_model import (
        DEFAULT_DURATIONS,
        SERVICE_STAGES,
        GraphEdge,
        ServiceStateGraph,
    )


def astar_search(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    start_state: str,
    goal_state: str,
    heuristic: Callable[[str], float] | None = None,
) -> dict[str, object]:
    """Run A* using an admissible minimum-remaining-stage heuristic."""

    if heuristic is None:
        def minimum_remaining_stage_duration(node: str) -> float:
            return _minimum_remaining_stage_duration(graph, node)

        heuristic = minimum_remaining_stage_duration
    heuristic_values: dict[str, float] = {}
    trace_steps: list[dict[str, object]] = []
    heuristic_values[start_state] = heuristic(start_state)
    frontier: list[tuple[float, float, int, str]] = [
        (heuristic_values[start_state], 0.0, 0, start_state)
    ]
    insertion_order = 1
    best_cost: dict[str, float] = {start_state: 0.0}
    parent: dict[str, str | None] = {start_state: None}
    nodes_expanded = 0

    while frontier:
        _, cost, _, node = _pop_min(frontier)
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
                    "frontier": [item[3] for item in frontier],
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
                _push(
                    frontier,
                    (
                        new_cost + edge_heuristic,
                        new_cost,
                        insertion_order,
                        edge.target,
                    ),
                )
                insertion_order += 1
        trace_steps.append(
            {
                "step": len(trace_steps),
                "current_node": node,
                "frontier": [item[3] for item in frontier],
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


def _minimum_remaining_stage_duration(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    node_id: str,
) -> float:
    """Sum per-stage minimum service durations for stages not yet completed."""

    if node_id == "service_completion":
        return 0.0
    if node_id == "waiting_queue":
        remaining_stages = SERVICE_STAGES
    else:
        if isinstance(graph, ServiceStateGraph):
            graph_node = graph.nodes.get(node_id)
            if graph_node is None or graph_node.stage not in SERVICE_STAGES:
                return 0.0
            remaining_stages = SERVICE_STAGES[
                SERVICE_STAGES.index(graph_node.stage) + 1 :
            ]
        else:
            _, separator, stage = node_id.partition(".")
            if not separator or stage not in SERVICE_STAGES:
                return 0.0
            remaining_stages = SERVICE_STAGES[SERVICE_STAGES.index(stage) + 1 :]

    durations = (
        graph.service_duration
        if isinstance(graph, ServiceStateGraph)
        else DEFAULT_DURATIONS
    )
    counter_ids = (
        graph.available_counters
        if isinstance(graph, ServiceStateGraph)
        else tuple(durations)
    )
    estimate = 0.0
    for stage in remaining_stages:
        stage_durations = [
            durations[counter][stage]
            for counter in counter_ids
            if counter in durations and stage in durations[counter]
        ]
        if not stage_durations:
            return 0.0
        estimate += min(stage_durations)
    return estimate


def _neighbors(
    graph: ServiceStateGraph | Mapping[str, Sequence[GraphEdge]],
    node: str,
) -> Sequence[GraphEdge]:
    if isinstance(graph, ServiceStateGraph):
        return graph.neighbors(node)
    return graph.get(node, ())


def _push(
    heap: list[tuple[float, float, int, str]],
    item: tuple[float, float, int, str],
) -> None:
    heap.append(item)
    index = len(heap) - 1
    while index > 0:
        parent = (index - 1) // 2
        if heap[parent] <= heap[index]:
            break
        heap[parent], heap[index] = heap[index], heap[parent]
        index = parent


def _pop_min(heap: list[tuple[float, float, int, str]]) -> tuple[float, float, int, str]:
    minimum = heap[0]
    last = heap.pop()
    if heap:
        heap[0] = last
        index = 0
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < len(heap) and heap[left] < heap[smallest]:
                smallest = left
            if right < len(heap) and heap[right] < heap[smallest]:
                smallest = right
            if smallest == index:
                break
            heap[index], heap[smallest] = heap[smallest], heap[index]
            index = smallest
    return minimum


a_star_search = astar_search
