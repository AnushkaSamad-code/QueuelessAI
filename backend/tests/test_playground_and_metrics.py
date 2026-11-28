from __future__ import annotations

import ctypes
import importlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from backend.ai.graph_model import (
    DEFAULT_STAGE_DURATIONS,
    SERVICE_ROUTE_STAGES,
    minimum_remaining_stage_duration,
)
from backend.ds.playground import DataStructurePlayground, DuplicateStructureItem


def test_waiting_time_summary_uses_only_valid_started_visits() -> None:
    from backend.api.main import _waiting_time_summary

    summary = _waiting_time_summary(
        [
            {
                "status": "S6_COMPLETED",
                "arrival_timestamp": "2025-01-01T10:00:00+00:00",
                "service_started_at": "2025-01-01T10:10:00+00:00",
            },
            {
                "status": "S5_IN_PROGRESS",
                "arrival_timestamp": "2025-01-01T10:00:00",
                "service_started_at": "2025-01-01T10:20:00",
            },
            {
                "status": "S3_WAITING",
                "arrival_timestamp": "2025-01-01T10:00:00+00:00",
                "service_started_at": None,
            },
            {
                "status": "S6_COMPLETED",
                "arrival_timestamp": None,
                "service_started_at": "2025-01-01T10:20:00+00:00",
            },
            {
                "status": "S6_COMPLETED",
                "arrival_timestamp": "not-a-date",
                "service_started_at": "2025-01-01T10:20:00+00:00",
            },
            {
                "status": "S6_COMPLETED",
                "arrival_timestamp": "2025-01-01T10:20:00+00:00",
                "service_started_at": "2025-01-01T10:10:00+00:00",
            },
        ]
    )

    assert summary == {
        "average_wait_min": 15.0,
        "waiting_time_sample_count": 2,
        "waiting_time_excluded": {
            "status": 1,
            "missing_timestamp": 1,
            "invalid_timestamp": 1,
            "negative_duration": 1,
        },
    }


def test_waiting_time_summary_returns_no_data_when_all_samples_are_invalid() -> None:
    from backend.api.main import _waiting_time_summary

    summary = _waiting_time_summary(
        [
            {
                "status": "S6_COMPLETED",
                "arrival_timestamp": "2025-01-01T10:20:00+00:00",
                "service_started_at": "2025-01-01T10:10:00+00:00",
            }
        ]
    )

    assert summary["average_wait_min"] is None
    assert summary["waiting_time_sample_count"] == 0
    assert summary["waiting_time_excluded"]["negative_duration"] == 1


def test_heuristic_targets_selected_stage_and_is_zero_at_goal() -> None:
    durations = {
        "registration": 7.0,
        "sample_collection": 9.0,
        "report_collection": 4.0,
    }

    assert minimum_remaining_stage_duration(
        "Registration",
        durations,
        "Sample Collection",
    ) == 7.0
    assert minimum_remaining_stage_duration(
        "Sample Collection",
        durations,
        "Sample Collection",
    ) == 0.0
    assert minimum_remaining_stage_duration(
        "Report Collection",
        durations,
        "Sample Collection",
    ) == 0.0
    assert minimum_remaining_stage_duration(
        "Registration",
        DEFAULT_STAGE_DURATIONS,
        SERVICE_ROUTE_STAGES[-1],
    ) == sum(DEFAULT_STAGE_DURATIONS.values())


