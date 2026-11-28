import { useEffect, useMemo, useState } from "react";
import { compareRoute } from "../api";

const ALGORITHMS = ["BFS", "UCS", "A*"];
const GRAPH_STATES = [
  "Registration",
  "Sample Collection",
  "Report Collection",
  "Service Completed",
];
const NODE_WIDTH = 156;
const NODE_HEIGHT = 70;

function costLabel(cost) {
  return Number.isInteger(cost) ? `${cost} min` : `${cost.toFixed(1)} min`;
}

/**
 * @param {{ services: import("../types").Service[] }} props
 */
export default function GraphVisualizer({ services }) {
  const [serviceId, setServiceId] = useState(services[0]?.service_id ?? "");
  const [goalState, setGoalState] = useState("Service Completed");
  const [algorithm, setAlgorithm] = useState("A*");
  const [comparison, setComparison] = useState(null);
  const [stepIndex, setStepIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (!services.length) {
      setServiceId("");
    } else if (!services.some((service) => service.service_id === serviceId)) {
      setServiceId(services[0].service_id);
    }
  }, [services, serviceId]);

  useEffect(() => {
    if (!serviceId || !goalState) {
      setComparison(null);
      setLoading(false);
      return undefined;
    }
    let active = true;
    setComparison(null);
    setStepIndex(-1);
    setPlaying(false);
    setError("");
    setLoading(true);
    compareRoute(serviceId, goalState)
      .then((result) => {
        if (active) setComparison(result);
      })
      .catch((requestError) => {
        if (active) {
          setComparison(null);
          setError(requestError instanceof Error ? requestError.message : "Search comparison failed.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [serviceId, goalState, algorithm]);

  const result = comparison?.results?.[algorithm];
  const trace = result?.trace_steps ?? [];
  const currentStep = stepIndex >= 0 ? trace[stepIndex] ?? null : null;
  const visited = useMemo(() => new Set(currentStep?.visited ?? []), [currentStep]);
  const frontier = useMemo(() => new Set(currentStep?.frontier ?? []), [currentStep]);
  const optimalPath = useMemo(() => new Set(result?.optimal_path ?? []), [result]);
  const nodes = comparison?.graph?.nodes ?? [];
  const edges = comparison?.graph?.edges ?? [];
  const noRoute = Boolean(result && result.optimal_path.length === 0);

  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setInterval(() => {
      setStepIndex((current) => Math.min(current + 1, trace.length - 1));
    }, 750);
    return () => window.clearInterval(timer);
  }, [playing, trace.length]);

  useEffect(() => {
    if (playing && (!trace.length || stepIndex >= trace.length - 1)) setPlaying(false);
  }, [playing, stepIndex, trace.length]);

  const finiteCosts = ALGORITHMS
    .map((name) => comparison?.results?.[name]?.total_cost)
    .filter((cost) => cost !== null && cost !== undefined);
  const minWeightedCost = finiteCosts.length ? Math.min(...finiteCosts) : null;

  function resetExecution() {
    setPlaying(false);
    setStepIndex(-1);
    setZoom(1);
  }

  function chooseService(value) {
    resetExecution();
    setComparison(null);
    setError("");
    setServiceId(value);
  }

  function chooseGoal(value) {
    resetExecution();
    setComparison(null);
    setError("");
    setGoalState(value);
  }

  function chooseAlgorithm(value) {
    resetExecution();
    setComparison(null);
    setError("");
    setAlgorithm(value);
  }

  return (
    <div className="academic-page">
      <section className="panel problem-formulation">
        <div className="panel-heading">
          <div className="panel-eyebrow">PROBLEM A · SERVICE ROUTE SEARCH</div>
          <h2>Problem Formulation</h2>
          <p>Searches use the same fixed diagnostic workflow; counter assignment is a separate problem.</p>
        </div>
        <div className="formulation-grid">
          {[
            ["Initial State", comparison?.problem_formulation?.initial_state ?? "Registration"],
            ["Goal State", goalState],
            ["Actions", (comparison?.problem_formulation?.actions ?? ["Complete the current diagnostic stage"]).join("; ")],
            ["Transition Model", comparison?.problem_formulation?.transition_model ?? "Registration → Sample Collection → Report Collection → Service Completed"],
            ["State Space", GRAPH_STATES.join(" → ")],
            ["Graph Representation", "Directed graph represented as states with outgoing weighted edges."],
            ["Dictionary Representation", "Each state maps to its outgoing actions and successor states."],
            ["Path Cost Function", comparison?.problem_formulation?.path_cost_function ?? "g(n) = cumulative estimated stage duration in minutes"],
            ["Heuristic Function h(n)", comparison?.problem_formulation?.heuristic_function ?? "Sum of minimum remaining stage durations; an admissible lower bound."],
            ["Goal Test", `Current state equals ${goalState}`],
          ].map(([label, value]) => (
            <div className="formulation-item" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="panel graph-visualizer">
        <div className="graph-toolbar">
          <div className="graph-toolbar-heading">
            <span className="graph-kicker">INTERACTIVE SEARCH TRACE</span>
            <h2>Diagnostic service route</h2>
            <p>BFS minimizes edge count; UCS and A* compare cumulative duration cost.</p>
          </div>
          <div className="graph-controls">
            <label>
              <span>Service</span>
              <select value={serviceId} onChange={(event) => chooseService(event.target.value)} disabled={!services.length}>
                {services.map((service) => (
                  <option value={service.service_id} key={service.service_id}>{service.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Goal state</span>
              <select value={goalState} onChange={(event) => chooseGoal(event.target.value)}>
                {GRAPH_STATES.map((state) => <option value={state} key={state}>{state}</option>)}
              </select>
            </label>
            <label>
              <span>Trace algorithm</span>
              <select value={algorithm} onChange={(event) => chooseAlgorithm(event.target.value)}>
                {ALGORITHMS.map((name) => <option value={name} key={name}>{name}</option>)}
              </select>
            </label>
          </div>
        </div>

        <div className="graph-execution-layout">
          <div className="graph-display-column">
            <div className="graph-action-toolbar" aria-label="Graph controls">
              <button className="button button-secondary button-small" type="button" onClick={() => setZoom((value) => Math.max(0.7, Number((value - 0.1).toFixed(1))))} aria-label="Zoom out">−</button>
              <span className="graph-zoom-value">{Math.round(zoom * 100)}%</span>
              <button className="button button-secondary button-small" type="button" onClick={() => setZoom((value) => Math.min(1.4, Number((value + 0.1).toFixed(1))))} aria-label="Zoom in">+</button>
              <button className="button button-secondary button-small" type="button" onClick={() => setZoom(1)}>Fit</button>
              <button className="button button-secondary button-small" type="button" onClick={resetExecution}>Reset</button>
              <button className="button button-primary button-small" type="button" disabled={loading || !trace.length || noRoute} onClick={() => { setPlaying(false); setStepIndex(0); }}>Explore</button>
              <span className="graph-action-spacer" />
              <button className="button button-secondary button-small" type="button" disabled={loading || stepIndex < 0} onClick={() => { setPlaying(false); setStepIndex((value) => Math.max(-1, value - 1)); }}>Back</button>
              <button className="button button-primary button-small" type="button" disabled={loading || !trace.length || noRoute} onClick={() => { if (stepIndex >= trace.length - 1) setStepIndex(-1); setPlaying((value) => !value); }}>{playing ? "Pause" : "Play"}</button>
              <button className="button button-secondary button-small" type="button" disabled={loading || !trace.length || noRoute} onClick={() => { setPlaying(false); setStepIndex((value) => Math.min(trace.length - 1, value + 1)); }}>Next</button>
            </div>
            <div className="graph-legend">
              <span><i className="legend-start" /> Start node</span>
              <span><i className="legend-explored" /> Explored</span>
              <span><i className="legend-frontier" /> Frontier</span>
              <span><i className="legend-optimal" /> Optimal path</span>
              <span><i className="legend-goal" /> Goal node</span>
            </div>
            <div className="route-graph-wrap">
              <svg className="route-graph" viewBox="0 0 900 250" role="img" aria-label={`Diagnostic service graph from Registration to ${goalState}`}>
                <defs>
                  <marker id="route-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L7,3 z" />
                  </marker>
                </defs>
                {!loading && comparison && <g transform={`translate(450 125) scale(${zoom}) translate(-450 -125)`}>
                  {edges.map((edge) => {
                    const from = nodes.find((node) => node.id === edge.source);
                    const to = nodes.find((node) => node.id === edge.target);
                    if (!from || !to) return null;
                    const onPath = optimalPath.has(edge.source) && optimalPath.has(edge.target);
                    const isCurrent = currentStep?.current_node === edge.source;
                    return (
                      <g key={`${edge.source}-${edge.target}`} className={onPath ? "route-edge route-edge-optimal" : isCurrent ? "route-edge route-edge-current" : "route-edge"}>
                        <line x1={from.x + NODE_WIDTH / 2} y1={from.y} x2={to.x - NODE_WIDTH / 2} y2={to.y} markerEnd="url(#route-arrow)" />
                        <text x={(from.x + to.x) / 2} y={from.y - 17}>{costLabel(edge.cost)}</text>
                      </g>
                    );
                  })}
                  {nodes.map((node) => {
                    const isStart = node.id === (comparison.problem_formulation?.initial_state ?? "Registration");
                    const isGoal = node.id === goalState;
                    const isCurrent = currentStep?.current_node === node.id;
                    const className = [
                      "route-node",
                      isStart && "route-node-start",
                      isGoal && "route-node-goal",
                      visited.has(node.id) && "route-node-explored",
                      frontier.has(node.id) && "route-node-frontier",
                      optimalPath.has(node.id) && "route-node-optimal",
                      isCurrent && "route-node-current",
                    ].filter(Boolean).join(" ");
                    return (
                      <g className={className} key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                        <rect x={-NODE_WIDTH / 2} y={-NODE_HEIGHT / 2} width={NODE_WIDTH} height={NODE_HEIGHT} rx="13" />
                        <text className="route-node-label" textAnchor="middle" y="-3">{node.label}</text>
                        <text className="route-node-hint" textAnchor="middle" y="18">{isStart ? "INITIAL STATE" : isGoal ? "GOAL STATE" : "SERVICE STAGE"}</text>
                      </g>
                    );
                  })}
                </g>}
              </svg>
              {loading && <div className="graph-loading-overlay">Running {algorithm} search…</div>}
              {!loading && !comparison && !error && <div className="graph-loading-overlay">Select a service to explore its route.</div>}
            </div>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            {noRoute && <div className="alert alert-warning" role="status">No valid route found from the initial state to {goalState}.</div>}
          </div>

          <aside className="graph-trace-panel" aria-live="polite">
            <span className="graph-kicker">{algorithm} EXECUTION</span>
            <h3>{currentStep ? `Step ${currentStep.step + 1}` : "Execution trace"}</h3>
            {currentStep ? <>
              <div className="trace-detail"><span>Current state</span><strong>{currentStep.current_node}</strong></div>
              <div className="trace-detail"><span>Action</span><strong>{currentStep.action.replaceAll("_", " ")}</strong></div>
              <div className="trace-detail"><span>Frontier</span><strong>{currentStep.frontier.length ? currentStep.frontier.join(", ") : "Empty"}</strong></div>
              <div className="trace-detail"><span>Visited</span><strong>{currentStep.visited.length ? currentStep.visited.join(", ") : "None"}</strong></div>
            </> : <p>{loading ? "Waiting for the selected search to finish." : error ? "Trace unavailable because the search failed." : noRoute ? "No active trace step: no valid route was found." : "No active trace step. Select Explore, Next, or Play."}</p>}
          </aside>
        </div>
      </section>

      <section className="panel comparison-panel">
        <div className="panel-heading">
          <div className="panel-eyebrow">SAME SERVICE · SAME TARGET</div>
          <h2>Algorithm Comparison</h2>
          <p>All algorithms are recomputed for the current service and goal state.</p>
        </div>
        <div className="table-scroll">
          <table className="data-table comparison-table">
            <thead><tr><th>Algorithm</th><th>Path</th><th>Total Cost</th><th>Nodes Expanded</th><th>Result</th></tr></thead>
            <tbody>
              {ALGORITHMS.map((name) => {
                const item = comparison?.results?.[name];
                const isWeightedOptimal = item?.total_cost !== null && item?.total_cost === minWeightedCost;
                return (
                  <tr key={name}>
                    <td><button className={`algorithm-chip ${algorithm === name ? "algorithm-chip-active" : ""}`} onClick={() => chooseAlgorithm(name)}>{name}</button></td>
                    <td>{item ? item.optimal_path.length ? item.optimal_path.join(" → ") : "No valid route found" : "—"}</td>
                    <td>{item?.total_cost == null ? "—" : costLabel(item.total_cost)}</td>
                    <td>{item?.nodes_expanded ?? "—"}</td>
                    <td>{!item ? "—" : item.optimal_path.length === 0 ? "Unreachable" : name === "BFS" ? (isWeightedOptimal ? "Fewest steps; lowest cost" : "Fewest steps") : "Weighted-cost optimal"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="algorithm-explanations">
          <p><strong>BFS</strong> explores by edge count, not weight.</p>
          <p><strong>UCS</strong> expands the lowest cumulative path cost g(n).</p>
          <p><strong>A*</strong> expands f(n) = g(n) + h(n), using the remaining-duration lower bound.</p>
        </div>
      </section>
    </div>
  );
}
