import { useEffect, useMemo, useState } from "react";
import { searchRoute } from "../api";

const COUNTERS = ["counter_1", "counter_2", "counter_3"];
const NODE_WIDTH = 148;
const NODE_HEIGHT = 62;
const COUNTER_Y = [155, 340, 525];

const nodePositions = {
  S1: { x: 150, y: 70 },
  S2: { x: 150, y: 175 },
  waiting_queue: { x: 150, y: 340 },
  S4: { x: 355, y: 340 },
  service_completion: { x: 1090, y: 340 },
};

function counterNodeId(counterId, stage) {
  return `${counterId}.${stage}`;
}

function formatNodeName(nodeId) {
  if (nodeId === "waiting_queue") return "Waiting queue";
  if (nodeId === "service_completion") return "Service complete";
  const [counter, stage] = nodeId.split(".");
  if (!stage) return nodeId;
  return `${counter.replace("_", " ")} · ${stage.replaceAll("_", " ")}`;
}

function edgeSegment(source, target) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const scale = Math.min(
    (NODE_WIDTH / 2 - 5) / Math.max(Math.abs(dx), 0.001),
    (NODE_HEIGHT / 2 - 5) / Math.max(Math.abs(dy), 0.001),
  );
  const startX = source.x + dx * scale;
  const startY = source.y + dy * scale;
  const endX = target.x - dx * scale;
  const endY = target.y - dy * scale;
  return {
    d: `M ${startX} ${startY} L ${endX} ${endY}`,
    labelX: (startX + endX) / 2,
    labelY: (startY + endY) / 2 - 7,
  };
}

function lifecycleNodes() {
  return [
    {
      id: "S1",
      title: "S1 · BOOKED",
      subtitle: "Appointment booked",
      x: nodePositions.S1.x,
      y: nodePositions.S1.y,
      lifecycle: "S1_BOOKED",
      kind: "lifecycle",
    },
    {
      id: "S2",
      title: "S2 · TOKEN",
      subtitle: "Token generated",
      x: nodePositions.S2.x,
      y: nodePositions.S2.y,
      lifecycle: "S2_TOKEN_GENERATED",
      kind: "lifecycle",
    },
    {
      id: "waiting_queue",
      title: "S3 · WAITING",
      subtitle: "Waiting queue",
      x: nodePositions.waiting_queue.x,
      y: nodePositions.waiting_queue.y,
      lifecycle: "S3_WAITING",
      kind: "lifecycle",
    },
    {
      id: "S4",
      title: "S4 · ASSIGNED",
      subtitle: "Counter assignment",
      x: nodePositions.S4.x,
      y: nodePositions.S4.y,
      lifecycle: "S4_COUNTER_ASSIGNED",
      kind: "lifecycle",
    },
  ];
}

function getGraphNodes(graphNodes) {
  const byId = new Map((graphNodes ?? []).map((node) => [node.id, node]));
  const nodes = lifecycleNodes();

  COUNTERS.forEach((counterId, index) => {
    ["registration", "sample_collection", "report_collection"].forEach(
      (stage) => {
        const id = counterNodeId(counterId, stage);
        const graphNode = byId.get(id);
        nodes.push({
          id,
          title: `S5 · ${counterId.replace("_", " ").toUpperCase()}`,
          subtitle:
            graphNode?.label ??
            `${counterId.replace("_", " ")} · ${stage.replaceAll("_", " ")}`,
          x: stage === "registration" ? 535 : stage === "sample_collection" ? 720 : 905,
          y: COUNTER_Y[index],
          lifecycle: "S5_IN_PROGRESS",
          kind: "service",
          unavailable: !graphNode,
        });
      },
    );
  });

  const completion = byId.get("service_completion");
  nodes.push({
    id: "service_completion",
    title: "S6 · COMPLETE",
    subtitle: completion?.label ?? "Service complete",
    x: nodePositions.service_completion.x,
    y: nodePositions.service_completion.y,
    lifecycle: "S6_COMPLETED",
    kind: "lifecycle",
  });
  return nodes;
}

function getEdges(graphEdges) {
  const edges = [
    { source: "S1", target: "S2", action: "appointment", cost: null },
    { source: "S2", target: "waiting_queue", action: "generate_token", cost: null },
    { source: "waiting_queue", target: "S4", action: "assign_counter", cost: null },
  ];

  (graphEdges ?? []).forEach((edge) => {
    edges.push({
      ...edge,
      source: edge.source === "waiting_queue" ? "S4" : edge.source,
    });
  });
  return edges;
}

