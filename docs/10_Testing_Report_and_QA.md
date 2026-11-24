# QueueLess AI — Testing Report and Quality Assurance

## 1. QA Strategy

Verification combines automated `pytest` tests, API integration tests, SQLite recovery tests, and manual browser checks. Automated tests run against isolated fixtures and deterministic clocks. Manual checks run at the three required viewport sizes with both visual themes enabled.

Every test records: identifier, preconditions, input, expected result, actual result, status, execution date, and defect reference. A test passes only when the observed result matches the expected result without an unreported warning or state mutation.

## 2. Unit Test Matrix

| ID | Area | Test and expected result |
|---|---|---|
| UT-01 | `TokenArray` | Append records to capacity; the next append resizes within the configured maximum and preserves index order. |
| UT-02 | `TokenArray` | Remove a middle record; all following records shift left exactly once, size decrements, and no occupied slot is skipped. |
| UT-03 | `ServiceLinkedList` | Insert and remove at head; `head`, `tail`, and size remain correct, and `pop_front` returns the new head. |
| UT-04 | `ServiceLinkedList` | Insert and remove at the middle; predecessor and successor links reconnect and traversal retains order. |
| UT-05 | `ServiceLinkedList` | Insert and remove at tail and remove the final node; tail updates and the empty-list invariants hold. |
| UT-06 | `SchedulingPriorityQueue` | Insert tokens with distinct and equal keys; extraction follows minimum effective priority, then arrival timestamp. |
| UT-07 | `SchedulingPriorityQueue` | Advance a deterministic clock by 15 minutes; the waiting token receives one aging boost and can move ahead of a newer token. |
| UT-08 | `TokenBST` | Insert tokens, then delete a leaf, a node with one child, and a node with two children; BST ordering remains valid after each operation. |
| UT-09 | `TokenBST` | Verify inorder is sorted, preorder visits root before descendants, and postorder visits descendants before root. |
| UT-10 | BFS | On an equal-edge-cost graph, BFS returns a shallowest goal path and reports failure for an unreachable goal. |
| UT-11 | UCS | On a weighted graph with a longer cheap route and a shorter expensive route, UCS returns the least-cost route and cost. |
| UT-12 | A* | Compare A* cost with UCS cost and assert \(h(n)\leq h^*(n)\) for every fixture node; assert consistency on every directed edge. |

### Unit-Test Assertions

- Core data structures must not call Python `list`, `dict`, `set`, or `heapq` for their storage or core operations.
- Duplicate token identifiers must be rejected.
- Invalid indexes, empty extraction, missing keys, negative edge costs, and malformed tokens must raise typed domain errors.
- Tests use fixed timestamps so aging and tie-breaking are reproducible.

## 3. Integration and API Test Matrix

| ID | Scenario | Expected verification |
|---|---|---|
| IT-01 | Book appointment and generate token | `POST /api/v1/appointments` followed by `POST /api/v1/tokens` returns a valid unique token such as `Q101`; SQLite and runtime indexes agree. |
| IT-02 | Check in and assign counter | Check-in places the token in the heap; assignment removes it from the heap, appends it to the selected counter list, and records the route and cost. |
| IT-03 | Staff stage lifecycle | Authorized staff move a token through registration, sample collection, report collection, and completion; invalid transitions return an explicit error. |
| IT-04 | Transfer and hold | A held token transfers atomically to an available counter; source and destination queues, token state, and audit events remain consistent. |
| IT-05 | Administrator analytics | The analytics endpoint returns aggregate wait, service, throughput, utilization, transfer, and cancellation metrics for a selected date range. |
| IT-06 | Restart recovery | Stop and restart the API after booking, assignment, transfer, and completion; hydration reconstructs equivalent array, list, heap, BST, and counter state. |

## 4. Performance and Reliability Checks

1. Run 100 concurrent API operations against at least 1,000 retained or active token records.
2. Measure server-side p95 latency for token lookup, assignment, and stage transition; the target is \(\leq150\text{ ms}\).
3. Run the same seeded workload against FCFS and AI routing.
4. Verify no transaction leaves a token assigned to two counters.
5. Verify the database remains readable after controlled process interruption and recovery.
6. Store raw timings, seed, Python version, database size, and test command with the report.

## 5. Responsive UI/UX Verification Checklist

| Check | Desktop 1440px | Tablet 768px | Mobile 375px |
|---|---|---|---|
| Navigation and role identity are visible | [ ] | [ ] | [ ] |
| Booking form labels, validation, and submit action work | [ ] | [ ] | [ ] |
| Token and ETA remain readable without clipping | [ ] | [ ] | [ ] |
| Queue tables wrap, scroll, or collapse without page overflow | [ ] | [ ] | [ ] |
| Counter cards expose status and next action | [ ] | [ ] | [ ] |
| Graph visualizer remains usable and does not obscure controls | [ ] | [ ] | [ ] |
| Keyboard focus order and visible focus indicator work | [ ] | [ ] | [ ] |
| Dark and light themes meet WCAG AA contrast | [ ] | [ ] | [ ] |
| Modal traps focus and supports Escape close | [ ] | [ ] | [ ] |
| Modal scroll lock prevents background scrolling and restores it on close | [ ] | [ ] | [ ] |
| No horizontal scrolling at 375px | [ ] | [ ] | [ ] |

## 6. Defect Tracking and Resolution Log

| Defect ID | Detected in | Severity | Description and reproduction | Expected | Actual | Root cause | Fix/commit | Retest result | Status |
|---|---|---|---|---|---|---|---|---|---|
| DEF-___ | UT/IT/UI-___ | Critical/High/Medium/Low |  |  |  |  |  |  | Open |

Severity rules: Critical blocks startup or corrupts state; High blocks a primary workflow; Medium affects a non-primary function or accessibility criterion; Low affects presentation or documentation without data impact. A defect may be closed only after the original test and a regression test pass.

## 7. Release Gate

The release is acceptable only when all UT-01–UT-12 and IT-01–IT-06 pass, no Critical or High defects remain open, the responsive checklist has evidence for all three viewports, and the p95 latency and SQLite recovery checks meet their stated criteria.
