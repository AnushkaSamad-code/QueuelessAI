"""QueueLess AI FastAPI application with SQLite and in-memory structures."""

from __future__ import annotations

import json
import hashlib
import hmac
import math
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Callable, Literal, Sequence

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

try:
    from backend.ds.custom_array import TokenArray
    from backend.ds.linked_list import ServiceLinkedList
    from backend.ds.priority_queue import SchedulingPriorityQueue
    from backend.ds.bst import TokenBST
    from backend.ds.playground import (
        DataStructurePlayground,
        DuplicateStructureItem,
    )
    from backend.ai.graph_model import (
        SERVICE_ROUTE_STAGES,
        build_service_route_graph,
        minimum_remaining_stage_duration,
        GraphEdge,
    )
    from backend.ai.counter_assignment import assign_best_counter
    from backend.ai.bfs import breadth_first_search
    from backend.ai.ucs import uniform_cost_search
    from backend.ai.astar import a_star_search
except ImportError:
    BACKEND_ROOT = Path(__file__).resolve().parents[1]
    if str(BACKEND_ROOT.parent) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT.parent))
    from backend.ds.custom_array import TokenArray
    from backend.ds.linked_list import ServiceLinkedList
    from backend.ds.priority_queue import SchedulingPriorityQueue
    from backend.ds.bst import TokenBST
    from backend.ds.playground import (
        DataStructurePlayground,
        DuplicateStructureItem,
    )
    from backend.ai.graph_model import (
        SERVICE_ROUTE_STAGES,
        build_service_route_graph,
        minimum_remaining_stage_duration,
        GraphEdge,
    )
    from backend.ai.counter_assignment import assign_best_counter
    from backend.ai.bfs import breadth_first_search
    from backend.ai.ucs import uniform_cost_search
    from backend.ai.astar import a_star_search


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
SEED_PATH = DATA_DIR / "diagnostic_lab_seed.json"
DB_PATH = Path(os.getenv("QUEUELESS_DB_PATH", str(DATA_DIR / "queueless.db")))


class BookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(min_length=1, max_length=120)
    service_id: str = Field(min_length=1, max_length=32)
    priority_level: Literal["STANDARD"] = "STANDARD"


class SearchRequest(BaseModel):
    algorithm: Literal["BFS", "UCS", "A*"] = "A*"
    service_id: str | None = None
    start_state: str = "Registration"
    goal_state: str = "Service Completed"


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str


class ServiceRequest(BaseModel):
    service_id: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    estimated_durations_min: dict[str, float]


class ServiceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    estimated_durations_min: dict[str, float] | None = None


class CounterRequest(BaseModel):
    counter_id: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    status: Literal["OPEN", "CLOSED"] = "OPEN"
    supported_services: list[str] = Field(default_factory=list)


class CounterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: Literal["OPEN", "CLOSED"] | None = None
    supported_services: list[str] | None = None


class ArrayOperationRequest(BaseModel):
    operation: Literal["insert", "delete", "search", "update", "traverse"]
    value: str | None = Field(default=None, max_length=120)
    index: int | None = Field(default=None, ge=0)


class LinkedListOperationRequest(BaseModel):
    operation: Literal[
        "insert_beginning",
        "insert_end",
        "insert_position",
        "delete",
        "search",
        "traverse",
    ]
    value: str | None = Field(default=None, max_length=120)
    position: int | None = Field(default=None, ge=0)
    item_id: str | None = Field(default=None, max_length=32)


class PriorityQueueOperationRequest(BaseModel):
    operation: Literal["enqueue", "dequeue", "peek", "update_priority", "display"]
    value: str | None = Field(default=None, max_length=120)
    priority: int | None = Field(default=None, ge=0, le=9)
    item_id: str | None = Field(default=None, max_length=32)


class BSTOperationRequest(BaseModel):
    operation: Literal["insert", "search", "delete", "inorder", "preorder", "postorder"]
    key: str | None = Field(default=None, max_length=120)
    value: str | None = Field(default=None, max_length=120)


def _password_hash(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 240_000
    ).hex()
    return f"pbkdf2_sha256${actual_salt}${digest}"


def _password_matches(password: str, encoded_hash: str) -> bool:
    algorithm, salt, _ = encoded_hash.split("$", 2)
    return algorithm == "pbkdf2_sha256" and hmac.compare_digest(
        encoded_hash, _password_hash(password, salt)
    )


def _stage_durations(service: dict[str, object]) -> dict[str, float]:
    raw = service.get("estimated_durations_min", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(stage).strip().lower().replace(" ", "_"): float(duration)
        for stage, duration in raw.items()
    }


def _validate_durations(durations: dict[str, float]) -> dict[str, float]:
    aliases = {
        "registration": "registration",
        "sample collection": "sample_collection",
        "sample_collection": "sample_collection",
        "report collection": "report_collection",
        "report_collection": "report_collection",
    }
    unknown_stages = [
        stage for stage in durations if stage.strip().lower() not in aliases
    ]
    if unknown_stages:
        raise HTTPException(status_code=422, detail="Unknown diagnostic stage in durations.")
    normalized = {
        aliases[stage.strip().lower()]: float(duration)
        for stage, duration in durations.items()
    }
    if set(normalized) != {"registration", "sample_collection", "report_collection"}:
        raise HTTPException(
            status_code=422,
            detail="Durations must include Registration, Sample Collection, and Report Collection.",
        )
    if any(not math.isfinite(duration) or duration <= 0 for duration in normalized.values()):
        raise HTTPException(status_code=422, detail="Stage durations must be positive.")
    return normalized


