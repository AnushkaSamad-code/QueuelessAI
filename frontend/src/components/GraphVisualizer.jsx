import { useEffect, useMemo, useState } from "react";
import { compareRoute } from "../api";

const ALGORITHMS = ["BFS", "UCS", "A*"];
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
  const [algorithm, setAlgorithm] = useState("A*");
  const [comparison, setComparison] = useState(null);
  const [stepIndex, setStepIndex] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!services.length) {
      setServiceId("");
    } else if (!services.some((service) => service.service_id === serviceId)) {
      setServiceId(services[0].service_id);
    }
  }, [services, serviceId]);

  useEffect(() => {
    if (!serviceId) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    compareRoute(serviceId)
      .then((result) => {
        if (!cancelled) {
          setComparison(result);
          setStepIndex(-1);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Search comparison failed.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [serviceId]);

  const result = comparison?.results?.[algorithm];
  const trace = result?.trace_steps ?? [];
  const currentStep = stepIndex >= 0 ? trace[stepIndex] : null;
  const visited = useMemo(() => new Set(currentStep?.visited ?? []), [currentStep]);
  const frontier = useMemo(() => new Set(currentStep?.frontier ?? []), [currentStep]);
  const optimalPath = useMemo(() => new Set(result?.optimal_path ?? []), [result]);
  const nodes = comparison?.graph?.nodes ?? [];
  const edges = comparison?.graph?.edges ?? [];

  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setInterval(() => {
      setStepIndex((current) => Math.min(current + 1, trace.length - 1));
    }, 750);
    return () => window.clearInterval(timer);
  }, [playing, trace.length]);

  useEffect(() => {
    if (playing && stepIndex >= trace.length - 1) setPlaying(false);
  }, [playing, stepIndex, trace.length]);

  const minWeightedCost = Math.min(
    ...ALGORITHMS.map((name) => comparison?.results?.[name]?.total_cost ?? Number.POSITIVE_INFINITY),
  );

  return (
    <div className="academic-page">
      <section className="panel problem-formulation">
        <div className="panel-heading">
          <div className="panel-eyebrow">PROBLEM A · SERVICE ROUTE SEARCH</div>
          <h2>Problem Formulation</h2>
          <p>All three searches run on the same selected service route and stage-duration graph.</p>
        </div>
        <div className="formulation-grid">
          {[
            ["Initial State", comparison?.problem_formulation?.initial_state ?? "Registration"],
            ["Goal State", comparison?.problem_formulation?.goal_state ?? "Service Completed"],
            ["Actions", (comparison?.problem_formulation?.actions ?? ["Complete the current diagnostic stage"]).join("; ")],
            ["Transition Model", comparison?.problem_formulation?.transition_model ?? "Registration → Sample Collection → Report Collection → Service Completed"],
            ["Path Cost Function", comparison?.problem_formulation?.path_cost_function ?? "g(n) = cumulative estimated stage duration in minutes"],
            ["Heuristic Function h(n)", comparison?.problem_formulation?.heuristic_function ?? "h(n) = sum of minimum remaining stage durations"],
            ["Goal Test", comparison?.problem_formulation?.goal_test ?? "Current state equals Service Completed"],
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
            <p>Problem B counter assignment is evaluated separately from this stage graph.</p>
          </div>
          <div className="graph-controls">
            <label>
              <span>Service</span>
              <select value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
                {services.map((service) => (
                  <option value={service.service_id} key={service.service_id}>{service.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Trace algorithm</span>
              <select
                value={algorithm}
                onChange={(event) => {
                  setAlgorithm(event.target.value);
                  setStepIndex(-1);
                  setPlaying(false);
                }}
              >
                {ALGORITHMS.map((name) => <option value={name} key={name}>{name}</option>)}
              </select>
            </label>
            <button className="button button-secondary button-small" disabled={loading || !trace.length} onClick={() => setStepIndex((value) => Math.max(-1, value - 1))}>Back</button>
            <button
              className="button button-primary button-small"
              disabled={loading || !trace.length}
              onClick={() => {
                if (stepIndex >= trace.length - 1) setStepIndex(-1);
                setPlaying((value) => !value);
              }}
            >
              {playing ? "Pause" : "Play"}
            </button>
            <button className="button button-secondary button-small" disabled={loading || !trace.length} onClick={() => { setPlaying(false); setStepIndex((value) => Math.min(trace.length - 1, value + 1)); }}>Next</button>
          </div>
        </div>

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="graph-legend">
          <span><i className="legend-start" /> Start node</span>
          <span><i className="legend-explored" /> Explored</span>
          <span><i className="legend-frontier" /> Frontier</span>
          <span><i className="legend-optimal" /> Optimal path</span>
          <span><i className="legend-goal" /> Goal node</span>
        </div>
        <div className="route-graph-wrap">
          <svg className="route-graph" viewBox="0 0 900 250" role="img" aria-label="Four-stage diagnostic service workflow graph">
            <defs>
              <marker id="route-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L7,3 z" />
              </marker>
            </defs>
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
            {nodes.map((node, index) => {
              const isStart = index === 0;
              const isGoal = index === nodes.length - 1;
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
          </svg>
        </div>
        <div className="route-trace-status">
          {loading ? "Running BFS, UCS, and A*…" : currentStep ? `${algorithm}: ${currentStep.action.replaceAll("_", " ")} · ${currentStep.current_node}` : "Choose Next or Play to inspect explored nodes and the frontier."}
        </div>
      </section>

      <section className="panel comparison-panel">
        <div className="panel-heading">
          <div className="panel-eyebrow">SAME ROUTE · SIDE-BY-SIDE</div>
          <h2>Algorithm Comparison</h2>
          <p>Optimality is assessed against the weighted stage-duration cost.</p>
        </div>
        <div className="table-scroll">
          <table className="data-table comparison-table">
            <thead><tr><th>Algorithm</th><th>Optimal Path</th><th>Total Cost</th><th>Nodes Expanded</th><th>Optimality</th></tr></thead>
            <tbody>
              {ALGORITHMS.map((name) => {
                const item = comparison?.results?.[name];
                const isWeightedOptimal = item?.total_cost === minWeightedCost;
                return (
                  <tr key={name}>
                    <td><button className={`algorithm-chip ${algorithm === name ? "algorithm-chip-active" : ""}`} onClick={() => { setAlgorithm(name); setStepIndex(-1); setPlaying(false); }}>{name}</button></td>
                    <td>{item?.optimal_path?.join(" → ") ?? "—"}</td>
                    <td>{item?.total_cost == null ? "—" : costLabel(item.total_cost)}</td>
                    <td>{item?.nodes_expanded ?? "—"}</td>
                    <td>{item ? name === "BFS" ? (isWeightedOptimal ? "Shortest steps + lowest cost" : "Shortest steps") : "Weighted-cost optimal" : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
