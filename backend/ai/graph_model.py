"""Weighted directed service graph model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping


class LifecycleState(str, Enum):
    S1_BOOKED = "S1_BOOKED"
    S2_TOKEN_GENERATED = "S2_TOKEN_GENERATED"
    S3_WAITING = "S3_WAITING"
    S4_COUNTER_ASSIGNED = "S4_COUNTER_ASSIGNED"
    S5_IN_PROGRESS = "S5_IN_PROGRESS"
    S6_COMPLETED = "S6_COMPLETED"


COUNTER_IDS = ("counter_1", "counter_2", "counter_3")
SERVICE_STAGES = ("registration", "sample_collection", "report_collection")

DEFAULT_DURATIONS: dict[str, dict[str, float]] = {
    "counter_1": {"registration": 5.0, "sample_collection": 8.0, "report_collection": 2.0},
    "counter_2": {"registration": 4.0, "sample_collection": 7.0, "report_collection": 2.0},
    "counter_3": {"registration": 3.0, "sample_collection": 6.0, "report_collection": 1.0},
}
DEFAULT_QUEUE_WAIT: dict[str, float] = {
    "counter_1": 15.0,
    "counter_2": 12.0,
    "counter_3": 10.0,
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


class ServiceStateGraph:
    def __init__(
        self,
        queue_wait: Mapping[str, float] | None = None,
        service_duration: Mapping[str, Mapping[str, float]] | None = None,
        transition_overhead: float = 1.0,
        available_counters: Iterable[str] = COUNTER_IDS,
    ) -> None:
        if transition_overhead < 0:
            raise ValueError("transition_overhead must be non-negative")
        self.queue_wait = dict(queue_wait or DEFAULT_QUEUE_WAIT)
        source_durations = service_duration or DEFAULT_DURATIONS
        self.service_duration = {
            counter: dict(durations)
            for counter, durations in source_durations.items()
        }
        self.transition_overhead = transition_overhead
        self.available_counters = tuple(
            counter for counter in available_counters if counter in COUNTER_IDS
        )
        self.nodes: dict[str, GraphNode] = {}
        self.adjacency: dict[str, tuple[GraphEdge, ...]] = {}
        self._build()

    def neighbors(self, node_id: str) -> tuple[GraphEdge, ...]:
        return self.adjacency.get(node_id, ())

    def rebuild(
        self,
        queue_wait: Mapping[str, float] | None = None,
        available_counters: Iterable[str] | None = None,
    ) -> None:
        if queue_wait is not None:
            self.queue_wait = dict(queue_wait)
        if available_counters is not None:
            self.available_counters = tuple(
                counter for counter in available_counters if counter in COUNTER_IDS
            )
        self.nodes.clear()
        self.adjacency.clear()
        self._build()

    def export_visualization(self) -> dict[str, list[dict[str, object]]]:
        nodes = [
            {
                "id": node.node_id,
                "label": node.label,
                "x": node.x,
                "y": node.y,
                "lifecycle_state": node.lifecycle_state.value,
                "counter_id": node.counter_id,
                "stage": node.stage,
            }
            for node in self.nodes.values()
        ]
        edges: list[dict[str, object]] = []
        for source, outgoing in self.adjacency.items():
            source_node = self.nodes[source]
            for edge in outgoing:
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

    def _build(self) -> None:
        self._add_node(
            GraphNode("waiting_queue", "Waiting Queue", 0.0, 0.0, LifecycleState.S3_WAITING)
        )
        self._add_node(
            GraphNode(
                "service_completion",
                "Service Completion",
                8.0,
                0.0,
                LifecycleState.S6_COMPLETED,
            )
        )
        for index, counter in enumerate(self.available_counters):
            x = float(index * 3 + 1)
            for stage_index, stage in enumerate(SERVICE_STAGES):
                node_id = f"{counter}.{stage}"
                self._add_node(
                    GraphNode(
                        node_id,
                        f"{counter.replace('_', ' ').title()}: {stage.replace('_', ' ').title()}",
                        x + stage_index * 0.25,
                        float(index + 1),
                        LifecycleState.S5_IN_PROGRESS,
                        counter,
                        stage,
                    )
                )

        for counter in self.available_counters:
            first_node = f"{counter}.{SERVICE_STAGES[0]}"
            self._add_edge(
                "waiting_queue",
                GraphEdge(
                    first_node,
                    f"assign_{counter}",
                    self.queue_wait.get(counter, 0.0)
                    + self.service_duration[counter][SERVICE_STAGES[0]]
                    + self.transition_overhead,
                ),
            )
            for index, stage in enumerate(SERVICE_STAGES):
                current = f"{counter}.{stage}"
                if index + 1 < len(SERVICE_STAGES):
                    next_stage = f"{counter}.{SERVICE_STAGES[index + 1]}"
                    self._add_edge(
                        current,
                        GraphEdge(
                            next_stage,
                            f"complete_{stage}",
                            self.service_duration[counter][SERVICE_STAGES[index + 1]]
                            + self.transition_overhead,
                        ),
                    )
                else:
                    self._add_edge(
                        current,
                        GraphEdge(
                            "service_completion",
                            "complete_service",
                            self.transition_overhead,
                        ),
                    )

    def _add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node
        self.adjacency.setdefault(node.node_id, ())

    def _add_edge(self, source: str, edge: GraphEdge) -> None:
        if edge.cost < 0:
            raise ValueError("graph edge cost must be non-negative")
        self.adjacency[source] = self.adjacency[source] + (edge,)


service_graph: dict[str, tuple[GraphEdge, ...]] = ServiceStateGraph().adjacency
