# QueueLess AI — AI Algorithms Documentation

## 1. Search Model

Search operates on the weighted directed graph \(G=(V,E,W)\). A node \(n\) stores its state, parent, path cost \(g(n)\), and remaining stages. The goal test succeeds when the token reaches `service_completion`. All edge costs are non-negative.

Let:

- \(b\) be the maximum branching factor;
- \(d\) be the shallowest goal depth;
- \(C^*\) be the optimal solution cost;
- \(\epsilon>0\) be a lower bound on every positive edge cost.

## 2. Breadth-First Search

BFS expands the shallowest unexpanded node first. It is appropriate when each action has equal cost or when minimizing the number of transitions is the objective.

### Pseudocode

```text
BFS(problem):
    frontier <- FIFO queue containing problem.initial
    discovered <- {problem.initial}
    parent <- empty map

    while frontier is not empty:
        node <- frontier.dequeue()
        if problem.goal_test(node):
            return reconstruct_path(parent, node)

        for child in problem.successors(node):
            if child not in discovered:
                discovered.add(child)
                parent[child] <- node
                frontier.enqueue(child)

    return FAILURE
```

### Properties

| Property | Result |
|---|---|
| Completeness | Complete when \(b\) is finite. |
| Optimality | Optimal by number of edges when all edge costs are equal; not generally optimal for unequal durations. |
| Time complexity | \(O(b^{d+1})\). |
| Space complexity | \(O(b^{d+1})\), because the frontier and discovered set are retained. |

## 3. Uniform-Cost Search

UCS expands the frontier node with minimum accumulated path cost \(g(n)\). It is Dijkstra's algorithm over the implicit state graph.

### Pseudocode

```text
UCS(problem):
    frontier <- min-priority queue containing (0, problem.initial)
    best_cost <- {problem.initial: 0}
    parent <- empty map

    while frontier is not empty:
        (cost, node) <- frontier.extract_min()
        if cost != best_cost[node]:
            continue
        if problem.goal_test(node):
            return reconstruct_path(parent, node), cost

        for (child, step_cost) in problem.successors(node):
            new_cost <- cost + step_cost
            if child not in best_cost or new_cost < best_cost[child]:
                best_cost[child] <- new_cost
                parent[child] <- node
                frontier.insert(new_cost, child)

    return FAILURE
```

### Properties

With finite branching and non-negative costs, UCS is complete. If every positive edge cost is at least \(\epsilon\), it expands only nodes with \(g(n)\le C^*\), plus a bounded frontier layer:

$$
T_{\text{UCS}}=O\left(b^{1+\lfloor C^*/\epsilon\rfloor}\right),
\qquad
S_{\text{UCS}}=O\left(b^{1+\lfloor C^*/\epsilon\rfloor}\right).
$$

UCS is optimal for non-negative edge costs because the first goal removed from the priority queue has the least possible path cost.

## 4. A* Search

A* orders the frontier by:

$$
f(n)=g(n)+h(n),
$$

where \(g(n)\) is the cost already incurred and \(h(n)\) estimates the least remaining cost.

### Pseudocode

```text
A_STAR(problem, heuristic):
    frontier <- min-priority queue containing
                (heuristic(problem.initial), 0, problem.initial)
    best_cost <- {problem.initial: 0}
    parent <- empty map

    while frontier is not empty:
        (priority, cost, node) <- frontier.extract_min()
        if cost != best_cost[node]:
            continue
        if problem.goal_test(node):
            return reconstruct_path(parent, node), cost

        for (child, step_cost) in problem.successors(node):
            new_cost <- cost + step_cost
            if child not in best_cost or new_cost < best_cost[child]:
                best_cost[child] <- new_cost
                parent[child] <- node
                frontier.insert(
                    new_cost + heuristic(child),
                    new_cost,
                    child,
                )

    return FAILURE
```

### Properties

| Condition | Result |
|---|---|
| Finite branching and positive lower edge bound \(\epsilon\) | Complete. |
| Admissible \(h\) with graph-search reopenings | Optimal. |
| Consistent \(h\) | Optimal without reopening a closed node; \(f\)-values are non-decreasing along a path. |
| Worst-case time | \(O(b^{1+\lfloor C^*/\epsilon\rfloor})\), with lower practical expansion when \(h\) is informative. |
| Worst-case space | \(O(b^{1+\lfloor C^*/\epsilon\rfloor})\). |