def _parse_utc_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _waiting_time_summary(
    tokens: Sequence[dict[str, object]],
) -> dict[str, object]:
    eligible_statuses = {"S5_IN_PROGRESS", "S6_COMPLETED"}
    total_minutes = 0.0
    sample_count = 0
    excluded = {
        "status": 0,
        "missing_timestamp": 0,
        "invalid_timestamp": 0,
        "negative_duration": 0,
    }
    for token in tokens:
        if token.get("status") not in eligible_statuses:
            excluded["status"] += 1
            continue
        arrival_value = token.get("arrival_timestamp")
        started_value = token.get("service_started_at")
        if not arrival_value or not started_value:
            excluded["missing_timestamp"] += 1
            continue
        arrival = _parse_utc_timestamp(arrival_value)
        started = _parse_utc_timestamp(started_value)
        if arrival is None or started is None:
            excluded["invalid_timestamp"] += 1
            continue
        elapsed_seconds = (started - arrival).total_seconds()
        if elapsed_seconds < 0:
            excluded["negative_duration"] += 1
            continue
        total_minutes += elapsed_seconds / 60.0
        sample_count += 1
    return {
        "average_wait_min": (
            round(total_minutes / sample_count, 2) if sample_count else None
        ),
        "waiting_time_sample_count": sample_count,
        "waiting_time_excluded": excluded,
    }