function getGoalForToken(token) {
  const counterId = token?.counter_id;
  if (!counterId || !["1", "2", "3"].includes(counterId)) {
    return "service_completion";
  }
  return `counter_${counterId}.report_collection`;
}

function calculateGCosts(result, algorithm) {
  const edges = result?.graph?.edges ?? [];
  const distances = new Map([["waiting_queue", 0]]);
  if (algorithm === "BFS") {
    for (const step of result?.trace_steps ?? []) {
      const currentCost = distances.get(step.current_node);
      if (currentCost === undefined) continue;
      for (const edge of edges) {
        if (edge.source === step.current_node && !distances.has(edge.target)) {
          distances.set(edge.target, currentCost + edge.cost);
        }
      }
    }
    return distances;
  }

  const pending = new Set(["waiting_queue"]);
  const visited = new Set();
  while (pending.size) {
    let currentNode;
    let currentCost = Number.POSITIVE_INFINITY;
    pending.forEach((nodeId) => {
      const nodeCost = distances.get(nodeId);
      if (nodeCost !== undefined && nodeCost < currentCost) {
        currentNode = nodeId;
        currentCost = nodeCost;
      }
    });
    if (!currentNode) break;
    pending.delete(currentNode);
    visited.add(currentNode);
    for (const edge of edges) {
      if (edge.source !== currentNode || visited.has(edge.target)) continue;
      const nextCost = currentCost + edge.cost;
      if (nextCost < (distances.get(edge.target) ?? Number.POSITIVE_INFINITY)) {
        distances.set(edge.target, nextCost);
        pending.add(edge.target);
      }
    }
  }
  return distances;
}

function formatCost(value) {
  return value === undefined || !Number.isFinite(value)
    ? "—"
    : `${Number(value.toFixed(1))}`;
}

function getTraceNodeIds(step, path) {
  const ids = new Set(path ?? []);
  if (!step) return [...ids];
  ids.add(step.current_node);
  step.visited.forEach((id) => ids.add(id));
  step.frontier.forEach((id) => ids.add(id));
  return [...ids];
}

/**
 * @param {{ tokens: import("../types").Token[] }} props
 */
