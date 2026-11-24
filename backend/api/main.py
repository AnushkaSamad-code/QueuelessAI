"""QueueLess AI FastAPI application with SQLite and in-memory structures."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.ds.custom_array import TokenArray
    from backend.ds.linked_list import ServiceLinkedList
    from backend.ds.priority_queue import ScheduledToken, SchedulingPriorityQueue
    from backend.ds.bst import TokenBST
    from backend.ai.graph_model import ServiceStateGraph
    from backend.ai.bfs import breadth_first_search
    from backend.ai.ucs import uniform_cost_search
    from backend.ai.astar import a_star_search
except ImportError:
    BACKEND_ROOT = Path(__file__).resolve().parents[1]
    if str(BACKEND_ROOT.parent) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT.parent))
    from backend.ds.custom_array import TokenArray
    from backend.ds.linked_list import ServiceLinkedList
    from backend.ds.priority_queue import ScheduledToken, SchedulingPriorityQueue
    from backend.ds.bst import TokenBST
    from backend.ai.graph_model import ServiceStateGraph
    from backend.ai.bfs import breadth_first_search
    from backend.ai.ucs import uniform_cost_search
    from backend.ai.astar import a_star_search


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
SEED_PATH = DATA_DIR / "diagnostic_lab_seed.json"
DB_PATH = DATA_DIR / "queueless.db"


class BookRequest(BaseModel):
    customer_name: str = Field(min_length=1)
    service_id: str
    priority_level: Literal["STANDARD", "APPOINTMENT", "PRIORITY"] = "STANDARD"
    arrival_offset_min: int = Field(default=0, ge=0)


class SearchRequest(BaseModel):
    algorithm: Literal["BFS", "UCS", "A*"] = "A*"
    start_state: str = "waiting_queue"
    goal_state: str = "service_completion"


class QueueLessState:
    """Owns SQLite and all live QueueLess runtime structures."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
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
        self.array = TokenArray[dict[str, object]](capacity=16, maximum_capacity=999)
        self.bst = TokenBST[dict[str, object]]()
        self.priority_queue = SchedulingPriorityQueue[dict[str, object]]()
        self.counter_lists = {
            "C1": ServiceLinkedList[dict[str, object]](),
            "C2": ServiceLinkedList[dict[str, object]](),
            "C3": ServiceLinkedList[dict[str, object]](),
        }
        self.service_graph = ServiceStateGraph(
            queue_wait={"counter_1": 15.0, "counter_2": 12.0, "counter_3": 10.0},
            transition_overhead=1.0,
        )
        self._initialize_database()
        self._hydrate_seeded_state()

    def _connect(self) -> sqlite3.Connection:
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
                    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED'))
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
                """
            )
            for counter in self.seed["counters"]:
                connection.execute(
                    """
                    INSERT INTO counters(counter_id, counter_name, status)
                    VALUES (?, ?, ?)
                    ON CONFLICT(counter_id) DO UPDATE SET
                        counter_name=excluded.counter_name,
                        status=excluded.status
                    """,
                    (counter["counter_id"], counter["name"], counter["status"]),
                )
            for service in self.seed["services"]:
                connection.execute(
                    """
                    INSERT INTO services(
                        service_id, name, category, required_stages, estimated_durations
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(service_id) DO UPDATE SET
                        name=excluded.name,
                        category=excluded.category,
                        required_stages=excluded.required_stages,
                        estimated_durations=excluded.estimated_durations
                    """,
                    (
                        service["service_id"],
                        service["name"],
                        service["category"],
                        json.dumps(service["required_stages"]),
                        json.dumps(service["estimated_durations_min"]),
                    ),
                )

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
            base_priority = self._base_priority(seed_token["priority_level"])
            recommendation = self._recommend_counter(seed_token["service_id"])
            token = {
                "token_id": seed_token["token_id"],
                "customer_name": seed_token["customer_name"],
                "service_id": seed_token["service_id"],
                "priority_level": seed_token["priority_level"],
                "status": "S4_COUNTER_ASSIGNED",
                "counter_id": recommendation["counter_id"],
                "assigned_path": recommendation["optimal_path"],
                "eta_min": recommendation["total_cost"],
                "arrival_timestamp": arrival.isoformat(),
                "updated_at": now.isoformat(),
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
        if token["status"] in ("S3_WAITING", "S4_COUNTER_ASSIGNED"):
            self.priority_queue.enqueue(
                token,
                str(token["token_id"]),
                priority,
                arrival,
            )
        counter_id = str(token["counter_id"])
        if counter_id in self.counter_lists and token["status"] in (
            "S3_WAITING",
            "S4_COUNTER_ASSIGNED",
            "S5_IN_PROGRESS",
        ):
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
        self.priority_queue.enqueue(
            token,
            str(token["token_id"]),
            self._base_priority(str(token["priority_level"])),
            arrival,
        )
        counter_id = str(token["counter_id"])
        self.counter_lists[counter_id].insert_tail(token)

    def _persist_token(self, token: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tokens(
                    token_id, customer_name, service_id, priority_level,
                    status, counter_id, assigned_path, eta_min,
                    arrival_timestamp, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_id) DO UPDATE SET
                    customer_name=excluded.customer_name,
                    service_id=excluded.service_id,
                    priority_level=excluded.priority_level,
                    status=excluded.status,
                    counter_id=excluded.counter_id,
                    assigned_path=excluded.assigned_path,
                    eta_min=excluded.eta_min,
                    arrival_timestamp=excluded.arrival_timestamp,
                    updated_at=excluded.updated_at
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
                ),
            )

    @staticmethod
    def _base_priority(priority_level: str) -> int:
        return {"STANDARD": 2, "APPOINTMENT": 1, "PRIORITY": 0}[priority_level]

    def _recommend_counter(self, service_id: str) -> dict[str, object]:
        queue_wait = {}
        for code, counter_name in (("C1", "counter_1"), ("C2", "counter_2"), ("C3", "counter_3")):
            queue_wait[counter_name] = self.counter_lists[code].length
        available = [
            "counter_1" if self.counter_status["C1"] == "OPEN" else "",
            "counter_2" if self.counter_status["C2"] == "OPEN" else "",
            "counter_3" if self.counter_status["C3"] == "OPEN" else "",
        ]
        available = [counter for counter in available if counter]
        if not available:
            raise HTTPException(status_code=409, detail="No counter is open")
        graph = ServiceStateGraph(
            queue_wait={
                counter: float(queue_wait[counter])
                for counter in available
            },
            transition_overhead=1.0,
            available_counters=available,
        )
        self.service_graph = graph
        result = a_star_search(graph, "waiting_queue", "service_completion")
        path = result["optimal_path"]
        counter_internal = next(
            (
                node.split(".", 1)[0]
                for node in path
                if "." in node
            ),
            None,
        )
        counter_id = {
            "counter_1": "C1",
            "counter_2": "C2",
            "counter_3": "C3",
        }.get(str(counter_internal), "C1")
        return {
            "counter_id": counter_id,
            "optimal_path": path,
            "total_cost": result["total_cost"] or 0.0,
        }

    def next_token(self, counter_id: str) -> dict[str, object]:
        if counter_id not in self.counter_lists:
            raise KeyError(counter_id)
        if self.counter_status[counter_id] != "OPEN":
            raise HTTPException(status_code=409, detail=f"{counter_id} is closed")

        for token in self.counter_lists[counter_id].traverse():
            if token["status"] == "S5_IN_PROGRESS":
                token["status"] = "S6_COMPLETED"
                token["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._persist_token(token)
                self.counter_lists[counter_id].delete_by_token_id(str(token["token_id"]))
                return token

        if self.counter_lists[counter_id].length == 0:
            raise HTTPException(status_code=404, detail="No token waiting at this counter")
        token = self.counter_lists[counter_id].pop_front()
        token["status"] = "S5_IN_PROGRESS"
        token["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self.priority_queue.remove(str(token["token_id"]))
        except KeyError:
            pass
        self._persist_token(token)
        return token

    def search(self, request: SearchRequest) -> dict[str, object]:
        if request.algorithm == "BFS":
            result = breadth_first_search(
                self.service_graph,
                request.start_state,
                request.goal_state,
            )
        elif request.algorithm == "UCS":
            result = uniform_cost_search(
                self.service_graph,
                request.start_state,
                request.goal_state,
            )
        else:
            result = a_star_search(
                self.service_graph,
                request.start_state,
                request.goal_state,
            )
        if hasattr(result, "get"):
            payload = dict(result)
        else:
            payload = dict(result)
        token_id = "VISUALIZER"
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
        payload["graph"] = self.service_graph.export_visualization()
        payload["algorithm"] = request.algorithm
        return payload

    def state_snapshot(self) -> dict[str, object]:
        active = [
            token
            for token in self.array.traverse()
            if token["status"] != "S6_COMPLETED"
        ]
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
                "priority_queue_size": self.priority_queue.size,
            },
        }

    def ds_snapshot(self) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        return {
            "token_array": self.array.to_dict(),
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


@app.get("/api/state")
def get_state() -> dict[str, object]:
    with runtime.lock:
        return runtime.state_snapshot()


@app.post("/api/tokens/book")
def book_token(request: BookRequest) -> dict[str, object]:
    with runtime.lock:
        if request.service_id not in runtime.services:
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
        arrival = now - timedelta(minutes=request.arrival_offset_min)
        recommendation = runtime._recommend_counter(request.service_id)
        token: dict[str, object] = {
            "token_id": token_id,
            "customer_name": request.customer_name,
            "service_id": request.service_id,
            "priority_level": request.priority_level,
            "status": "S4_COUNTER_ASSIGNED",
            "counter_id": recommendation["counter_id"],
            "assigned_path": recommendation["optimal_path"],
            "eta_min": recommendation["total_cost"],
            "arrival_timestamp": arrival.isoformat(),
            "updated_at": now.isoformat(),
        }
        runtime._insert_runtime_token(token)
        runtime._persist_token(token)
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
        return {
            "token": token,
            "optimal_path": token["assigned_path"],
            "eta_min": token["eta_min"],
        }


@app.post("/api/counters/{counter_id}/next")
def call_next(counter_id: str) -> dict[str, object]:
    with runtime.lock:
        try:
            token = runtime.next_token(counter_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown counter") from exc
        return {"token": token}


@app.post("/api/ai/search")
def ai_search(request: SearchRequest) -> dict[str, object]:
    with runtime.lock:
        return runtime.search(request)


@app.get("/api/ds/inspect")
def inspect_data_structures() -> dict[str, object]:
    with runtime.lock:
        return runtime.ds_snapshot()