def test_data_structure_playground_executes_manual_operations() -> None:
    playground = DataStructurePlayground()
    assert isinstance(playground.array._storage, ctypes.Array)
    assert isinstance(playground.priority_queue._heap, ctypes.Array)
    assert not hasattr(playground.priority_queue, "_positions")

    playground.array_operation("insert", "first")
    playground.array_operation("insert", "second")
    playground.array_operation("update", "updated", 1)
    assert playground.array_operation("search", "updated")["message"] == (
        "Found updated at index 1."
    )
    assert playground.array_operation("delete", index=0)["snapshot"]["array"]["elements"] == [
        {"token_id": "A002", "value": "updated"}
    ]

    playground.linked_list_operation("insert_beginning", "head")
    playground.linked_list_operation("insert_end", "tail")
    playground.linked_list_operation("insert_position", "middle", 1)
    assert playground.linked_list_operation("search", "middle")["message"].startswith(
        "Found middle"
    )
    assert playground.linked_list_operation(
        "delete",
        item_id="L003",
    )["snapshot"]["linked_list"] == [
        {"token_id": "L001", "value": "head"},
        {"token_id": "L002", "value": "tail"},
    ]

    playground.priority_queue_operation("enqueue", "standard", priority=7)
    playground.priority_queue_operation("enqueue", "urgent", priority=4)
    assert "urgent" in playground.priority_queue_operation("peek")["message"]
    playground.priority_queue_operation(
        "update_priority",
        priority=2,
        item_id="P001",
    )
    assert "standard" in playground.priority_queue_operation("peek")["message"]
    assert "standard" in playground.priority_queue_operation("dequeue")["message"]

    playground.bst_operation("insert", key="B", value="root")
    playground.bst_operation("insert", key="A", value="left")
    playground.bst_operation("insert", key="C", value="right")
    assert [item["token_id"] for item in playground.snapshot()["bst"]["inorder"]] == [
        "A",
        "B",
        "C",
    ]
    assert playground.bst_operation("search", key="A")["message"] == "Found A: left."
    assert playground.bst_operation("delete", key="B")["snapshot"]["bst"]["size"] == 2
    assert playground.bst_operation("preorder")["snapshot"]["bst"]["preorder"][0][
        "token_id"
    ] == "C"

    with pytest.raises(DuplicateStructureItem):
        playground.bst_operation("insert", key="A", value="duplicate")


