<<<<<<< Updated upstream
"""Counter-aware service graph model for QueueLess AI search algorithms."""
=======
"""Weighted directed graph model for the diagnostic service lifecycle."""
>>>>>>> Stashed changes

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping


class LifecycleState(str, Enum):
<<<<<<< Updated upstream
    """Formal token lifecycle states from appointment through completion."""
=======
    """Lifecycle labels exposed to the graph visualizer."""
>>>>>>> Stashed changes

    S1_BOOKED = "S1_BOOKED"
    S2_TOKEN_GENERATED = "S2_TOKEN_GENERATED"
    S3_WAITING = "S3_WAITING"
    S4_COUNTER_ASSIGNED = "S4_COUNTER_ASSIGNED"
    S5_IN_PROGRESS = "S5_IN_PROGRESS"
    S6_COMPLETED = "S6_COMPLETED"


COUNTER_IDS: tuple[str, str, str] = ("counter_1", "counter_2", "counter_3")
SERVICE_STAGES: tuple[str, str, str] = (
    "registration",
    "sample_collection",
    "report_collection",
)

DEFAULT_DURATIONS: dict[str, dict[str, float]] = {
    "counter_1": {
        "registration": 5.0,
        "sample_collection": 8.0,
        "report_collection": 2.0,
    },
    "counter_2": {
        "registration": 4.0,
        "sample_collection": 7.0,
        "report_collection": 2.0,
    },
    "counter_3": {
        "registration": 3.0,
        "sample_collection": 6.0,
        "report_collection": 1.0,
    },
}
DEFAULT_QUEUE_WAIT: dict[str, float] = {
    "counter_1": 15.0,
    "counter_2": 12.0,
    "counter_3": 10.0,
}


@dataclass(frozen=True)
class GraphEdge:
<<<<<<< Updated upstream
    """A directed, labelled, non-negative service transition."""
=======
    """A directed transition with an action label and non-negative cost."""
>>>>>>> Stashed changes

    target: str
    action: str
    cost: float


@dataclass(frozen=True)
class GraphNode:
<<<<<<< Updated upstream
    """A visualizable graph node with stable coordinates."""
=======
    """A visualizable service state and its coordinates."""
>>>>>>> Stashed changes

    node_id: str
    label: str
    x: float
    y: float
    lifecycle_state: LifecycleState
    counter_id: str | None = None
    stage: str | None = None


class ServiceStateGraph:
<<<<<<< Updated upstream
    """Build and expose a weighted graph for the three-counter workflow."""
=======
    """Build and expose a counter-aware service graph snapshot."""
>>>>>>> Stashed changes

    def __init__(
        self,
        queue_wait: Mapping[str, float] | None = None,
        service_duration: Mapping[str, Mapping[str, float]] | None = None,
        transition_overhead: float = 1.0,
        available_counters: Iterable[str] = COUNTER_IDS,
    ) -> None:
        """Create a graph using queue, duration, and counter availability data."""
        self.queue_wait = dict(
            DEFAULT_QUEUE_WAIT if queue_wait is None else queue_wait
        )
        source_durations = (
            DEFAULT_DURATIONS if service_duration is None else service_duration
        )
        self.service_duration = {
            counter: dict(durations)
            for counter, durations in source_durations.items()
        }
        self.transition_overhead = transition_overhead
        self.available_counters = self._validate_counters(available_counters)
        if transition_overhead < 0:
            raise ValueError("transition_overhead must be non-negative")
        self.nodes, self.adjacency = self._build_graph(
            self.queue_wait,
            self.service_duration,
            self.transition_overhead,
            self.available_counters,
        )

    def neighbors(self, node_id: str) -> tuple[GraphEdge, ...]:
<<<<<<< Updated upstream
        """Return outgoing edges for ``node_id``."""

=======
        """Return outgoing transitions for ``node_id`` in insertion order."""
>>>>>>> Stashed changes
        return self.adjacency.get(node_id, ())

    def rebuild(
        self,
        queue_wait: Mapping[str, float] | None = None,
        available_counters: Iterable[str] | None = None,
        service_duration: Mapping[str, Mapping[str, float]] | None = None,
        transition_overhead: float | None = None,
    ) -> None:
<<<<<<< Updated upstream
        """Rebuild weights after queue or counter availability changes."""

        if queue_wait is not None:
            self.queue_wait = dict(queue_wait)
        if available_counters is not None:
            self.available_counters = tuple(
                counter
                for counter in available_counters
                if counter in COUNTER_IDS
            )
        self.nodes.clear()
        self.adjacency.clear()
        self._build()

    def export_visualization(self) -> dict[str, list[dict[str, object]]]:
        """Export node and edge coordinates for a graph visualizer."""

=======
        """Atomically replace the graph using any supplied runtime updates."""
        next_queue_wait = dict(self.queue_wait if queue_wait is None else queue_wait)
        next_service_duration = {
            counter: dict(durations)
            for counter, durations in (
                self.service_duration
                if service_duration is None
                else service_duration
            ).items()
        }
        next_transition_overhead = (
            self.transition_overhead
            if transition_overhead is None
            else transition_overhead
        )
        next_available_counters = self._validate_counters(
            self.available_counters
            if available_counters is None
            else available_counters
        )
        if next_transition_overhead < 0:
            raise ValueError("transition_overhead must be non-negative")
        next_nodes, next_adjacency = self._build_graph(
            next_queue_wait,
            next_service_duration,
            next_transition_overhead,
            next_available_counters,
        )
        self.queue_wait = next_queue_wait
        self.service_duration = next_service_duration
        self.transition_overhead = next_transition_overhead
        self.available_counters = next_available_counters
        self.nodes = next_nodes
        self.adjacency = next_adjacency

    def export_visualization(self) -> dict[str, list[dict[str, object]]]:
        """Export node and edge labels, costs, and endpoint coordinates."""
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
    def _build(self) -> None:
        self._add_node(
=======
    @staticmethod
    def _validate_counters(counters: Iterable[str]) -> tuple[str, ...]:
        """Validate and retain the requested counter order."""
        available = tuple(counters)
        if len(set(available)) != len(available):
            raise ValueError("available_counters cannot contain duplicates")
        invalid = [counter for counter in available if counter not in COUNTER_IDS]
        if invalid:
            raise ValueError(f"unknown counter identifier: {invalid[0]}")
        return available

    @staticmethod
    def _build_graph(
        queue_wait: Mapping[str, float],
        service_duration: Mapping[str, Mapping[str, float]],
        transition_overhead: float,
        available_counters: tuple[str, ...],
    ) -> tuple[dict[str, GraphNode], dict[str, tuple[GraphEdge, ...]]]:
        """Construct a complete graph snapshot without mutating live state."""
        nodes: dict[str, GraphNode] = {}
        adjacency: dict[str, tuple[GraphEdge, ...]] = {}

        ServiceStateGraph._add_node(
            nodes,
            adjacency,
>>>>>>> Stashed changes
            GraphNode(
                "waiting_queue",
                "Waiting Queue",
                0.0,
<<<<<<< Updated upstream
                0.0,
                LifecycleState.S3_WAITING,
            )
=======
                1.0,
                LifecycleState.S3_WAITING,
            ),
>>>>>>> Stashed changes
        )
        ServiceStateGraph._add_node(
            nodes,
            adjacency,
            GraphNode(
                "service_completion",
                "Service Completion",
                8.0,
                1.0,
                LifecycleState.S6_COMPLETED,
            ),
        )
        for counter_index, counter in enumerate(available_counters):
            y = float(counter_index)
            for stage_index, stage in enumerate(SERVICE_STAGES):
                node_id = f"{counter}.{stage}"
                lifecycle_state = (
                    LifecycleState.S4_COUNTER_ASSIGNED
                    if stage_index == 0
                    else LifecycleState.S5_IN_PROGRESS
                )
                ServiceStateGraph._add_node(
                    nodes,
                    adjacency,
                    GraphNode(
                        node_id,
                        f"{counter.replace('_', ' ').title()}: "
                        f"{stage.replace('_', ' ').title()}",
                        float((stage_index + 1) * 2),
                        y,
                        lifecycle_state,
                        counter,
                        stage,
                    ),
                )