## 5. QueueLess AI Heuristic

Let `remaining_stages(n)` be the ordered stages not yet completed at node \(n\). Define:

$$
h(n)=\sum_{k\in\text{remaining\_stages}(n)}
\min_{i\in\{1,2,3\}}D_{\text{service}}(k,c_i).
$$

The heuristic ignores waiting, transfers, and transition overhead. Ignoring non-negative costs can only make the estimate smaller than the true remaining cost.

### 5.1 Admissibility Proof

Let \(h^*(n)\) be the true minimum cost from \(n\) to a goal.

1. Every valid solution must process every \(k\in\text{remaining\_stages}(n)\).
2. For any counter \(c_i\), the service duration satisfies:
   \[
   D_{\text{service}}(k,c_i)\geq
   \min_{j\in\{1,2,3\}}D_{\text{service}}(k,c_j).
   \]
3. Therefore, the sum of mandatory service durations on any solution path is at least \(h(n)\).
4. The actual path also pays non-negative waiting and transition costs.
5. Hence every solution path has cost at least \(h(n)\), and the least such path satisfies:
   \[
   h(n)\leq h^*(n).
   \]

Thus \(h\) is admissible.

### 5.2 Consistency Proof

Consider an edge \(n\rightarrow n'\) that completes the next stage \(k\). Let its actual step cost be:

$$
w(n,n')=W_{\text{wait}}+D_{\text{service}}(k,c_i)+\tau_{\text{transition}}.
$$

1. The remaining stages in \(n'\) are the remaining stages in \(n\) with \(k\) removed.
2. Therefore:
   \[
   h(n)-h(n')=
   \min_jD_{\text{service}}(k,c_j).
   \]
3. Since counter \(c_i\) performs \(k\):
   \[
   \min_jD_{\text{service}}(k,c_j)
   \leq D_{\text{service}}(k,c_i).
   \]
4. Since waiting and transition costs are non-negative:
   \[
   D_{\text{service}}(k,c_i)
   \leq w(n,n').
   \]
5. Thus:
   \[
   h(n)\leq w(n,n')+h(n').
   \]

This is the consistency inequality. At a goal, the remaining-stage set is empty and \(h(\text{goal})=0\). Therefore the heuristic is consistent under the stated edge-cost model.

## 6. Q101 Dry-Run Trace

Assume token `Q101` has three remaining stages and the following durations:

| Stage | Counter 1 | Counter 2 | Counter 3 |
|---|---:|---:|---:|
| Registration | 5 | 4 | 3 |
| Sample Collection | 8 | 7 | 6 |
| Report Collection | 2 | 2 | 1 |

Assume each counter assignment edge has one minute of transition cost, no waiting cost, and the search graph contains the three counter branches. BFS minimizes depth, whereas UCS and A* minimize duration plus transition cost.

| Step | Current node | BFS frontier choice | UCS frontier choice \(g\) | A* frontier choice \(f=g+h\) |
|---:|---|---|---|---|
| 0 | `waiting_queue` | Expand `counter_1.registration` (in insertion order) | Choose `counter_3.registration` with \(g=4\) | Choose `counter_3.registration` with \(f=4+(6+1)=11\) |
| 1 | Counter 1 / Counter 3 registration | Enqueue all sample-collection nodes at depth 2 | Expand `counter_3.sample_collection`, \(g=11\) | Expand `counter_3.sample_collection`, \(f=11+(1)=12\) |
| 2 | Sample collection | Enqueue all report-collection nodes at depth 3 | Expand `counter_3.report_collection`, \(g=13\) | Expand `counter_3.report_collection`, \(f=13\) |
| 3 | Report collection | Return first depth-4 completion branch, potentially Counter 1 | Expand `service_completion`, \(g=14\) | Expand `service_completion`, \(f=14\) |

The optimal branch for the stated data is Counter 3:

$$
1+3+1+6+1+1+1=14\text{ minutes},
$$

where the terms are assignment transition, registration, stage transition, sample collection, stage transition, report collection, and completion transition. BFS remains complete and returns a shallowest path, but its result depends on branch order when all branches have equal depth and therefore need not minimize the 14-minute cost.
