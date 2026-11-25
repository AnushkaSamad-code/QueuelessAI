"""Deterministic counter assignment for Problem B, separate from route search."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def assign_best_counter(
    service_id: str,
    counters: Sequence[Mapping[str, object]],
    workload_minutes: Mapping[str, float],
    service_duration_min: float,
) -> dict[str, object]:
    """Choose the compatible open counter with the lowest projected finish time."""

    candidates: list[tuple[float, float, str, Mapping[str, object]]] = []
    for counter in counters:
        counter_id = str(counter["counter_id"])
        supported_services = counter.get("supported_services", ())
        if (
            counter.get("status") != "OPEN"
            or not isinstance(supported_services, (list, tuple, set))
            or service_id not in supported_services
        ):
            continue
        workload = max(0.0, float(workload_minutes.get(counter_id, 0.0)))
        candidates.append(
            (workload + service_duration_min, workload, counter_id, counter)
        )
    if not candidates:
        raise ValueError(f"No open counter supports service {service_id}")
    projected_finish, workload, counter_id, _ = min(
        candidates,
        key=lambda item: (item[0], item[1], item[2]),
    )
    return {
        "counter_id": counter_id,
        "estimated_wait_min": workload,
        "total_cost": projected_finish,
    }
