# QueueLess AI - Software Requirements Specification

**Intelligent Appointment, Queue & Service Optimization Platform**

## 1. Purpose

This document specifies the functional and non-functional requirements for QueueLess AI Version 1.0. Version 1.0 implements a simulated diagnostic laboratory with three parallel service counters. Each requirement is traceable to implementation work and acceptance evidence.

## 2. System Users and Role Permissions

| Capability | Customer | Counter Staff | Administrator |
|---|---|---|---|
| Create appointment | Allowed | Allowed on behalf of customer | Allowed |
| View own appointment and token | Allowed | Allowed for listed customer | Allowed |
| Generate walk-in token | Allowed | Allowed | Allowed |
| View public queue status | Allowed | Allowed | Allowed |
| View assigned counter queue | Not allowed | Allowed for assigned or selected counter | Allowed |
| Advance a service stage | Not allowed | Allowed within assigned counter | Not allowed |
| Transfer a token to another counter | Not allowed | Allowed with staff authorization | Allowed |
| Hold or resume a token | Not allowed | Allowed for assigned counter | Allowed |
| Configure laboratory stages or graph | Not allowed | Not allowed | Allowed |
| View aggregate analytics | Not allowed | Limited to operational counter view | Allowed |
| Manage staff accounts and permissions | Not allowed | Not allowed | Allowed |
| Modify historical records | Not allowed | Not allowed | Not allowed |

API routes that create or change service state require authenticated role permissions. Public queue lookup may expose only token state and estimated information.

## 3. Finalized Module Ownership and Workflow

The implementation workflow assigns the AI and Data Structures modules as follows:

- **Anushka Samad (CSC-25F-083), AI Lead:** owns problem formulation, state-space representation, initial state/goal state/actions, graph and dictionary creation, BFS, graph visualization, AI documentation, array implementation and operations, and array integration with QueueLess. Anushka also makes UI/UX decisions and coordinates the project overall.
- **Ubaid Raza (CSC-25F-013), DS & Search Lead:** owns UCS, $A^*$, path-cost calculation, the heuristic function, search-algorithm integration, linked lists, priority queues, BSTs, insertion/deletion/search/traversal operations, data-structures integration, and backend development.
- **Laiba Khan (CSC-25F-024), Project Content & Sample Data Collection (small task):** prepares 5–10 diagnostic laboratory services, estimated service durations, and 3 service-counter names. Laiba has no coding, backend, or AI-algorithm assignment.
- **Danyal Hassan (CSC-25F-032), Testing & Project Support (supporting):** collects screenshots, prepares a basic testing checklist, tests assigned features, reports feedback, and maintains GitHub contributions for completed work.

Anushka and Ubaid each own 50% of Artificial Intelligence and 50% of Data Structures. These ownership assignments do not alter the functional or non-functional requirements below.

### Git and Co-Authoring Workflow

GitHub history shall represent actual completed work. When Anushka or Ubaid materially assists with documentation or testing, the commit author shall add a `Co-authored-by` trailer for the assisting contributor using the contributor's verified GitHub noreply address. No commit shall claim work that was not performed.

## 4. Functional Requirements

### FR-01: Customer Appointment Booking

The system shall accept a customer name, selected service, preferred date, and time slot. It shall reject past dates, closed service periods, duplicate active appointments for the same customer and slot, and invalid service identifiers. A successful booking shall create a unique appointment record and return an appointment reference.

### FR-02: Appointment Confirmation

The system shall return the customer-visible service, date, time slot, appointment reference, and current appointment state. The API shall expose only those customer data fields necessary for lookup and check-in.

### FR-03: Walk-In Token Generation

The system shall generate a token in the inclusive range `Q101`-`Q999`. Each token shall be unique among active and retained records that share the configured database lifetime. The token generator shall not reuse a token while another active record holds it.

### FR-04: Appointment Check-In

The customer or staff shall check in an existing appointment using the appointment reference and verified customer identity. Check-in shall create or associate the appointment with a valid queue token and set the service state to waiting.

### FR-05: Custom Queue Operations

The system shall provide enqueue, dequeue, peek, remove, and size operations through a custom queue implementation. Queue operations shall preserve FIFO order for equal priority and shall report unsuccessful removal without corrupting state.

### FR-06: Custom Priority Queue Operations

