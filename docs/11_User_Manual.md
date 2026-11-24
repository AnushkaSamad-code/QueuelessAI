# QueueLess AI — User Manual

## 1. Access and Roles

Open the frontend at the configured Vite address. Use the role assigned to the account:

- **Customer Portal:** appointment, check-in, token, and ETA actions.
- **Staff Counter Console:** queue and stage operations for authorized counters.
- **Admin & AI Inspector Console:** counter availability, analytics, graph search, and structure inspection.

Do not share account credentials. A user may see only the data and actions permitted by their role.

## 2. Customer Portal

### 2.1 Book an Appointment

1. Open **Customer Portal** and select **Book Appointment**.
2. Enter the customer name or verified account identity.
3. Select a diagnostic laboratory service, date, and available time slot.
4. Review the service duration and appointment details.
5. Select **Confirm Booking**.
6. Record the appointment reference shown by the confirmation message.

The system rejects past dates, closed slots, duplicate active appointments, and unknown services. A failed request does not create a token.

### 2.2 Receive a Digital Token

1. Select **Check In** and enter the appointment reference when using an appointment.
2. For a walk-in visit, select **Generate Walk-In Token**.
3. Confirm the displayed service and customer identity.
4. Select **Generate Token**.
5. The portal displays the token, for example `Q101`, its current stage, and queue status.

Keep the token visible when contacting staff. The token remains unique while its record is active or retained by the system.

### 2.3 Read the AI Recommendation and Live ETA

1. Open **My Queue Status**.
2. Read the recommended counter and the route summary.
3. Read the estimated wait and the current queue position.
4. Refresh the status or wait for the live update indicator.
5. Follow the portal instruction to proceed only when the token is called.

The recommendation is an estimate based on counter availability, queue state, stage duration, and aging priority. It is not a guarantee of completion time. A transfer or counter status change can change the ETA.

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

### 4.3 Inspect Runtime Data Structures

Open **AI Inspector > Data Structures** and select:

- **BST:** view `Inorder`, `Preorder`, or `Postorder` token traversal.
- **Min-Heap:** view effective priority, arrival timestamp, and heap order.
- **TokenArray:** view active token and counter records by index.
- **ServiceLinkedList:** view each counter queue and completed-service history.

These are runtime views reconstructed from SQLite. A discrepancy between a view and the database is a data-integrity incident and must be recorded rather than corrected by direct UI editing.

## 5. Safe Operating Rules

- Do not refresh or close the browser while a mutation is showing an indeterminate result; check token status first.
- Do not edit SQLite directly during service.
- Protect customer information when taking screenshots.
- Report incorrect ETA, duplicate tokens, invalid stage transitions, or missing audit events with the token and timestamp.
