# QueueLess AI — User Manual

## 1. Access and Roles

Open the frontend at the configured Vite address and sign in with the account role:

- **Customer Portal:** book a diagnostic service and track a token.
- **Staff Workspace:** dashboard, booking, counter operations, configuration, AI search, Data Structures, analytics, and profile.
- **Admin and Staff** share the workspace shell; API authorization controls access to protected operations.

Do not share account credentials. A user may see only the data and actions permitted by their role.

## 2. Customer Portal

### 2.1 Book a Diagnostic Service

1. Open **Customer Booking** in the Staff Workspace or use the Customer Portal.
2. Enter the patient name. The new booking field starts blank.
3. Select one of the configured diagnostic services.
4. Review the displayed estimated service duration.
5. Select **Generate digital token** and keep the returned token ID.

The current system does not verify appointment dates, time slots, or appointment eligibility. Do not treat a booking as a confirmed time-slot appointment.

### 2.2 Scheduling Priority

Public bookings are assigned `STANDARD` priority by the server; clients cannot choose elevated priority or backdate arrival time. Queue ordering uses effective priority, then the earliest server-recorded `arrival_timestamp`, then token ID for deterministic ties. The system has no verified appointment-priority mechanism, so appointment-based priority is not applied.

### 2.3 Receive and Track a Digital Token

1. The booking response displays the generated token, for example `Q101`, patient, selected service, and status.
2. The token tracker refreshes automatically; a patient can also enter a token ID to look it up.
3. A waiting token may display an estimated wait. The estimate is not a guaranteed start time.
4. A called or in-progress token displays its lifecycle status. A completed token displays **Service Completed** and no longer shows an active route or ETA.

### 2.4 Read Waiting-Time Analytics

Average waiting time is the mean interval from `arrival_timestamp` to `service_started_at`, in minutes, for `S5_IN_PROGRESS` and `S6_COMPLETED` tokens with valid timestamps. Waiting/called tokens, missing timestamps, malformed timestamps, and negative intervals are excluded and reported separately. An empty valid sample is shown as **No valid data**, not as a zero-minute average.

## 3. Staff Counter Console

### 3.1 View the Counter Queue

1. Sign in as Counter Staff.
2. Select the authorized counter.
3. Review the waiting list, token stage, priority, and estimated service time.
4. Confirm that the counter is marked available before calling a token.

The queue is ordered by effective scheduling priority and arrival timestamp. Do not manually bypass a token unless a hold, transfer, or administrative instruction is recorded.

### 3.2 Call the Next Token

1. Select **Call Next**.
2. Confirm the token identity and appointment/service details.
3. Select **Start Service**.
4. The token moves from \(S_4(c_i)\), counter assigned, to \(S_5(c_i)\), service in progress.
5. The console records the staff action and timestamp.

If the token is missing or the counter is unavailable, stop and report the error; do not retry an uncertain mutation repeatedly.

### 3.3 Advance Service Stages

Use the stage control only after the current stage has actually finished:

1. **Registration:** select **Complete Registration**.
2. **Sample Collection:** perform and record collection, then select **Complete Sample Collection**.
3. **Report Collection:** provide or verify the report, then select **Complete Report Collection**.
4. **Service Completion:** select **Complete Service**.

The normal state progression is:

$$
S_4(c_i)\rightarrow S_5(c_i)\rightarrow S_6.
$$

The stage labels inside \(S_5\) are `Registration`, `Sample Collection`, and `Report Collection`. Each transition creates an immutable service-audit event. Invalid order, unauthorized counter access, or completion of a held token is rejected.

### 3.4 Hold, Resume, and Transfer

1. Select **Hold** when service cannot continue.
2. Add the operational reason required by local procedure.
3. Select **Resume** when the same counter can continue.
4. Select **Transfer** only when another counter is available and the token is eligible.
5. Confirm the destination counter and the transfer event.

Never create a second active queue entry manually. The system must remove the source assignment and create the destination assignment atomically.

## 4. Admin & AI Inspector Console

### 4.1 Toggle Counter Status

1. Sign in as Administrator.
2. Open **Counter Management**.
3. Select Counter 1, Counter 2, or Counter 3.
4. Toggle **Available** or **Unavailable**.
5. Confirm the change.

Unavailable counters are excluded from new assignment routes. Existing active service remains visible and must be completed or transferred according to policy.

### 4.2 Compare BFS, UCS, and A*

1. Open **AI Inspector > Graph Visualizer**.
2. Select a token or enter a source state and goal state.
3. Select `BFS`, `UCS`, or `A*`.
4. Select **Run Search**.
5. Compare the returned route, path cost, expanded nodes, and counter branch.

Interpret results as follows:

- **BFS** minimizes edge count and ignores unequal edge weights.
- **UCS** minimizes accumulated path cost.
- **A\*** minimizes accumulated cost using \(f(n)=g(n)+h(n)\) when the heuristic is admissible and consistent.

The visualizer is an inspection tool. It does not change a live assignment unless the administrator confirms the assignment action.

### 4.3 Use the Data Structures Visualizer

Open **DS Visualizer** and select:

- **Array:** insert, delete, search, update, and traverse.
- **Linked List:** insert at the beginning, end, or position; delete, search, and traverse.
- **Priority Queue:** enqueue, dequeue, peek, update priority, and display.
- **Binary Search Tree:** insert, search, delete, and run inorder, preorder, or postorder traversals.

These operations use the manual backend data-structure classes in an isolated in-memory playground. They do not inspect or mutate operational tokens, queues, counters, or SQLite records; playground contents reset when the backend process restarts.

## 5. Safe Operating Rules

- Do not refresh or close the browser while a mutation is showing an indeterminate result; check token status first.
- Do not edit SQLite directly during service.
- Protect customer information when taking screenshots.
- Report incorrect ETA, duplicate tokens, invalid stage transitions, or missing audit events with the token and timestamp.