class QueueLessState:
    """Owns SQLite and all live QueueLess runtime structures."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.ds_playgrounds: dict[int, DataStructurePlayground] = {}
        self.seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.services = {
            service["service_id"]: service
            for service in self.seed["services"]
        }
        self.counter_status: dict[str, str] = {
            counter["counter_id"]: counter["status"]
            for counter in self.seed["counters"]
        }
        self.counter_names: dict[str, str] = {
            counter["counter_id"]: counter["name"]
            for counter in self.seed["counters"]
        }
        all_service_ids = [str(service["service_id"]) for service in self.seed["services"]]
        self.counter_supported_services: dict[str, list[str]] = {
            counter["counter_id"]: list(counter.get("supported_services", all_service_ids))
            for counter in self.seed["counters"]
        }
        self.array = TokenArray[dict[str, object]](capacity=16, maximum_capacity=999)
        self.bst = TokenBST[dict[str, object]]()
        self.priority_queue = SchedulingPriorityQueue[dict[str, object]]()
        self.counter_lists = {
            counter["counter_id"]: ServiceLinkedList[dict[str, object]]()
            for counter in self.seed["counters"]
        }
        self.current_by_counter: dict[str, dict[str, object] | None] = {
            counter_id: None for counter_id in self.counter_lists
        }
        self.service_graph = build_service_route_graph()
        self._initialize_database()
        self._load_config_from_database()
        self._hydrate_seeded_state()

    def _connect(self) -> sqlite3.Connection:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    counter_id TEXT PRIMARY KEY,
                    counter_name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                    supported_services TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS services (
                    service_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    required_stages TEXT NOT NULL,
                    estimated_durations TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tokens (
                    token_id TEXT PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    priority_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    counter_id TEXT,
                    assigned_path TEXT NOT NULL,
                    eta_min REAL NOT NULL,
                    arrival_timestamp TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    service_started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY(counter_id) REFERENCES counters(counter_id)
                );
                CREATE TABLE IF NOT EXISTS search_logs (
                    search_id INTEGER PRIMARY KEY,
                    token_id TEXT,
                    algorithm TEXT NOT NULL,
                    source_node TEXT NOT NULL,
                    goal_node TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tokens_status
                    ON tokens(status);
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('CUSTOMER', 'STAFF', 'ADMIN'))
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            token_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(tokens)").fetchall()
            }
            legacy_token_lifecycle = "service_started_at" not in token_columns
            if "service_started_at" not in token_columns:
                connection.execute("ALTER TABLE tokens ADD COLUMN service_started_at TEXT")
            if "completed_at" not in token_columns:
                connection.execute("ALTER TABLE tokens ADD COLUMN completed_at TEXT")
            if legacy_token_lifecycle:
                connection.execute(
                    """
                    UPDATE tokens SET status = 'S3_WAITING'
                    WHERE status = 'S4_COUNTER_ASSIGNED'
                    """
                )
                connection.execute(
                    """
                    UPDATE tokens SET service_started_at = updated_at
                    WHERE status = 'S5_IN_PROGRESS' AND service_started_at IS NULL
                    """
                )
            counter_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(counters)").fetchall()
            }
            if "supported_services" not in counter_columns:
                connection.execute(
                    "ALTER TABLE counters ADD COLUMN supported_services TEXT NOT NULL DEFAULT '[]'"
                )
                all_service_ids = json.dumps(
                    [service["service_id"] for service in self.seed["services"]]
                )
                for counter in self.seed["counters"]:
                    connection.execute(
                        """
                        UPDATE counters SET supported_services = ?
                        WHERE counter_id = ? AND supported_services = '[]'
                        """,
                        (all_service_ids, counter["counter_id"]),
                    )
            for counter in self.seed["counters"]:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO counters(
                        counter_id, counter_name, status, supported_services
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        counter["counter_id"],
                        counter["name"],
                        counter["status"],
                        json.dumps(
                            counter.get("supported_services", [
                                service["service_id"] for service in self.seed["services"]
                            ])
                        ),
                    ),
                )
            for service in self.seed["services"]:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO services(
                        service_id, name, category, required_stages, estimated_durations
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        service["service_id"],
                        service["name"],
                        service["category"],
                        json.dumps(service["required_stages"]),
                        json.dumps(service["estimated_durations_min"]),
                    ),
                )
            demo_users = (
                ("QueueLess Administrator", "admin@queueless.ai", "admin123", "ADMIN"),
                ("QueueLess Staff", "staff@queueless.ai", "staff123", "STAFF"),
                ("Demo Customer", "patient@queueless.ai", "patient123", "CUSTOMER"),
            )
            for full_name, email, password, role in demo_users:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO users(full_name, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (full_name, email, _password_hash(password), role),
                )

    def _load_config_from_database(self) -> None:
        with self._connect() as connection:
            service_rows = connection.execute(
                "SELECT * FROM services ORDER BY service_id"
            ).fetchall()
            counter_rows = connection.execute(
                "SELECT * FROM counters ORDER BY counter_id"
            ).fetchall()
        self.services = {}
        for row in service_rows:
            self.services[str(row["service_id"])] = {
                "service_id": str(row["service_id"]),
                "name": str(row["name"]),
                "category": str(row["category"]),
                "required_stages": json.loads(str(row["required_stages"])),
                "estimated_durations_min": json.loads(str(row["estimated_durations"])),
            }
        self.seed["services"] = list(self.services.values())
        self.counter_lists = {}
        self.current_by_counter = {}
        self.counter_status = {}
        self.counter_names = {}
        self.counter_supported_services = {}
        self.seed["counters"] = []
        for row in counter_rows:
            counter_id = str(row["counter_id"])
            try:
                supported = json.loads(str(row["supported_services"]))
            except json.JSONDecodeError:
                supported = []
            counter = {
                "counter_id": counter_id,
                "name": str(row["counter_name"]),
                "status": str(row["status"]),
                "supported_services": supported,
            }
            self.seed["counters"].append(counter)
            self.counter_lists[counter_id] = ServiceLinkedList[dict[str, object]]()
            self.current_by_counter[counter_id] = None
            self.counter_status[counter_id] = str(row["status"])
            self.counter_names[counter_id] = str(row["counter_name"])
            self.counter_supported_services[counter_id] = list(supported)

    def _hydrate_seeded_state(self) -> None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            db_tokens = connection.execute(
                "SELECT * FROM tokens ORDER BY token_id"
            ).fetchall()
        for row in db_tokens:
            self._hydrate_token(dict(row))

        if db_tokens:
            return

        for seed_token in self.seed["sample_tokens"]:
            arrival = now - timedelta(minutes=seed_token["arrival_offset_min"])
            recommendation = self._recommend_counter(seed_token["service_id"])
            token = {
                "token_id": seed_token["token_id"],
                "customer_name": seed_token["customer_name"],
                "service_id": seed_token["service_id"],
                "priority_level": seed_token["priority_level"],
                "status": "S3_WAITING",
                "counter_id": recommendation["counter_id"],
                "assigned_path": recommendation["optimal_path"],
                "eta_min": recommendation["total_cost"],
                "arrival_timestamp": arrival.isoformat(),
                "updated_at": now.isoformat(),
                "service_started_at": None,
                "completed_at": None,
            }
            self._insert_runtime_token(token)
            self._persist_token(token)

    def _hydrate_token(self, token: dict[str, object]) -> None:
        if isinstance(token["assigned_path"], str):
            try:
                token["assigned_path"] = json.loads(token["assigned_path"])
            except json.JSONDecodeError:
                token["assigned_path"] = []
        arrival = datetime.fromisoformat(str(token["arrival_timestamp"]))
        if arrival.tzinfo is None:
            arrival = arrival.replace(tzinfo=timezone.utc)
        priority = self._base_priority(str(token["priority_level"]))
        self.array.append(token)
        self.bst.insert(str(token["token_id"]), token)
        counter_id = str(token["counter_id"])
        if counter_id not in self.counter_lists:
            return
        if token["status"] in ("S4_COUNTER_ASSIGNED", "S5_IN_PROGRESS"):
            if self.current_by_counter[counter_id] is not None:
                raise RuntimeError(f"multiple active tokens for counter {counter_id}")
            self.current_by_counter[counter_id] = token
        elif token["status"] == "S3_WAITING":
            self.priority_queue.enqueue(
                token,
                str(token["token_id"]),
                priority,
                arrival,
            )
            self.counter_lists[counter_id].insert_tail(token)

    def _insert_runtime_token(self, token: dict[str, object]) -> None:
        existing = self.array.linear_search(
            lambda record: record["token_id"] == token["token_id"]
        )
        if existing is not None:
            raise ValueError("duplicate token_id")
        self.array.append(token)
        self.bst.insert(str(token["token_id"]), token)
        arrival = datetime.fromisoformat(str(token["arrival_timestamp"]))
        if arrival.tzinfo is None:
            arrival = arrival.replace(tzinfo=timezone.utc)
        counter_id = str(token["counter_id"])
        if counter_id not in self.counter_lists:
            raise RuntimeError(f"token references unknown counter {counter_id}")
        if token["status"] != "S3_WAITING":
            raise ValueError("new tokens must enter the waiting queue")
        self.priority_queue.enqueue(
            token,
            str(token["token_id"]),
            self._base_priority(str(token["priority_level"])),
            arrival,
        )
        self.counter_lists[counter_id].insert_tail(token)

    def _persist_token(self, token: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tokens(
                    token_id, customer_name, service_id, priority_level,
                    status, counter_id, assigned_path, eta_min,
                    arrival_timestamp, updated_at, service_started_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_id) DO UPDATE SET
                    customer_name=excluded.customer_name,
                    service_id=excluded.service_id,
                    priority_level=excluded.priority_level,
                    status=excluded.status,
                    counter_id=excluded.counter_id,
                    assigned_path=excluded.assigned_path,
                    eta_min=excluded.eta_min,
                    arrival_timestamp=excluded.arrival_timestamp,
                    updated_at=excluded.updated_at,
                    service_started_at=excluded.service_started_at,
                    completed_at=excluded.completed_at
                """,
                (
                    token["token_id"],
                    token["customer_name"],
                    token["service_id"],
                    token["priority_level"],
                    token["status"],
                    token["counter_id"],
                    json.dumps(token["assigned_path"]),
                    float(token["eta_min"]),
                    token["arrival_timestamp"],
                    token["updated_at"],
                    token.get("service_started_at"),
                    token.get("completed_at"),
                ),
            )

    @staticmethod
    def _base_priority(priority_level: str) -> int:
        return {"STANDARD": 2, "APPOINTMENT": 1, "PRIORITY": 0}[priority_level]

    def _recommend_counter(self, service_id: str) -> dict[str, object]:
        if service_id not in self.services:
            raise HTTPException(status_code=404, detail="Unknown service_id")
        durations = _stage_durations(self.services[service_id])
        service_duration = sum(durations.values())
        workloads: dict[str, float] = {}
        for counter_id, linked_list in self.counter_lists.items():
            workload = 0.0
            for queued_token in linked_list.traverse():
                queued_service = self.services.get(str(queued_token["service_id"]), {})
                workload += sum(_stage_durations(queued_service).values())
            current = self.current_by_counter[counter_id]
            if current is not None:
                current_service = self.services.get(str(current["service_id"]), {})
                workload += sum(_stage_durations(current_service).values())
            workloads[counter_id] = workload
        counters = [
            {
                "counter_id": counter_id,
                "status": status,
                "supported_services": self.counter_supported_services[counter_id],
            }
            for counter_id, status in self.counter_status.items()
        ]
        try:
            assignment = assign_best_counter(
                service_id,
                counters,
                workloads,
                service_duration,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        graph = build_service_route_graph(durations)
        result = a_star_search(
            graph,
            SERVICE_ROUTE_STAGES[0],
            SERVICE_ROUTE_STAGES[-1],
            lambda node: minimum_remaining_stage_duration(node, durations),
        )
        self.service_graph = graph
        return {
            **assignment,
            "optimal_path": result["optimal_path"],
            "route_cost": result["total_cost"] or 0.0,
        }

    def call_next(self, counter_id: str) -> dict[str, object]:
        if counter_id not in self.counter_lists:
            raise KeyError(counter_id)
        if self.counter_status[counter_id] != "OPEN":
            raise HTTPException(status_code=409, detail=f"{counter_id} is closed")
        if self.current_by_counter[counter_id] is not None:
            raise HTTPException(status_code=409, detail="Complete the current service first")

        if self.counter_lists[counter_id].length == 0:
            raise HTTPException(status_code=404, detail="No token waiting at this counter")

        now = datetime.now(timezone.utc)
        next_token_id: str | None = None
        next_key: tuple[int, datetime, str] | None = None
        for item in self.priority_queue.to_heap_snapshot(now):
            candidate_id = str(item["token_id"])
            candidate = self.bst.search(candidate_id)
            if candidate is None:
                raise RuntimeError(f"scheduled token {candidate_id} is missing from BST")
            if candidate["counter_id"] != counter_id:
                continue
            key = (
                int(item["effective_priority"]),
                datetime.fromisoformat(str(item["arrival_timestamp"])),
                candidate_id,
            )
            if next_key is None or key < next_key:
                next_token_id = candidate_id
                next_key = key
        if next_token_id is None:
            raise RuntimeError(
                f"waiting tokens for {counter_id} are missing from priority queue"
            )

        token = self.counter_lists[counter_id].search(next_token_id)
        if token is None:
            raise RuntimeError(f"scheduled token {next_token_id} is missing from counter list")
        token_id = str(token["token_id"])
        try:
            scheduled = self.priority_queue.remove(token_id)
        except KeyError as exc:
            raise RuntimeError(f"waiting token {token_id} is missing from priority queue") from exc
        called = dict(token)
        called["status"] = "S4_COUNTER_ASSIGNED"
        called["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self._persist_token(called)
        except sqlite3.Error:
            self.priority_queue.insert(scheduled)
            raise
        self.counter_lists[counter_id].delete_by_token_id(token_id)
        token.update(called)
        self.current_by_counter[counter_id] = token
        return token

    def start_service(self, counter_id: str) -> dict[str, object]:
        token = self.current_by_counter.get(counter_id)
        if token is None:
            raise HTTPException(status_code=404, detail="No token has been called to this counter")
        if token["status"] != "S4_COUNTER_ASSIGNED":
            raise HTTPException(status_code=409, detail="Token is not awaiting service start")
        updated = dict(token)
        now = datetime.now(timezone.utc).isoformat()
        updated.update({"status": "S5_IN_PROGRESS", "service_started_at": now, "updated_at": now})
        self._persist_token(updated)
        token.update(updated)
        return token

    def complete_service(self, counter_id: str) -> dict[str, object]:
        token = self.current_by_counter.get(counter_id)
        if token is None or token["status"] != "S5_IN_PROGRESS":
            raise HTTPException(status_code=409, detail="No service is currently in progress")
        updated = dict(token)
        now = datetime.now(timezone.utc).isoformat()
        updated.update({"status": "S6_COMPLETED", "completed_at": now, "updated_at": now})
        self._persist_token(updated)
        token.update(updated)
        self.current_by_counter[counter_id] = None
        return token

    def search(self, request: SearchRequest) -> dict[str, object]:
        service_id = request.service_id or next(iter(self.services))
        if service_id not in self.services:
            raise HTTPException(status_code=404, detail="Unknown service_id")
        durations = _stage_durations(self.services[service_id])
        graph = build_service_route_graph(durations)
        self.service_graph = graph
        if request.algorithm == "BFS":
            result = breadth_first_search(
                graph,
                request.start_state,
                request.goal_state,
            )
        elif request.algorithm == "UCS":
            result = uniform_cost_search(
                graph,
                request.start_state,
                request.goal_state,
            )
        else:
            result = a_star_search(
                graph,
                request.start_state,
                request.goal_state,
                lambda node: minimum_remaining_stage_duration(
                    node,
                    durations,
                    request.goal_state,
                ),
            )
        payload = dict(result)
        payload["graph"] = self._export_graph(graph)
        payload["service_id"] = service_id
        payload["heuristic_formula"] = (
            "h(n) = remaining stage durations from n to the selected goal"
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO search_logs(
                    token_id, algorithm, source_node, goal_node, result_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    request.algorithm,
                    request.start_state,
                    request.goal_state,
                    json.dumps(payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        payload["algorithm"] = request.algorithm
        return payload

    def compare_search(self, request: SearchRequest) -> dict[str, object]:
        selected_service = request.service_id or next(iter(self.services))
        results = {
            algorithm: self.search(
                SearchRequest(
                    algorithm=algorithm,
                    service_id=selected_service,
                    start_state=request.start_state,
                    goal_state=request.goal_state,
                )
            )
            for algorithm in ("BFS", "UCS", "A*")
        }
        return {
            "service_id": selected_service,
            "graph": results["A*"]["graph"],
            "results": results,
            "problem_formulation": {
                "initial_state": request.start_state,
                "goal_state": request.goal_state,
                "actions": ["Complete the current diagnostic stage"],
                "transition_model": "Registration → Sample Collection → Report Collection → Service Completed",
                "path_cost_function": "g(n) = cumulative estimated stage duration in minutes",
                "heuristic_function": "h(n) = remaining stage durations from n to the selected goal",
                "goal_test": "Current state equals Service Completed",
            },
        }

    @staticmethod
    def _export_graph(
        graph: dict[str, Sequence[GraphEdge]],
    ) -> dict[str, list[dict[str, object]]]:
        nodes = [
            {
                "id": stage,
                "label": stage,
                "x": index * 210 + 110,
                "y": 120,
                "lifecycle_state": "S6_COMPLETED" if index == 3 else "S5_IN_PROGRESS",
                "counter_id": None,
                "stage": stage,
            }
            for index, stage in enumerate(SERVICE_ROUTE_STAGES)
        ]
        edges: list[dict[str, object]] = []
        positions = {node["id"]: node for node in nodes}
        for source, outgoing in graph.items():
            for edge in outgoing:
                edges.append(
                    {
                        "source": source,
                        "target": edge.target,
                        "action": edge.action,
                        "cost": edge.cost,
                        "source_x": positions[source]["x"],
                        "source_y": positions[source]["y"],
                        "target_x": positions[edge.target]["x"],
                        "target_y": positions[edge.target]["y"],
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def state_snapshot(self) -> dict[str, object]:
        all_tokens = list(self.array.traverse())
        active = [token for token in all_tokens if token["status"] != "S6_COMPLETED"]
        queues = {
            counter_id: [token for token in linked_list.traverse()]
            for counter_id, linked_list in self.counter_lists.items()
        }
        return {
            "counters": [
                {
                    "counter_id": counter["counter_id"],
                    "name": counter["name"],
                    "status": self.counter_status[counter["counter_id"]],
                    "queue_length": self.counter_lists[counter["counter_id"]].length,
                    "current_token_id": (
                        self.current_by_counter[counter["counter_id"]]["token_id"]
                        if self.current_by_counter[counter["counter_id"]] is not None
                        else None
                    ),
                    "supported_services": self.counter_supported_services[counter["counter_id"]],
                }
                for counter in self.seed["counters"]
            ],
            "active_tokens": active,
            "queues": queues,
            "stats": {
                "active_token_count": len(active),
                "waiting_count": sum(
                    1
                    for token in active
                    if token["status"] in ("S3_WAITING", "S4_COUNTER_ASSIGNED")
                ),
                "in_progress_count": sum(
                    1 for token in active if token["status"] == "S5_IN_PROGRESS"
                ),
                "completed_count": sum(
                    1 for token in all_tokens if token["status"] == "S6_COMPLETED"
                ),
                "average_eta_min": (
                    round(
                        sum(
                            float(token["eta_min"])
                            for token in active
                            if token["status"] == "S3_WAITING"
                        )
                        / sum(token["status"] == "S3_WAITING" for token in active),
                        2,
                    )
                    if any(token["status"] == "S3_WAITING" for token in active)
                    else None
                ),
                "priority_queue_size": self.priority_queue.size,
            },
        }

    def ds_snapshot(self) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        token_array = self.array.to_dict()
        token_array["slots"] = token_array["elements"] + [
            None
        ] * (self.array.capacity - self.array.size)
        return {
            "token_array": token_array,
            "counter_linked_lists": {
                counter_id: [token for token in linked.traverse()]
                for counter_id, linked in self.counter_lists.items()
            },
            "priority_queue": self.priority_queue.to_heap_snapshot(now),
            "bst": {
                "inorder": [payload for payload in self.bst.inorder()],
                "preorder": [payload for payload in self.bst.preorder()],
                "postorder": [payload for payload in self.bst.postorder()],
            },
        }


runtime = QueueLessState()
app = FastAPI(title="QueueLess AI", version="1.0")
local_frontend_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
production_frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=local_frontend_origins + production_frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


security = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, object]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    with runtime._connect() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.full_name, users.email, users.role
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return dict(row)


def require_roles(*roles: str):
    def check_role(user: dict[str, object] = Depends(current_user)) -> dict[str, object]:
        if str(user["role"]) not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return user

    return check_role


def _session_response(user: dict[str, object]) -> dict[str, object]:
    raw_token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with runtime._connect() as connection:
        connection.execute(
            "INSERT INTO sessions(token_hash, user_id, created_at) VALUES (?, ?, ?)",
            (token_hash, user["id"], datetime.now(timezone.utc).isoformat()),
        )
    return {
        "access_token": raw_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.post("/api/auth/signup")
def signup(request: SignupRequest) -> dict[str, object]:
    email = request.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    try:
        with runtime._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users(full_name, email, password_hash, role)
                VALUES (?, ?, ?, 'CUSTOMER')
                """,
                (request.full_name.strip(), email, _password_hash(request.password)),
            )
            user = {
                "id": cursor.lastrowid,
                "full_name": request.full_name.strip(),
                "email": email,
                "role": "CUSTOMER",
            }
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    return _session_response(user)


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict[str, object]:
    with runtime._connect() as connection:
        row = connection.execute(
            "SELECT id, full_name, email, password_hash, role FROM users WHERE email = ?",
            (request.email.strip().lower(),),
        ).fetchone()
    if row is None or not _password_matches(request.password, str(row["password_hash"])):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return _session_response(dict(row))


@app.get("/api/auth/me")
def get_current_user(user: dict[str, object] = Depends(current_user)) -> dict[str, object]:
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
    }


@app.post("/api/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    _user: dict[str, object] = Depends(current_user),
) -> dict[str, bool]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    with runtime._connect() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    return {"logged_out": True}


@app.get("/api/services")
def get_services() -> list[dict[str, object]]:
    return [
        {
            **service,
            "duration": f"{sum(_stage_durations(service).values()):g} min",
            "description": str(service["category"]),
        }
        for service in runtime.services.values()
    ]


def _clean_required_name(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail=f"{field_name} is required")
    return cleaned


def _ensure_unique_service_name(name: str, excluding_id: str | None = None) -> None:
    normalized_name = name.casefold()
    for service_id, service in runtime.services.items():
        if service_id == excluding_id:
            continue
        if str(service["name"]).strip().casefold() == normalized_name:
            raise HTTPException(status_code=409, detail="Service name already exists")


def _ensure_unique_counter_name(name: str, excluding_id: str | None = None) -> None:
    normalized_name = name.casefold()
    for counter_id, current_name in runtime.counter_names.items():
        if counter_id != excluding_id and current_name.strip().casefold() == normalized_name:
            raise HTTPException(status_code=409, detail="Counter name already exists")


@app.post("/api/services")
def create_service(
    request: ServiceRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        service_id = request.service_id.strip()
        if not service_id:
            raise HTTPException(status_code=422, detail="Service ID is required")
        if service_id in runtime.services:
            raise HTTPException(status_code=409, detail="Service ID already exists")
        name = _clean_required_name(request.name, "Service name")
        category = _clean_required_name(request.category, "Category")
        _ensure_unique_service_name(name)
        durations = _validate_durations(request.estimated_durations_min)
        stage_labels = {
            "registration": "Registration",
            "sample_collection": "Sample Collection",
            "report_collection": "Report Collection",
        }
        service = {
            "service_id": service_id,
            "name": name,
            "category": category,
            "required_stages": list(stage_labels.values()),
            "estimated_durations_min": {
                stage_labels[key]: value for key, value in durations.items()
            },
        }
        next_supported_services = {
            counter_id: [*supported, service_id]
            for counter_id, supported in runtime.counter_supported_services.items()
        }
        try:
            with runtime._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO services(service_id, name, category, required_stages, estimated_durations)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        service_id,
                        service["name"],
                        service["category"],
                        json.dumps(service["required_stages"]),
                        json.dumps(service["estimated_durations_min"]),
                    ),
                )
                for counter_id, supported in next_supported_services.items():
                    connection.execute(
                        "UPDATE counters SET supported_services = ? WHERE counter_id = ?",
                        (json.dumps(supported), counter_id),
                    )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Service already exists") from exc
        runtime.counter_supported_services = next_supported_services
        runtime.services[service_id] = service
    return service


@app.put("/api/services/{service_id}")
def update_service(
    service_id: str,
    request: ServiceUpdateRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        service = runtime.services.get(service_id)
        if service is None:
            raise HTTPException(status_code=404, detail="Service not found")
        updated = dict(service)
        if request.name is not None:
            updated["name"] = _clean_required_name(request.name, "Service name")
        if request.category is not None:
            updated["category"] = _clean_required_name(request.category, "Category")
        _ensure_unique_service_name(str(updated["name"]).strip(), service_id)
        if request.estimated_durations_min is not None:
            durations = _validate_durations(request.estimated_durations_min)
            stage_labels = {
                "registration": "Registration",
                "sample_collection": "Sample Collection",
                "report_collection": "Report Collection",
            }
            updated["estimated_durations_min"] = {
                stage_labels[key]: value for key, value in durations.items()
            }
        try:
            with runtime._connect() as connection:
                connection.execute(
                    """
                    UPDATE services SET name = ?, category = ?, required_stages = ?,
                        estimated_durations = ? WHERE service_id = ?
                    """,
                    (
                        updated["name"],
                        updated["category"],
                        json.dumps(updated["required_stages"]),
                        json.dumps(updated["estimated_durations_min"]),
                        service_id,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Service already exists") from exc
        runtime.services[service_id] = updated
        return updated


@app.get("/api/counters")
def get_counters(
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> list[dict[str, object]]:
    with runtime.lock:
        return runtime.state_snapshot()["counters"]


@app.post("/api/counters")
def create_counter(
    request: CounterRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        counter_id = request.counter_id.strip()
        name = _clean_required_name(request.name, "Counter name")
        if not counter_id:
            raise HTTPException(status_code=422, detail="Counter ID is required")
        if counter_id in runtime.counter_lists:
            raise HTTPException(status_code=409, detail="Counter ID already exists")
        _ensure_unique_counter_name(name)
        unknown_services = set(request.supported_services) - set(runtime.services)
        if unknown_services:
            raise HTTPException(status_code=422, detail="Counter references an unknown service")
        try:
            with runtime._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO counters(counter_id, counter_name, status, supported_services)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        counter_id,
                        name,
                        request.status,
                        json.dumps(request.supported_services),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Counter already exists") from exc
        runtime.counter_lists[counter_id] = ServiceLinkedList[dict[str, object]]()
        runtime.current_by_counter[counter_id] = None
        runtime.counter_status[counter_id] = request.status
        runtime.counter_names[counter_id] = name
        runtime.counter_supported_services[counter_id] = request.supported_services
        runtime.seed["counters"].append(
            {
                "counter_id": counter_id,
                "name": name,
                "status": request.status,
                "supported_services": request.supported_services,
            }
        )
        return runtime.state_snapshot()["counters"][-1]


@app.put("/api/counters/{counter_id}")
def update_counter(
    counter_id: str,
    request: CounterUpdateRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        if counter_id not in runtime.counter_lists:
            raise HTTPException(status_code=404, detail="Counter not found")
        if request.status == "CLOSED" and runtime.current_by_counter[counter_id] is not None:
            raise HTTPException(status_code=409, detail="Complete the current service before closing")
        supported = request.supported_services
        if supported is not None and set(supported) - set(runtime.services):
            raise HTTPException(status_code=422, detail="Counter references an unknown service")
        name = (
            _clean_required_name(request.name, "Counter name")
            if request.name is not None
            else runtime.counter_names[counter_id]
        )
        _ensure_unique_counter_name(name, counter_id)
        status = request.status or runtime.counter_status[counter_id]
        next_supported = (
            supported
            if supported is not None
            else runtime.counter_supported_services[counter_id]
        )
        with runtime._connect() as connection:
            connection.execute(
                """
                UPDATE counters SET counter_name = ?, status = ?, supported_services = ?
                WHERE counter_id = ?
                """,
                (name, status, json.dumps(next_supported), counter_id),
            )
        runtime.counter_names[counter_id] = name
        runtime.counter_status[counter_id] = status
        runtime.counter_supported_services[counter_id] = next_supported
        for counter in runtime.seed["counters"]:
            if counter["counter_id"] == counter_id:
                counter.update(
                    {"name": name, "status": status, "supported_services": next_supported}
                )
                break
        return next(
            item
            for item in runtime.state_snapshot()["counters"]
            if item["counter_id"] == counter_id
        )


@app.get("/api/state")
def get_state(
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return runtime.state_snapshot()


@app.post("/api/tokens/book")
def book_token(request: BookRequest) -> dict[str, object]:
    with runtime.lock:
        service_id = request.service_id.strip()
        customer_name = _clean_required_name(request.customer_name, "Patient name")
        if service_id not in runtime.services:
            raise HTTPException(status_code=404, detail="Unknown service_id")

        highest = 100
        for token in runtime.array.traverse():
            token_id = str(token["token_id"])
            if token_id.startswith("Q"):
                try:
                    highest = max(highest, int(token_id[1:]))
                except ValueError:
                    continue
        token_id = f"Q{highest + 1}"
        if highest >= 999:
            raise HTTPException(status_code=409, detail="Token range Q101-Q999 exhausted")

        now = datetime.now(timezone.utc)
        recommendation = runtime._recommend_counter(service_id)
        token: dict[str, object] = {
            "token_id": token_id,
            "customer_name": customer_name,
            "service_id": service_id,
            "priority_level": "STANDARD",
            "status": "S3_WAITING",
            "counter_id": recommendation["counter_id"],
            "assigned_path": recommendation["optimal_path"],
            "eta_min": recommendation["estimated_wait_min"],
            "arrival_timestamp": now.isoformat(),
            "updated_at": now.isoformat(),
            "service_started_at": None,
            "completed_at": None,
        }
        runtime._persist_token(token)
        runtime._insert_runtime_token(token)
        return {
            "token": token,
            "recommendation": recommendation,
        }


@app.get("/api/tokens/{token_id}")
def get_token(token_id: str) -> dict[str, object]:
    with runtime.lock:
        token = runtime.bst.search(token_id)
        if token is None:
            raise HTTPException(status_code=404, detail="Token not found")
        public_token = dict(token)
        is_completed = token["status"] == "S6_COMPLETED"
        eta_min = (
            float(token["eta_min"])
            if token["status"] == "S3_WAITING"
            else None
        )
        optimal_path = [] if is_completed else list(token["assigned_path"])
        public_token["eta_min"] = eta_min
        if is_completed:
            public_token["assigned_path"] = []
        return {
            "token": public_token,
            "optimal_path": optimal_path,
            "eta_min": eta_min,
        }


@app.post("/api/counters/{counter_id}/next")
def call_next(
    counter_id: str,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        try:
            token = runtime.call_next(counter_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown counter") from exc
        return {"token": token}


@app.post("/api/counters/{counter_id}/start")
def start_service(
    counter_id: str,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return {"token": runtime.start_service(counter_id)}


@app.post("/api/counters/{counter_id}/complete")
def complete_service(
    counter_id: str,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return {"token": runtime.complete_service(counter_id)}


@app.post("/api/ai/search")
def ai_search(
    request: SearchRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return runtime.search(request)


@app.post("/api/ai/compare")
def compare_search(
    request: SearchRequest,
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return runtime.compare_search(request)


@app.get("/api/ds/inspect")
def inspect_data_structures(
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return runtime.ds_snapshot()


def _playground_for_user(user: dict[str, object]) -> DataStructurePlayground:
    user_id = int(user["id"])
    playground = runtime.ds_playgrounds.get(user_id)
    if playground is None:
        playground = DataStructurePlayground()
        runtime.ds_playgrounds[user_id] = playground
    return playground


def _run_playground_operation(
    user: dict[str, object],
    operation: Callable[[DataStructurePlayground], dict[str, object]],
) -> dict[str, object]:
    with runtime.lock:
        playground = _playground_for_user(user)
        try:
            return operation(playground)
        except DuplicateStructureItem as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
        except IndexError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/ds/playground")
def get_ds_playground(
    user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        return _playground_for_user(user).snapshot()


@app.post("/api/ds/playground/array")
def operate_array_playground(
    request: ArrayOperationRequest,
    user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    return _run_playground_operation(
        user,
        lambda playground: playground.array_operation(
            request.operation,
            request.value,
            request.index,
        ),
    )


@app.post("/api/ds/playground/linked-list")
def operate_linked_list_playground(
    request: LinkedListOperationRequest,
    user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    return _run_playground_operation(
        user,
        lambda playground: playground.linked_list_operation(
            request.operation,
            request.value,
            request.position,
            request.item_id,
        ),
    )


@app.post("/api/ds/playground/priority-queue")
def operate_priority_queue_playground(
    request: PriorityQueueOperationRequest,
    user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    return _run_playground_operation(
        user,
        lambda playground: playground.priority_queue_operation(
            request.operation,
            request.value,
            request.priority,
            request.item_id,
        ),
    )


@app.post("/api/ds/playground/bst")
def operate_bst_playground(
    request: BSTOperationRequest,
    user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    return _run_playground_operation(
        user,
        lambda playground: playground.bst_operation(
            request.operation,
            request.key,
            request.value,
        ),
    )


@app.get("/api/reports/summary")
def reports_summary(
    _user: dict[str, object] = Depends(require_roles("STAFF", "ADMIN")),
) -> dict[str, object]:
    with runtime.lock:
        tokens = list(runtime.array.traverse())
        wait_summary = _waiting_time_summary(tokens)
        statuses = {
            "waiting": sum(token["status"] in ("S3_WAITING", "S4_COUNTER_ASSIGNED") for token in tokens),
            "in_progress": sum(token["status"] == "S5_IN_PROGRESS" for token in tokens),
            "completed": sum(token["status"] == "S6_COMPLETED" for token in tokens),
        }
        total = len(tokens)
        active_counters = sum(status == "OPEN" for status in runtime.counter_status.values())
        busy_counters = sum(
            token is not None and token["status"] == "S5_IN_PROGRESS"
            for token in runtime.current_by_counter.values()
        )
        counter_reports = []
        for counter_id, status in runtime.counter_status.items():
            completed_count = sum(
                token["counter_id"] == counter_id and token["status"] == "S6_COMPLETED"
                for token in tokens
            )
            current = runtime.current_by_counter[counter_id]
            queue_length = runtime.counter_lists[counter_id].length
            counter_reports.append(
                {
                    "counter_id": counter_id,
                    "name": runtime.counter_names[counter_id],
                    "status": status,
                    "waiting_count": queue_length,
                    "in_progress_count": int(current is not None and current["status"] == "S5_IN_PROGRESS"),
                    "completed_count": completed_count,
                    "utilization_pct": 100 if current is not None and status == "OPEN" else 0,
                }
            )
        return {
            "total_appointments": total,
            "waiting_count": statuses["waiting"],
            "in_progress_count": statuses["in_progress"],
            "completed_count": statuses["completed"],
            **wait_summary,
            "open_counters": active_counters,
            "busy_counters": busy_counters,
            "utilization_pct": round(busy_counters / active_counters * 100, 2) if active_counters else 0.0,
            "counters": counter_reports,
        }