@pytest.fixture(scope="module", autouse=True)
def isolated_database(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    previous_path = os.environ.get("QUEUELESS_DB_PATH")
    os.environ["QUEUELESS_DB_PATH"] = str(tmp_path_factory.mktemp("queueless-api") / "tests.db")
    api = importlib.import_module("backend.api.main")
    yield api
    if previous_path is None:
        os.environ.pop("QUEUELESS_DB_PATH", None)
    else:
        os.environ["QUEUELESS_DB_PATH"] = previous_path


@pytest.fixture(scope="module")
def isolated_api(isolated_database: Any) -> Iterator[tuple[Any, Any, dict[str, str]]]:
    from fastapi.testclient import TestClient

    api = isolated_database
    with TestClient(api.app) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@queueless.ai", "password": "admin123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        yield client, api, headers


def test_booking_policy_and_completed_token_response(
    isolated_api: tuple[Any, Any, dict[str, str]],
) -> None:
    client, api, headers = isolated_api
    service_id = next(iter(api.runtime.services))
    payload = {"customer_name": "Test Patient", "service_id": service_id}

    for unsupported in (
        {**payload, "priority_level": "PRIORITY"},
        {**payload, "arrival_offset_min": 120},
    ):
        assert client.post("/api/tokens/book", json=unsupported).status_code == 422

    booked = client.post("/api/tokens/book", json=payload)
    assert booked.status_code == 200
    token = booked.json()["token"]
    assert token["priority_level"] == "STANDARD"
    assert token["eta_min"] == booked.json()["recommendation"]["estimated_wait_min"]

    counter_id = token["counter_id"]
    for _ in range(20):
        called_response = client.post(
            f"/api/counters/{counter_id}/next",
            headers=headers,
        )
        assert called_response.status_code == 200
        called_token = called_response.json()["token"]
        if called_token["token_id"] == token["token_id"]:
            break
        assert client.post(
            f"/api/counters/{counter_id}/start",
            headers=headers,
        ).status_code == 200
        assert client.post(
            f"/api/counters/{counter_id}/complete",
            headers=headers,
        ).status_code == 200
    else:
        pytest.fail("The newly booked token was not found in the selected counter queue.")
    called = client.get(f"/api/tokens/{token['token_id']}")
    assert called.status_code == 200
    assert called.json()["eta_min"] is None

    assert client.post(
        f"/api/counters/{counter_id}/start",
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/api/counters/{counter_id}/complete",
        headers=headers,
    ).status_code == 200
    completed = client.get(f"/api/tokens/{token['token_id']}")
    assert completed.status_code == 200
    assert completed.json()["token"]["status"] == "S6_COMPLETED"
    assert completed.json()["token"]["eta_min"] is None
    assert completed.json()["token"]["assigned_path"] == []
    assert completed.json()["optimal_path"] == []


def test_data_structure_playground_isolated_per_authenticated_user(
    isolated_api: tuple[Any, Any, dict[str, str]],
) -> None:
    client, _api, admin_headers = isolated_api
    staff_login = client.post(
        "/api/auth/login",
        json={"email": "staff@queueless.ai", "password": "staff123"},
    )
    assert staff_login.status_code == 200
    staff_headers = {
        "Authorization": f"Bearer {staff_login.json()['access_token']}"
    }

    admin_result = client.post(
        "/api/ds/playground/array",
        headers=admin_headers,
        json={"operation": "insert", "value": "admin only"},
    )
    assert admin_result.status_code == 200
    assert admin_result.json()["snapshot"]["array"]["elements"][0]["value"] == "admin only"

    staff_snapshot = client.get("/api/ds/playground", headers=staff_headers)
    assert staff_snapshot.status_code == 200
    assert staff_snapshot.json()["array"]["elements"] == []

    invalid_position = client.post(
        "/api/ds/playground/array",
        headers=admin_headers,
        json={"operation": "delete", "index": 9},
    )
    assert invalid_position.status_code == 422


def test_service_and_counter_names_are_unique(
    isolated_api: tuple[Any, Any, dict[str, str]],
) -> None:
    client, api, headers = isolated_api
    existing_service_name = next(iter(api.runtime.services.values()))["name"]
    duplicate_service = client.post(
        "/api/services",
        headers=headers,
        json={
            "service_id": "SVC-TEST-DUP",
            "name": f"  {existing_service_name.upper()}  ",
            "category": "Test",
            "estimated_durations_min": {
                "Registration": 2,
                "Sample Collection": 3,
                "Report Collection": 1,
            },
        },
    )
    assert duplicate_service.status_code == 409
    service_ids = list(api.runtime.services)
    if len(service_ids) > 1:
        duplicate_service_update = client.put(
            f"/api/services/{service_ids[1]}",
            headers=headers,
            json={"name": existing_service_name},
        )
        assert duplicate_service_update.status_code == 409

    existing_counter_name = next(iter(api.runtime.counter_names.values()))
    service_id = next(iter(api.runtime.services))
    duplicate_counter = client.post(
        "/api/counters",
        headers=headers,
        json={
            "counter_id": "99",
            "name": existing_counter_name.swapcase(),
            "supported_services": [service_id],
        },
    )
    assert duplicate_counter.status_code == 409
    counter_ids = list(api.runtime.counter_names)
    if len(counter_ids) > 1:
        duplicate_counter_update = client.put(
            f"/api/counters/{counter_ids[1]}",
            headers=headers,
            json={"name": existing_counter_name},
        )
        assert duplicate_counter_update.status_code == 409


def test_counter_lifecycle_rejects_empty_queue_and_duplicate_transitions(
    isolated_api: tuple[Any, Any, dict[str, str]],
) -> None:
    client, api, headers = isolated_api
    service_id = next(iter(api.runtime.services))
    counter_id = "88"
    created = client.post(
        "/api/counters",
        headers=headers,
        json={
            "counter_id": counter_id,
            "name": "Lifecycle Test Counter",
            "supported_services": [service_id],
        },
    )
    assert created.status_code == 200
    for existing_counter_id in list(api.runtime.counter_lists):
        if existing_counter_id == counter_id:
            continue
        closed = client.put(
            f"/api/counters/{existing_counter_id}",
            headers=headers,
            json={"status": "CLOSED"},
        )
        assert closed.status_code == 200
    assert client.post(
        f"/api/counters/{counter_id}/next",
        headers=headers,
    ).status_code == 404

    booking = client.post(
        "/api/tokens/book",
        json={"customer_name": "Lifecycle Test", "service_id": service_id},
    )
    assert booking.status_code == 200
    token_id = booking.json()["token"]["token_id"]
    assert booking.json()["token"]["counter_id"] == counter_id

    called = client.post(f"/api/counters/{counter_id}/next", headers=headers)
    assert called.status_code == 200
    assert called.json()["token"]["token_id"] == token_id
    assert client.post(
        f"/api/counters/{counter_id}/next",
        headers=headers,
    ).status_code == 409

    started = client.post(f"/api/counters/{counter_id}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["token"]["status"] == "S5_IN_PROGRESS"
    assert client.post(
        f"/api/counters/{counter_id}/start",
        headers=headers,
    ).status_code == 409
    assert client.post(
        f"/api/counters/{counter_id}/next",
        headers=headers,
    ).status_code == 409

    completed = client.post(f"/api/counters/{counter_id}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["token"]["status"] == "S6_COMPLETED"
    assert client.post(
        f"/api/counters/{counter_id}/complete",
        headers=headers,
    ).status_code == 409
