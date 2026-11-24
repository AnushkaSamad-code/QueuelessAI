# QueueLess AI — UML, Operational Flow, and Call Flow

## 1. Use Case Diagram

```mermaid
flowchart LR
    Customer[Customer]
    Staff[Counter Staff]
    Admin[Administrator]

    subgraph System[QueueLess AI]
        Book((Book appointment))
        Token((Generate token))
        Status((View queue status))
        CheckIn((Check in))
        Serve((Advance service stage))
        Transfer((Transfer or hold token))
        Analytics((View analytics))
        Configure((Configure service graph))
    end

    Customer --> Book
    Customer --> Token
    Customer --> Status
    Customer --> CheckIn
    Staff --> Book
    Staff --> Token
    Staff --> Status
    Staff --> CheckIn
    Staff --> Serve
    Staff --> Transfer
    Admin --> Book
    Admin --> Token
    Admin --> Status
    Admin --> Transfer
    Admin --> Analytics
    Admin --> Configure
```

Customers control their appointment and status interactions. Staff control operational transitions. Administrators control aggregate analysis and configuration.

## 2. Class Diagram

```mermaid
classDiagram
    class Token {
        +str token_id
        +str stage
        +str status
        +str counter_id
        +datetime arrival_timestamp
        +int base_priority
    }

    class Counter {
        +str counter_id
        +bool available
        +int queue_length
        +assign(Token) bool
        +release(Token) bool
    }

    class TokenArray {
        -TokenRecord[] storage
        -int size
        -int capacity
        +append(Token) int
        +get(int) Token
        +find_token(str) int
        +remove(int) Token
    }

    class ServiceLinkedList {
        -Node head
        -Node tail
        -int size
        +append(Token) void
        +pop_front() Token
        +remove(str) Token
        +find(str) Token
    }

    class SchedulingPriorityQueue {
        -HeapNode[] heap
        -int aging_interval_minutes
        +insert(Token) void
        +extract_min() Token
        +refresh_aging(datetime) void
    }

    class TokenBST {
        -BSTNode root
        +insert(Token) void
        +search(str) Token
        +delete(str) Token
        +inorder() Token[]
        +preorder() Token[]
        +postorder() Token[]
    }

    class ServiceGraph {
        +add_node(str) void
        +add_edge(str, str, float) void
        +neighbors(str) Edge[]
        +recalculate_weights() void
    }

    class SearchEngine {
        +bfs(ServiceGraph, str, str) Route
        +ucs(ServiceGraph, str, str) Route
        +a_star(ServiceGraph, str, str) Route
        +heuristic(str) float
    }

    TokenArray "1" o-- "*" Token : stores
    Counter "1" o-- "1" ServiceLinkedList : owns queue
    ServiceLinkedList "1" o-- "*" Token : orders
    SchedulingPriorityQueue "1" o-- "*" Token : schedules
    TokenBST "1" o-- "*" Token : indexes
    SearchEngine --> ServiceGraph : searches
    Counter --> Token : assigns
```

The classes expose abstract operations rather than their internal storage. `SearchEngine` consumes a graph snapshot and returns a route; it does not mutate the data structures.

## 3. System Operational Flowchart

```mermaid
flowchart TD
    Start([Customer starts]) --> Book[Submit appointment]
    Book --> Validate{Request valid?}
    Validate -- No --> Reject[Return validation error]
    Validate -- Yes --> Generate[Generate Q101-Q999 token]
    Generate --> Store[Store in TokenArray and TokenBST]
    Store --> Schedule[Insert into SchedulingPriorityQueue]
    Schedule --> Graph[Build counter-aware graph]
    Graph --> Route[A* selects least-cost counter route]
    Route --> Queue[Append to counter ServiceLinkedList]
    Queue --> Staff[Staff dequeues next token]
    Staff --> Registration[Registration]
    Registration --> Sample[Sample Collection]
    Sample --> Report[Report Collection]
    Report --> Complete[Service Completion S6]
    Complete --> History[Append completed record to history list]
    History --> Audit[Write audit event to SQLite]
    Audit --> End([Customer served])
```

The rejection branch terminates before any active token or queue structure is mutated.

## 4. End-to-End Call Flow

```mermaid
sequenceDiagram
    actor Customer
    participant API as FastAPI
    participant Array as TokenArray
    participant BST as TokenBST
    participant Heap as SchedulingPriorityQueue
    participant AI as A* Search
    participant Staff as Counter Staff
    participant List as ServiceLinkedList
    participant DB as SQLite

    Customer->>API: POST /api/v1/appointments
    API->>DB: Insert appointment transaction
    DB-->>API: Appointment reference
    Customer->>API: POST /api/v1/tokens
    API->>Array: append(Q101)
    API->>BST: insert(Q101)
    API->>Heap: insert(Q101, priority, arrival_time)
    API->>DB: Persist token and audit event
    API-->>Customer: Q101 confirmation
    API->>AI: Search waiting_queue to service_completion
    AI-->>API: Counter 3 route and cost
    API->>List: append(Q101) to Counter 3
    API->>DB: Persist assignment
    Staff->>API: POST /tokens/Q101/transition
    API->>List: pop_front()
    API->>Array: update status to S5(c3)
    API->>DB: Record stage event
    Staff->>API: Complete report collection
    API->>Array: update status to S6
    API->>List: append(Q101) to completed history
    API->>DB: Record completion and audit event
    API-->>Staff: Completion confirmed
```

The API is the transaction boundary: in-memory updates and the corresponding SQLite event must either both succeed or both be rolled back.