export default function GraphVisualizer({ tokens }) {
  const [algorithm, setAlgorithm] = useState("A*");
  const [selectedTokenId, setSelectedTokenId] = useState("");
  const [result, setResult] = useState(null);
  const [stepIndex, setStepIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tokens.length) {
      setSelectedTokenId("");
      return;
    }
    if (!tokens.some((token) => token.token_id === selectedTokenId)) {
      setSelectedTokenId(tokens[0].token_id);
    }
  }, [tokens, selectedTokenId]);

  const selectedToken = tokens.find(
    (token) => token.token_id === selectedTokenId,
  );
  const goalState = getGoalForToken(selectedToken);
  const traceSteps = result?.trace_steps ?? [];
  const currentStep = stepIndex >= 0 ? traceSteps[stepIndex] : null;
  const graphNodes = useMemo(
    () => getGraphNodes(result?.graph?.nodes ?? []),
    [result],
  );
  const graphEdges = useMemo(
    () => getEdges(result?.graph?.edges ?? []),
    [result],
  );
  const positions = useMemo(
    () => new Map(graphNodes.map((node) => [node.id, node])),
    [graphNodes],
  );
  const path = result?.optimal_path ?? [];
  const pathSet = useMemo(() => new Set(path), [path]);
  const frontierSet = useMemo(
    () => new Set(currentStep?.frontier ?? []),
    [currentStep],
  );
  const visitedSet = useMemo(
    () => new Set(currentStep?.visited ?? []),
    [currentStep],
  );
  const gCosts = useMemo(
    () => calculateGCosts(result, algorithm),
    [result, algorithm],
  );
  const visibleCostNodes = getTraceNodeIds(currentStep, path);

  useEffect(() => {
    if (!isPlaying) return undefined;
    const interval = window.setInterval(() => {
      setStepIndex((current) => Math.min(current + 1, traceSteps.length - 1));
    }, 750);
    return () => window.clearInterval(interval);
  }, [isPlaying, traceSteps.length]);

  useEffect(() => {
    if (isPlaying && stepIndex >= traceSteps.length - 1) {
      setIsPlaying(false);
    }
  }, [isPlaying, stepIndex, traceSteps.length]);

  async function runSearch() {
    setIsRunning(true);
    setIsPlaying(false);
    setError("");
    setResult(null);
    setStepIndex(-1);
    try {
      setResult(await searchRoute(algorithm, goalState));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Search request failed.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  function chooseToken(tokenId) {
    setSelectedTokenId(tokenId);
    setResult(null);
    setStepIndex(-1);
    setIsPlaying(false);
    setError("");
  }

  function stepForward() {
    setIsPlaying(false);
    setStepIndex((current) => Math.min(current + 1, traceSteps.length - 1));
  }

  function togglePlay() {
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }
    if (stepIndex >= traceSteps.length - 1) setStepIndex(-1);
    setIsPlaying(true);
  }

  function edgeClass(edge) {
    const pathEdge =
      pathSet.has(edge.source === "S4" ? "waiting_queue" : edge.source) &&
      pathSet.has(edge.target);
    if (pathEdge) return "graph-edge graph-edge-optimal";
    if (currentStep?.current_node === edge.source) {
      return "graph-edge graph-edge-current";
    }
    if (frontierSet.has(edge.target)) return "graph-edge graph-edge-frontier";
    return "graph-edge";
  }

  function nodeClass(node) {
    const searchId = node.id === "S3" ? "waiting_queue" : node.id;
    const isCurrent =
      currentStep?.current_node === searchId ||
      (node.id === "S4" && currentStep?.current_node === "waiting_queue");
    const isVisited =
      visitedSet.has(searchId) ||
      (node.id === "S4" && visitedSet.has("waiting_queue"));
    const isFrontier = frontierSet.has(searchId);
    const isOptimal = pathSet.has(searchId) || (node.id === "S4" && path.length > 1);
    return [
      "graph-node",
      `graph-node-${node.kind}`,
      isOptimal && "graph-node-optimal",
      isVisited && "graph-node-visited",
      isFrontier && "graph-node-frontier",
      isCurrent && "graph-node-current",
      node.unavailable && "graph-node-unavailable",
    ]
      .filter(Boolean)
      .join(" ");
  }

  return (
    <section className="graph-visualizer">
      <div className="graph-toolbar">
        <div className="graph-toolbar-heading">
          <div className="graph-kicker">STATE SPACE / SEARCH EXECUTION</div>
          <h2>Route search visualizer</h2>
          <p>Inspect how each algorithm explores the live service graph.</p>
        </div>
        <div className="graph-controls">
          <label>
            <span>ALGORITHM</span>
            <select
              value={algorithm}
              onChange={(event) => {
                setAlgorithm(event.target.value);
                setResult(null);
                setStepIndex(-1);
                setIsPlaying(false);
              }}
            >
              <option value="BFS">BFS</option>
              <option value="UCS">UCS</option>
              <option value="A*">A* Search</option>
            </select>
          </label>
          <label>
            <span>TARGET TOKEN</span>
            <select
              value={selectedTokenId}
              onChange={(event) => chooseToken(event.target.value)}
              disabled={!tokens.length}
            >
              {tokens.length ? (
                tokens.map((token) => (
                  <option value={token.token_id} key={token.token_id}>
                    {token.token_id} · {token.customer_name} ·{" "}
                    {token.counter_id
                      ? `Counter ${token.counter_id}`
                      : "Unassigned"}
                  </option>
                ))
              ) : (
                <option value="">No tokens available</option>
              )}
            </select>
          </label>
          <button
            type="button"
            className="graph-button graph-button-primary"
            onClick={runSearch}
            disabled={isRunning}
          >
            {isRunning ? "Running…" : "Run Search"}
          </button>
        </div>
      </div>

      {error && <div className="graph-error" role="alert">{error}</div>}

      <div className="graph-state-strip">
        <div>
          <span className="graph-state-label">TARGET</span>
          <strong>
            {selectedToken
              ? `${selectedToken.token_id} · ${selectedToken.customer_name}`
              : "Select a token"}
          </strong>
          <span>{selectedToken ? `Counter ${selectedToken.counter_id ?? "—"}` : "Token BST is empty"}</span>
        </div>
        <div>
          <span className="graph-state-label">SEARCH GOAL</span>
          <strong>{formatNodeName(goalState)}</strong>
          <span>{algorithm === "A*" ? "Heuristic-guided route" : algorithm === "UCS" ? "Lowest cumulative cost" : "Shallowest route first"}</span>
        </div>
        <div>
          <span className="graph-state-label">EXECUTION</span>
          <strong>{result ? `${result.algorithm} · ${result.nodes_expanded} expanded` : "Not started"}</strong>
          <span>{result ? `${traceSteps.length} trace steps` : "Run a search to load the trace"}</span>
        </div>
      </div>

      <div className="graph-workspace">
        <div className="graph-canvas-panel">
          <div className="graph-canvas-heading">
            <span>WEIGHTED SERVICE STATE GRAPH</span>
            {currentStep && (
              <span className="trace-step-pill">
                STEP {String(stepIndex + 1).padStart(2, "0")} /{" "}
                {String(traceSteps.length).padStart(2, "0")}
              </span>
            )}
          </div>
          <div className="graph-canvas-scroll">
            <svg
              className="state-graph"
              viewBox="0 0 1240 650"
              role="img"
              aria-label="QueueLess state-space graph with lifecycle and counter branches"
            >
              <defs>
                <marker
                  id="graph-arrow"
                  markerWidth="7"
                  markerHeight="7"
                  refX="6"
                  refY="3.5"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L7,3.5 L0,7 z" className="graph-arrow-fill" />
                </marker>
                <marker
                  id="graph-arrow-optimal"
                  markerWidth="7"
                  markerHeight="7"
                  refX="6"
                  refY="3.5"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L7,3.5 L0,7 z" className="graph-arrow-optimal-fill" />
                </marker>
              </defs>
              <text className="graph-column-label" x="150" y="35" textAnchor="middle">
                CUSTOMER LIFECYCLE
              </text>
              <text className="graph-column-label" x="690" y="75" textAnchor="middle">
                COUNTER SERVICE BRANCHES
              </text>
              <text className="graph-column-label" x="1090" y="255" textAnchor="middle">
                TERMINAL STATE
              </text>

              {graphEdges.map((edge, index) => {
                const source = positions.get(edge.source);
                const target = positions.get(edge.target);
                if (!source || !target) return null;
                const segment = edgeSegment(source, target);
                const className = edgeClass(edge);
                return (
                  <g key={`${edge.source}-${edge.target}-${index}`}>
                    <path
                      d={segment.d}
                      className={className}
                      markerEnd={
                        className.includes("optimal")
                          ? "url(#graph-arrow-optimal)"
                          : "url(#graph-arrow)"
                      }
                    />
                    {edge.cost !== null && edge.cost !== undefined && (
                      <g className="edge-cost">
                        <rect
                          x={segment.labelX - 25}
                          y={segment.labelY - 10}
                          width="50"
                          height="18"
                          rx="4"
                        />
                        <text
                          x={segment.labelX}
                          y={segment.labelY + 2}
                          textAnchor="middle"
                        >
                          {Number(edge.cost).toFixed(1)}m
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {graphNodes.map((node) => (
                <g
                  className={nodeClass(node)}
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                >
                  <rect
                    className="graph-node-box"
                    x={-NODE_WIDTH / 2}
                    y={-NODE_HEIGHT / 2}
                    width={NODE_WIDTH}
                    height={NODE_HEIGHT}
                    rx="7"
                  />
                  <text className="graph-node-title" x="0" y="-5" textAnchor="middle">
                    {node.title}
                  </text>
                  <text className="graph-node-subtitle" x="0" y="14" textAnchor="middle">
                    {node.subtitle}
                  </text>
                  {node.unavailable && (
                    <text className="graph-node-state" x="0" y="27" textAnchor="middle">
                      NO ACTIVE BRANCH
                    </text>
                  )}
                  {node.kind === "lifecycle" && node.id !== "S4" && (
                    <text className="graph-node-state" x="0" y="27" textAnchor="middle">
                      {node.lifecycle.replaceAll("_", " ")}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>
          <div className="graph-legend">
            <span><i className="legend-dot legend-current" /> Expanding</span>
            <span><i className="legend-dot legend-visited" /> Visited / closed</span>
            <span><i className="legend-dot legend-frontier" /> Active frontier</span>
            <span><i className="legend-line legend-optimal" /> Optimal path</span>
            <span className="graph-legend-note">Edge labels show estimated minutes</span>
          </div>
        </div>

        <aside className="graph-side-panel">
          <section className="graph-subpanel execution-panel">
            <div className="graph-subpanel-heading">
              <div>
                <span>SEARCH FRONTIER</span>
                <strong>
                  {algorithm === "BFS" ? "Queue" : "Priority heap"}
                </strong>
              </div>
              <span className="frontier-count">
                {currentStep?.frontier.length ?? 0}
              </span>
            </div>
            <div className="current-expansion">
              <span className="graph-state-label">CURRENTLY EXPANDING</span>
              <strong>
                {currentStep
                  ? formatNodeName(currentStep.current_node)
                  : "Waiting for execution"}
              </strong>
              <span>{currentStep?.action ?? "No active trace step"}</span>
            </div>
            <div className="frontier-list">
              {currentStep?.frontier.length ? (
                currentStep.frontier.map((nodeId, index) => (
                  <div className="frontier-item" key={`${nodeId}-${index}`}>
                    <span className="frontier-index">
                      {String(index).padStart(2, "0")}
                    </span>
                    <span>{formatNodeName(nodeId)}</span>
                    <span className="frontier-node-id">{nodeId}</span>
                  </div>
                ))
              ) : (
                <div className="frontier-empty">Frontier is empty</div>
              )}
            </div>
            <div className="trace-controls">
              <button
                type="button"
                className="graph-button graph-button-secondary"
                onClick={stepForward}
                disabled={!result || stepIndex >= traceSteps.length - 1}
              >
                Step Forward
              </button>
              <button
                type="button"
                className="graph-button graph-button-play"
                onClick={togglePlay}
                disabled={!result || !traceSteps.length}
              >
                {isPlaying ? "Pause" : "Play"}
              </button>
            </div>
          </section>

          <section className="graph-subpanel cost-panel">
            <div className="graph-subpanel-heading">
              <div>
                <span>COST BREAKDOWN</span>
                <strong>
                  g(n), h(n), f(n)
                </strong>
              </div>
              <span className="cost-units">MIN</span>
            </div>
            <div className="cost-table-scroll">
              <table className="cost-table">
                <thead>
                  <tr>
                    <th>State</th>
                    <th>g</th>
                    <th>h</th>
                    <th>f</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCostNodes.length ? (
                    visibleCostNodes.map((nodeId) => {
                      const g = gCosts.get(nodeId);
                      const h = result?.heuristic_values?.[nodeId] ?? 0;
                      return (
                        <tr
                          className={nodeId === currentStep?.current_node ? "cost-row-current" : ""}
                          key={nodeId}
                        >
                          <td title={formatNodeName(nodeId)}>{formatNodeName(nodeId)}</td>
                          <td>{formatCost(g)}</td>
                          <td>{formatCost(h)}</td>
                          <td>{formatCost(g === undefined ? undefined : g + h)}</td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="4" className="cost-empty">
                        Run a search to inspect live node costs.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="cost-note">
              {algorithm === "A*"
                ? "A* combines accumulated cost g(n) with the backend heuristic h(n)."
                : `${algorithm} uses h(n) = 0; f(n) equals the accumulated path cost.`}
            </p>
          </section>
        </aside>
      </div>

      <div className="graph-result-bar">
        <div className="graph-result-copy">
          <span className="graph-state-label">OPTIMAL PATH</span>
          <strong>
            {result?.optimal_path?.length
              ? result.optimal_path.map(formatNodeName).join("  →  ")
              : result
                ? "No route found for this target."
                : "Run search to calculate the target route."}
          </strong>
        </div>
        <div className="graph-result-stats">
          <span>
            <small>TOTAL COST</small>
            <strong>
              {result?.total_cost === null || result?.total_cost === undefined
                ? "—"
                : `${Number(result.total_cost).toFixed(1)} min`}
            </strong>
          </span>
          <span>
            <small>EXPANDED</small>
            <strong>{result?.nodes_expanded ?? "—"}</strong>
          </span>
          <span>
            <small>TRACE STEP</small>
            <strong>
              {currentStep
                ? `${stepIndex + 1} / ${traceSteps.length}`
                : `0 / ${traceSteps.length}`}
            </strong>
          </span>
        </div>
      </div>
    </section>
  );
}
