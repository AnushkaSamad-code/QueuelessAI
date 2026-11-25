"""Diagnostic service-route graph used by Problem A search."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class LifecycleState(str, Enum):
    S1_BOOKED = "S1_BOOKED"
    S2_TOKEN_GENERATED = "S2_TOKEN_GENERATED"
    S3_WAITING = "S3_WAITING"
    S4_COUNTER_ASSIGNED = "S4_COUNTER_ASSIGNED"
    S5_IN_PROGRESS = "S5_IN_PROGRESS"
    S6_COMPLETED = "S6_COMPLETED"


SERVICE_ROUTE_STAGES = (
    "Registration",
    "Sample Collection",
    "Report Collection",
    "Service Completed",
)
SERVICE_STAGE_KEYS = (
    "registration",
    "sample_collection",
    "report_collection",
)
DEFAULT_STAGE_DURATIONS: dict[str, float] = {
    "registration": 5.0,
    "sample_collection": 8.0,
    "report_collection": 3.0,
}


@dataclass(frozen=True)
class GraphEdge:
    target: str
    action: str
    cost: float


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    label: str
    x: float
    y: float
    lifecycle_state: LifecycleState
    counter_id: str | None = None
    stage: str | None = None


def build_service_route_graph(
    durations: Mapping[str, float] | None = None,
) -> dict[str, tuple[GraphEdge, ...]]:
    """Build the same weighted, linear route for BFS, UCS, and A*."""

    stage_durations = dict(DEFAULT_STAGE_DURATIONS)
    if durations is not None:
        stage_durations.update(
            {stage: float(durations[stage]) for stage in SERVICE_STAGE_KEYS if stage in durations}
        )
    graph: dict[str, tuple[GraphEdge, ...]] = {}
    for index, stage in enumerate(SERVICE_ROUTE_STAGES):
        if index + 1 == len(SERVICE_ROUTE_STAGES):
            graph[stage] = ()
            continue
        next_stage = SERVICE_ROUTE_STAGES[index + 1]
        graph[stage] = (
            GraphEdge(
                target=next_stage,
                action=f"complete_{SERVICE_STAGE_KEYS[index]}",
                cost=stage_durations[SERVICE_STAGE_KEYS[index]],
            ),
        )
    return graph


def minimum_remaining_stage_duration(
    node: str,
    durations: Mapping[str, float] | None = None,
) -> float:
    """Sum minimum durations for each remaining stage; zero at the goal."""

    stage_durations = dict(DEFAULT_STAGE_DURATIONS)
    if durations is not None:
        stage_durations.update(
            {stage: float(durations[stage]) for stage in SERVICE_STAGE_KEYS if stage in durations}
        )
    if node == SERVICE_ROUTE_STAGES[-1]:
        return 0.0
    try:
        stage_index = SERVICE_ROUTE_STAGES.index(node)
    except ValueError:
        return 0.0
    return sum(
        stage_durations[stage]
        for stage in SERVICE_STAGE_KEYS[stage_index:]
    )


class ServiceStateGraph:
    """Compatibility wrapper around the service-stage-only adjacency graph."""

    def __init__(
        self,
        queue_wait: Mapping[str, float] | None = None,
        service_duration: Mapping[str, Mapping[str, float]] | None = None,
        transition_overhead: float = 0.0,
        available_counters: object = None,
    ) -> None:
        del queue_wait, available_counters
        if transition_overhead < 0:
            raise ValueError("transition_overhead must be non-negative")
        durations = DEFAULT_STAGE_DURATIONS
        if service_duration:
            durations = next(iter(service_duration.values()))
        self.service_duration = {"service": dict(durations)}
        self.available_counters: tuple[str, ...] = ()
        self.adjacency = build_service_route_graph(durations)
        self.nodes = {
            stage: GraphNode(
                node_id=stage,
                label=stage,
                x=float(index * 210 + 110),
                y=100.0,
                lifecycle_state=(
                    LifecycleState.S6_COMPLETED
                    if stage == SERVICE_ROUTE_STAGES[-1]
                    else LifecycleState.S5_IN_PROGRESS
                ),
                stage=SERVICE_STAGE_KEYS[index] if index < len(SERVICE_STAGE_KEYS) else None,
            )
            for index, stage in enumerate(SERVICE_ROUTE_STAGES)
        }

    def neighbors(self, node_id: str) -> tuple[GraphEdge, ...]:
        return self.adjacency.get(node_id, ())

    def rebuild(
        self,
        queue_wait: Mapping[str, float] | None = None,
        available_counters: object = None,
    ) -> None:
        del queue_wait, available_counters
        durations = self.service_duration["service"]
        self.adjacency = build_service_route_graph(durations)

    def export_visualization(self) -> dict[str, list[dict[str, object]]]:
        nodes = [
            {
                "id": node.node_id,
                "label": node.label,
                "x": node.x,
                "y": node.y,
                "lifecycle_state": node.lifecycle_state.value,
                "counter_id": None,
                "stage": node.stage,
            }
            for node in self.nodes.values()
        ]
        edges: list[dict[str, object]] = []
        for source, outgoing in self.adjacency.items():
            for edge in outgoing:
                source_node = self.nodes[source]
                target_node = self.nodes[edge.target]
                edges.append(
                    {
                        "source": source,
                        "target": edge.target,
                        "action": edge.action,
                        "cost": edge.cost,
                        "source_x": source_node.x,
                        "source_y": source_node.y,
                        "target_x": target_node.x,
                        "target_y": target_node.y,
                    }
                )
        return {"nodes": nodes, "edges": edges}


SERVICE_ROUTE_GRAPH = build_service_route_graph()
service_graph = SERVICE_ROUTE_GRAPH