<<<<<<< Updated upstream
        for counter in self.available_counters:
            first_node = self._node_id(counter, SERVICE_STAGES[0])
            self._add_edge(
=======
        for counter in available_counters:
            first_stage = SERVICE_STAGES[0]
            ServiceStateGraph._add_edge(
                adjacency,
>>>>>>> Stashed changes
                "waiting_queue",
                GraphEdge(
                    f"{counter}.{first_stage}",
                    f"assign_{counter}",
<<<<<<< Updated upstream
                    self._assignment_cost(counter),
                ),
            )
            for index, stage in enumerate(SERVICE_STAGES):
                current = self._node_id(counter, stage)
                if index + 1 < len(SERVICE_STAGES):
                    next_stage = self._node_id(counter, SERVICE_STAGES[index + 1])
                    self._add_edge(
=======
                    queue_wait.get(counter, 0.0)
                    + service_duration[counter][first_stage]
                    + transition_overhead,
                ),
            )
            for stage_index, stage in enumerate(SERVICE_STAGES):
                current = f"{counter}.{stage}"
                if stage_index + 1 < len(SERVICE_STAGES):
                    next_stage = SERVICE_STAGES[stage_index + 1]
                    ServiceStateGraph._add_edge(
                        adjacency,
>>>>>>> Stashed changes
                        current,
                        GraphEdge(
                            f"{counter}.{next_stage}",
                            f"complete_{stage}",
<<<<<<< Updated upstream
                            self._stage_cost(counter, SERVICE_STAGES[index + 1]),
=======
                            service_duration[counter][next_stage]
                            + transition_overhead,
>>>>>>> Stashed changes
                        ),
                    )
                else:
                    ServiceStateGraph._add_edge(
                        adjacency,
                        current,
                        GraphEdge(
                            "service_completion",
                            "complete_service",
                            transition_overhead,
                        ),
                    )
<<<<<<< Updated upstream
                for other_counter in self.available_counters:
                    if other_counter != counter:
                        self._add_edge(
                            current,
                            GraphEdge(
                                self._node_id(other_counter, stage),
                                f"transfer_to_{other_counter}",
                                self.transition_overhead,
                            ),
                        )

    def _assignment_cost(self, counter: str) -> float:
        return (
            self.queue_wait.get(counter, 0.0)
            + self.service_duration[counter][SERVICE_STAGES[0]]
            + self.transition_overhead
        )

    def _stage_cost(self, counter: str, stage: str) -> float:
        return self.service_duration[counter][stage] + self.transition_overhead
=======
                for other_counter in available_counters:
                    if other_counter != counter:
                        ServiceStateGraph._add_edge(
                            adjacency,
                            current,
                            GraphEdge(
                                f"{other_counter}.{stage}",
                                f"transfer_to_{other_counter}",
                                transition_overhead,
                            ),
                        )
        return nodes, adjacency
>>>>>>> Stashed changes

    @staticmethod
    def _add_node(
        nodes: dict[str, GraphNode],
        adjacency: dict[str, tuple[GraphEdge, ...]],
        node: GraphNode,
    ) -> None:
        """Register a graph node and initialize its outgoing edge collection."""
        nodes[node.node_id] = node
        adjacency[node.node_id] = ()

    @staticmethod
    def _add_edge(
        adjacency: dict[str, tuple[GraphEdge, ...]],
        source: str,
        edge: GraphEdge,
    ) -> None:
        """Add a validated directed edge to its source node."""
        if edge.cost < 0:
            raise ValueError("graph edge cost must be non-negative")
        adjacency[source] = adjacency[source] + (edge,)

    @staticmethod
    def _node_id(counter: str, stage: str) -> str:
        return f"{counter}.{stage}"


_DEFAULT_GRAPH = ServiceStateGraph()
service_graph: dict[str, tuple[GraphEdge, ...]] = _DEFAULT_GRAPH.adjacency
