# QueueLess AI — Final Project Report

## Abstract

QueueLess AI is a simulated diagnostic-laboratory platform that combines appointment booking, tokenized queues, three parallel service counters, custom data structures, and graph-search algorithms. The system models a token from appointment through registration, sample collection, report collection, and service completion. A FastAPI gateway coordinates a React interface, SQLite persistence, a counter-aware service graph, and manually implemented `TokenArray`, `ServiceLinkedList`, `SchedulingPriorityQueue`, and `TokenBST` structures. BFS, UCS, and A* are implemented as distinct routing strategies. The design emphasizes deterministic state transitions, anti-starvation aging, admissible heuristic search, restart recovery, and role-specific operation.

## 1. Introduction

Walk-in diagnostic laboratories must coordinate variable arrival times, fixed service stages, and limited counter capacity. Informal queues provide weak ordering and little operational evidence. QueueLess AI addresses this problem as an applied Artificial Intelligence and Data Structures project rather than as a clinical decision system. Its Version 1.0 domain is a controlled laboratory simulation with exactly three service counters.

The project objectives are to provide a valid token workflow, compare search strategies on a weighted service graph, demonstrate manual data-structure implementation, preserve state in SQLite, and expose measurable queue and counter behavior to customers, staff, and administrators.

## 2. Literature and Background Context

The design draws on four established areas:

1. **Queueing and scheduling:** FIFO ordering is a useful baseline, while priority and aging policies address unequal urgency and starvation.
2. **Graph search:** BFS minimizes transitions in unweighted graphs; UCS minimizes non-negative cumulative cost; A* combines accumulated cost with a lower-bound heuristic.
3. **Abstract data types:** Arrays, linked lists, heaps, and binary search trees illustrate different access, insertion, deletion, and ordering trade-offs.
4. **Transaction-backed information systems:** SQLite transactions and audit events provide durable state and recoverable operational history.

QueueLess AI applies these concepts to a bounded service workflow. It does not claim that a simulated route is a medical recommendation or that a queue estimate replaces laboratory staff judgment.

## 3. System Design

The system has four tiers:

- **Presentation:** React, Vite, and Tailwind CSS portals for customers, staff, and administrators.
- **REST gateway:** FastAPI validation, authentication, role authorization, service orchestration, and JSON responses.
- **AI engine:** counter-aware graph construction, BFS, UCS, A*, heuristic calculation, and fairness policy.
- **Data and persistence:** four custom runtime structures, SQLite repositories, schema constraints, and audit logs.

The central state transition is:

$$
S_1\rightarrow S_2\rightarrow S_3\rightarrow S_4(c_i)
\rightarrow S_5(c_i)\rightarrow S_6.
$$

Service stages within \(S_5\) are ordered as Registration, Sample Collection, and Report Collection. All state-changing operations are validated at the gateway and persisted with an audit event.

## 4. Data Structures and AI Implementation Highlights

### Data Structures

- `TokenArray` provides contiguous active-token and counter records.
- `ServiceLinkedList` provides per-counter waiting queues and completed history.
- `SchedulingPriorityQueue` provides a binary min-heap ordered by effective priority and arrival timestamp. Every 15 minutes of waiting improves effective priority by one aging unit.
- `TokenBST` provides token identifier search and three traversals.

Core operations are manually implemented; built-in Python containers are not used as substitutes for these structures.

### AI Algorithms

The service graph uses non-negative weighted transitions. BFS provides a minimum-hop baseline. UCS returns the least cumulative-cost route. A* uses:

$$
f(n)=g(n)+h(n),
\qquad
h(n)=\sum_{k\in\text{remaining stages}}
\min_iD_{\text{service}}(k,c_i).
$$

The heuristic is admissible because every remaining stage must be serviced and the minimum duration is no greater than the duration at the selected counter. It is consistent when each edge cost includes the completed stage duration plus non-negative waiting and transition costs.

## 5. Comparative Performance Evaluation

### 5.1 Evaluation Protocol

The comparison uses identical seeded workloads for both policies:

1. Generate a fixed set of appointments and walk-ins.
2. Use the same three counters, service durations, arrival timestamps, and stage transitions.
3. Run FCFS with counter assignment based only on queue order.
4. Run AI-optimized routing with counter-aware weights and aging.
5. Record average wait time, counter utilization, utilization variance, nodes expanded, route cost, throughput, and completed-token count.
6. Repeat with increasing queue sizes and report median and p95 values.

### 5.2 Metrics

| Metric | Definition |
|---|---|
| Average wait time | \(\frac{1}{N}\sum_{j=1}^{N}(t_{\text{service},j}-t_{\text{arrival},j})\). |
| Counter utilization | Busy service minutes divided by available counter minutes. |
| Utilization variance | Population variance of the three counter utilization ratios. |
| Nodes expanded | Number of graph nodes removed from the search frontier before route completion. |
| Route cost | Sum of waiting, service, and transition costs on the selected route. |

### 5.3 Expected Comparative Behavior

| Measure | FCFS baseline | AI-optimized routing | Interpretation |
|---|---|---|---|
| Average wait time | Queue-order dependent | Uses duration, availability, and aging | AI should reduce avoidable delay when counters have unequal load or service times. |
| Counter utilization variance | Can be high when work is assigned sequentially | Assignment considers all available counters | Lower variance indicates better workload balance. |
| Nodes expanded | Not applicable to routing, or one fixed branch | Reported for BFS, UCS, and A* | A* should expand no more nodes than UCS on the same consistent heuristic in the tested graph, subject to tie-breaking. |
| Starvation risk | Low for strict FIFO but inflexible | Controlled by 15-minute aging | Aging preserves fairness while allowing cost-aware scheduling. |

No empirical timing or utilization value is asserted without an executed seeded benchmark. The release report must attach the raw pytest/benchmark output and environment details before presenting numeric claims.

## 6. Limitations

- Version 1.0 models one laboratory and exactly three counters.
- Service durations are estimates, not instrument telemetry.
- SQLite is suitable for the local academic deployment but not a demonstrated multi-site production database.
- The system does not diagnose illness, interpret specimens, issue medical advice, or integrate with an electronic health record.
- A* quality depends on the graph and heuristic assumptions; invalid or stale duration data can reduce decision quality.
- The current accessibility and performance requirements require execution evidence; documentation alone is not certification.

## 7. Future FYP Roadmap

1. Validate the model with anonymized operational data and domain-expert review.
2. Add multi-laboratory and variable-counter configuration without weakening state invariants.
3. Add notifications, appointment reminders, and customer consent controls.
4. Introduce forecasting for arrivals and service duration with transparent evaluation.
5. Add stronger authentication, role federation, encrypted deployment, and audit retention policy.
6. Evaluate PostgreSQL or a managed transactional store for concurrent deployments.
7. Conduct formal accessibility, load, security, and usability studies.

Each extension requires a revised SRS, migration plan, threat model, and regression suite.

## 8. Conclusion

QueueLess AI presents a complete academic architecture for appointment and service optimization in a simulated diagnostic laboratory. Its contribution is the integration of explicit state-space formulation, weighted graph search, manually implemented data structures, role-based operations, and durable audit-backed state. FCFS remains a necessary baseline, while UCS and A* provide principled cost-aware alternatives and aging prevents indefinite waiting. The system is ready for controlled demonstration and further FYP validation once benchmark and UI evidence are collected.
