# QueueLess AI - Project Proposal

**Intelligent Appointment, Queue & Service Optimization Platform**

## 1. Executive Summary

QueueLess AI is an appointment, token, and service-routing platform for diagnostic laboratory environments. The project addresses the operational gap between fixed appointment schedules and unpredictable walk-in demand by maintaining a persistent queue, assigning customers to three parallel counters, and recording their progress through laboratory stages.

The Version 1.0 implementation provides a simulated three-counter laboratory. Customers can book appointments and receive tokens from `Q101` through `Q999`; counter staff can start, hold, resume, transfer, or complete service; and administrators can view utilization and queue analytics. Custom queue and heap implementations provide the principal data-structure operations. Breadth-first search (BFS), uniform-cost search (UCS), and $A^*$ provide route selection over a laboratory workflow graph. SQLite provides restart-safe state recovery.

The project is divided across backend services, data structures, AI routing, the React interface, integration, and verification. The resulting system serves as an academic implementation of Applied Artificial Intelligence and Data Structures, with controlled laboratory simulation rather than a production medical deployment.

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

| Member | Backend | Data Structures | AI | Frontend | Testing and Documentation |
|---|---|---|---|---|---|
| Anushka Samad - CSC-25F-083 | FastAPI routes, service orchestration, integration | Queue API integration | Workflow policy coordination | Staff API integration | Project coordination, SRS, final report |
| Ubaid Raza - CSC-25F-013 | Routing service interfaces | Graph representation and edge costs | BFS, UCS, $A^*$ implementation and admissibility tests | Routing visualization data | Algorithm test cases and technical report sections |
| Laiba Khan - CSC-25F-024 | Frontend API contracts | - | Customer-facing wait and route status display | React views, Tailwind layout, keyboard and WCAG AA checks | UI test plan and user manual |
| Danyal Hassan - CSC-25F-032 | SQLite repositories and transactions | Custom queue, heap, and priority operations | Fairness and aging input structures | Service-state data handling | Unit tests, recovery tests, latency measurement |

All members participate in integration and final verification. No responsibility is complete until peer review and traceable tests have been performed.
