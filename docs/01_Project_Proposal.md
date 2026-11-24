# QueueLess AI - Project Proposal

**Intelligent Appointment, Queue & Service Optimization Platform**

## 1. Executive Summary

QueueLess AI is an appointment, token, and service-routing platform for diagnostic laboratory environments. The project addresses the operational gap between fixed appointment schedules and unpredictable walk-in demand by maintaining a persistent queue, assigning customers to three parallel counters, and recording their progress through laboratory stages.

The Version 1.0 implementation provides a simulated three-counter laboratory. Customers can book appointments and receive tokens from `Q101` through `Q999`; counter staff can start, hold, resume, transfer, or complete service; and administrators can view utilization and queue analytics. Custom queue and heap implementations provide the principal data-structure operations. Breadth-first search (BFS), uniform-cost search (UCS), and $A^*$ provide route selection over a laboratory workflow graph. SQLite provides restart-safe state recovery.

The project follows the finalized team division: Anushka Samad leads AI and arrays while coordinating UI/UX and the project; Ubaid Raza leads UCS, $A^*$, backend development, and the remaining data structures; Laiba Khan completes the small diagnostic-service sample-data task; and Danyal Hassan provides supporting testing, screenshots, feedback, and contribution maintenance. The resulting system serves as an academic implementation of Applied Artificial Intelligence and Data Structures, with controlled laboratory simulation rather than a production medical deployment.

## 2. Real-World Problem Statement

Walk-in diagnostic laboratories encounter the following recurring bottlenecks:

1. **Unstructured customer arrival:** Walk-in customers join informal lines or approach multiple counters, producing duplicate requests and no authoritative waiting order.
2. **Counter imbalance:** Staff assign new customers using local judgment, leaving one counter overloaded while another has limited work.
3. **Opaque waiting estimates:** Customers cannot determine when they are likely to be served, and staff cannot explain expected delay from a consistent queue model.
4. **Interrupted stage transitions:** A customer may wait for registration, specimen collection, testing, or report preparation without a tracked stage state. Missed handoffs delay completion and obscure current responsibility.
5. **Limited operational evidence:** Manual registers do not reliably record arrival time, counter idle time, queue length, transfer count, or completion time. Managers therefore cannot diagnose recurring delays with quantitative data.

These bottlenecks increase waiting time, create disputes over queue priority, and make service outcomes dependent on individual staff decisions rather than an auditable system policy.

## 3. Proposed Solution and Core Objectives

QueueLess AI provides one queue authority for the simulated laboratory. It records each token, appointment, counter assignment, stage transition, and completion event. Route selection is based on the laboratory workflow graph, while counter assignment uses waiting priority and capacity information.

### Core Objectives

- Replace informal queues with deterministic token-based service.
- Generate every active token inside the inclusive `Q101`-`Q999` range.
- Operate three parallel counters while retaining a single view of demand.
- Implement and verify custom priority queue, queue, and graph data structures.
- Compare BFS, UCS, and $A^*$ for laboratory workflow routing.
- Apply an admissible $A^*$ heuristic and show its correctness through tests.
- Preserve queue state across process restarts using SQLite transactions.
- Give customers, staff, and administrators role-specific information and permissions.
- Produce measurable waiting, throughput, and counter-utilization analytics.

## 4. Scope and Non-Goals

### In Scope for Version 1.0

- Simulated diagnostic laboratory with exactly three service counters
- Customer appointment booking and token lookup
- Walk-in token generation and slot-based appointment handling
- Laboratory stages for arrival, registration, service, report preparation, and completion
- Counter staff stage transitions and counter transfer
- BFS, UCS, and $A^*$ workflow routing
- Administrator queue and counter analytics
- SQLite persistence and restart recovery
- Local React, FastAPI, and SQLite deployment

### Explicit Non-Goals

- Clinical diagnosis or automated treatment recommendation
- Electronic health-record integration
- Payment processing or insurance verification
- Real-time hardware counter control
- SMS, email, or push notification delivery in the base release
- Multi-laboratory or multi-site routing
- Production medical certification or regulatory approval
- Replacement of qualified laboratory personnel

Version 1.0 is an academic and technical simulation. The future FYP scope may extend the platform to additional counters and laboratories, external notifications, live operational integrations, forecasting models, and secure role federation. These extensions require separate requirements and validation.

## 5. Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Backend language | Python 3.11+ | API, services, algorithms, persistence |
| Web API | FastAPI | Request validation and HTTP endpoints |
| Database | SQLite | Transactions and durable local state |
| Frontend | React | Role-specific user interfaces |
| Build tool | Vite | Development and production frontend builds |
| Styling | Tailwind CSS | Responsive and accessible presentation |

## 6. Five-Phase Development Roadmap

| Phase | Duration | Principal Work | Exit Criteria |
|---|---|---|---|
| 1. Requirements and Design | 1 week | Confirm roles, workflows, data model, and API contracts | Approved SRS, design, and task breakdown |
| 2. Core Backend and Data Structures | 2 weeks | Implement token service, custom queue/heap/graph, SQLite repositories | Deterministic tests pass for queue and token operations |
| 3. AI Routing and Fairness | 1 week | Implement BFS, UCS, $A^*$, aging, and counter assignment | Route-cost and admissible-heuristic tests pass |
| 4. Frontend and Integration | 2 weeks | Build React customer, staff, and administrator views; connect API | End-to-end scenarios pass across all roles |
| 5. Verification and Reporting | 1 week | Run functional and NFR tests, accessibility checks, and performance measurement | Test report, setup instructions, and final project report are complete |

## 7. Detailed Member Responsibility Matrix

The percentages below apply to the two technical subjects only. Anushka and Ubaid each own 50% of Artificial Intelligence and 50% of Data Structures. Laiba's and Danyal's assignments are intentionally limited to the supporting tasks stated below; they do not own coding, backend, or AI-algorithm implementation.

| Member | Finalized Role | Artificial Intelligence (50%) | Data Structures (50%) | Additional Responsibility |
|---|---|---|---|---|---|
| Anushka Samad - CSC-25F-083 | AI Lead | Problem formulation; state-space representation; initial state, goal state, and actions; graph creation; dictionary creation; BFS implementation; graph visualization; AI documentation | Array implementation; array operations; array integration with QueueLess | UI/UX decisions and overall project coordination |
| Ubaid Raza - CSC-25F-013 | DS & Search Lead | UCS; $A^*$ search; path-cost calculation; heuristic function; search-algorithm integration | Linked-list implementation; priority-queue implementation; BST implementation; insertion, deletion, search, and traversal operations; data-structures integration | Backend development |
| Laiba Khan - CSC-25F-024 | Project Content & Sample Data Collection (small task) | Not assigned | Not assigned | List 5-10 diagnostic laboratory services; collect estimated service durations; suggest three service-counter names; no coding, backend, or AI algorithms |
| Danyal Hassan - CSC-25F-032 | Testing & Project Support (supporting) | Not assigned | Not assigned | Collect screenshots; prepare a basic testing checklist; test assigned features and report feedback; maintain GitHub contributions for completed work |

### Git and Co-Authoring Workflow

Each member records only actual completed work in GitHub. When Anushka or Ubaid assists with documentation or testing, the commit must include a `Co-authored-by` trailer for the assisting contributor using their verified GitHub noreply address. This records real assistance without assigning unperformed work.