The system shall provide insert, extract-minimum or extract-highest-priority, peek, update-priority, and size operations through a custom heap-backed priority queue. Priority shall account for scheduled appointment priority and configured aging. Core priority operations shall not rely on an external priority-queue library.

### FR-07: Laboratory Workflow Graph

The system shall represent laboratory stages and permitted transitions as a directed weighted graph. Version 1.0 shall include arrival, registration, service, report preparation, and completion stages. Invalid transitions and disconnected routes shall be rejected or reported.

### FR-08: Breadth-First Search Routing

The system shall implement BFS for minimum-hop routing from a current laboratory stage to a requested destination. If multiple routes have equal hop count, the system shall use deterministic graph insertion order. BFS shall not consider weighted edge cost when selecting minimum-hop routes.

### FR-09: Uniform-Cost Search Routing

The system shall implement UCS using non-negative edge weights. UCS shall return a least cumulative-cost route and shall report no route when the destination is unreachable. Route and cost shall be reproducible for fixed graph and tie-breaking inputs.

### FR-10: $A^*$ Routing

The system shall implement $A^*$ with $h(n)$ equal to or lower than the true remaining cost to the destination. The system shall provide the chosen route, total cost, and expanded node count. The implementation shall reject or report invalid weighted graphs containing negative edges.

### FR-11: Three-Counter Assignment

The system shall maintain exactly three counters identified as Counter 1, Counter 2, and Counter 3. Assignment shall select an available counter and account for queue length, estimated service time, and waiting-time priority. No counter shall receive an additional active token while it is marked unavailable or while a configured capacity limit is exceeded.

### FR-12: Staff Stage Transitions

Counter staff shall initiate a service-stage transition only for a token assigned to an authorized counter. Valid transitions shall include waiting to in-service, in-service to held, held to in-service, in-service to counter transfer, and in-service to completed. The system shall validate state transitions and append an immutable stage-event record.

### FR-13: Transfer and Hold Operations

Staff shall transfer a held or active token to an available counter only after removing it from the source counter's active state. The system shall move it atomically and retain a transfer event. Staff shall not transfer a completed or cancelled token.

### FR-14: Administrator Analytics

The administrator shall retrieve aggregate measurements for active queue length, completed token count, average waiting time, average service time, counter throughput, counter utilization, transfer count, and abandonment or cancellation count. Analytics shall support a selectable date range and shall not expose customer-identifying fields in exported aggregate data.

## 5. Non-Functional Requirements

### NFR-01: Queue Decision Latency

The API shall return queue assignment, token lookup, and stage-transition decisions within $150\text{ ms}$ at the 95th percentile under 100 concurrent read/write operations and a populated test queue of at least 1,000 active or retained records. Measurement shall exclude client network and browser rendering time.

### NFR-02: $A^*$ Heuristic Admissibility

The implemented $A^*$ heuristic shall be admissible for every graph in the test suite: $h(n) \le h^*(n)$, where $h^*(n)$ is the true least remaining cost from node $n$ to the destination. The test suite shall include disconnected routes, single-node routes, cycles, and at least three route-cost alternatives. Consistency shall be tested for heuristic-bearing laboratory graphs.

### NFR-03: Starvation-Free Aging Fairness

The priority policy shall ensure that any waiting token receives a strictly higher effective priority as its wait time increases. This aging mechanism shall prevent indefinitely unchanged priority ordering and shall be proven by a bounded-wait test. The test shall demonstrate that a maximum-priority token that remains ready will be selected within a configured upper bound under a continuously populated queue.

### NFR-04: SQLite State Recovery

The system shall treat SQLite transactions as the source of truth and shall preserve token, assignment, stage, and event state across normal backend restarts. Initialization shall validate schema version and required constraints. Interrupted transactions shall not leave a token in two active counter states. Recovery tests shall verify state after process termination during booking, assignment, transfer, and completion operations.

### NFR-05: WCAG AA Accessibility

The customer, staff, and administrator interfaces shall conform to WCAG 2.1 AA success criteria applicable to the implemented controls. Text and essential status indicators shall meet contrast requirements; all operations shall be available from the keyboard; focused controls shall have a visible indicator; status changes shall be announced through appropriate live regions; and responsive layouts shall remain usable without horizontal scrolling at 320 CSS pixels and above.
