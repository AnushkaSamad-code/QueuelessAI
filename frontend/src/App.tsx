import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  API_URL,
  advanceCounter,
  bookToken,
  findToken,
  getInspector,
  getState,
} from "./api";
import Icon from "./Icons";
import type { IconName } from "./Icons";
import type {
  BookResponse,
  Counter,
  InspectorSnapshot,
  PortalView,
  PriorityLevel,
  Service,
  StateSnapshot,
  Theme,
  Token,
  TokenResponse,
} from "./types";

const services: Service[] = [
  {
    id: "SVC-001",
    name: "Complete Blood Count",
    category: "Hematology",
    duration: "16 min",
    description: "CBC",
  },
  {
    id: "SVC-002",
    name: "Lipid Profile",
    category: "Clinical chemistry",
    duration: "19 min",
    description: "Cholesterol and triglycerides",
  },
  {
    id: "SVC-003",
    name: "HbA1c Diabetes Panel",
    category: "Diabetes diagnostics",
    duration: "14 min",
    description: "Three-month average glucose",
  },
  {
    id: "SVC-004",
    name: "Thyroid Function (TSH)",
    category: "Endocrinology",
    duration: "13 min",
    description: "Thyroid-stimulating hormone",
  },
  {
    id: "SVC-005",
    name: "Liver Function Test",
    category: "Hepatic panel",
    duration: "18 min",
    description: "LFT",
  },
  {
    id: "SVC-006",
    name: "Renal Function Test",
    category: "Renal diagnostics",
    duration: "18 min",
    description: "RFT",
  },
  {
    id: "SVC-007",
    name: "Vitamin D3 Assay",
    category: "Nutritional testing",
    duration: "15 min",
    description: "Vitamin D level",
  },
  {
    id: "SVC-008",
    name: "Diagnostic Report Pickup",
    category: "Report services",
    duration: "10 min",
    description: "Collect a completed report",
  },
];

const navigation: Array<{ id: PortalView; label: string; icon: IconName }> = [
  { id: "booking", label: "Customer booking", icon: "ticket" },
  { id: "staff", label: "Counter console", icon: "users" },
  { id: "inspector", label: "Data inspector", icon: "layers" },
];

const serviceById = new Map<string, Service>(
  services.map((service) => [service.id, service] as const),
);

function readTheme(): Theme {
  return localStorage.getItem("queueless-theme") === "light" ? "light" : "dark";
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

function serviceName(serviceId: string): string {
  return serviceById.get(serviceId)?.name ?? serviceId;
}

function counterLabel(counterId: string | null): string {
  if (!counterId) return "Not assigned";
  return `Counter ${counterId}`;
}

function formatPathNode(node: string): string {
  if (node === "waiting_queue") return "Waiting queue";
  if (node === "service_completion") return "Service complete";
  const [counter, stage] = node.split(".");
  if (!stage) return node;
  const stageName = stage.replaceAll("_", " ");
  return `${counter.replace("_", " ")} · ${stageName}`;
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    S3_WAITING: "Waiting",
    S4_COUNTER_ASSIGNED: "Assigned",
    S5_IN_PROGRESS: "In progress",
    S6_COMPLETED: "Completed",
  };
  return labels[status] ?? status.replaceAll("_", " ").toLowerCase();
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function App() {
  const [view, setView] = useState<PortalView>("booking");
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const [snapshot, setSnapshot] = useState<StateSnapshot | null>(null);
  const [inspector, setInspector] = useState<InspectorSnapshot | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [serviceId, setServiceId] = useState(services[0].id);
  const [priority, setPriority] = useState<PriorityLevel>("STANDARD");
  const [bookingResult, setBookingResult] = useState<BookResponse | null>(null);
  const [tokenQuery, setTokenQuery] = useState("");
  const [tokenResult, setTokenResult] = useState<TokenResponse | null>(null);
  const [tokenError, setTokenError] = useState("");
  const [tokenSearchBusy, setTokenSearchBusy] = useState(false);

  const refreshData = useCallback(async () => {
    try {
      const [nextSnapshot, nextInspector] = await Promise.all([
        getState(),
        getInspector(),
      ]);
      setSnapshot(nextSnapshot);
      setInspector(nextInspector);
      setApiError("");
    } catch (error) {
      setApiError(errorText(error));
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("queueless-theme", theme);
  }, [theme]);

  useEffect(() => {
    void refreshData();
    const interval = window.setInterval(() => void refreshData(), 7000);
    return () => window.clearInterval(interval);
  }, [refreshData]);

  useEffect(() => {
    if (!menuOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [menuOpen]);

  const trackedTokenId = tokenResult?.token.token_id;

  useEffect(() => {
    if (!trackedTokenId) return;
    let cancelled = false;
    const interval = window.setInterval(async () => {
      try {
        const latest = await findToken(trackedTokenId);
        if (!cancelled) {
          setTokenResult(latest);
          setTokenError("");
        }
      } catch (error) {
        if (!cancelled) setTokenError(errorText(error));
      }
    }, 7000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [trackedTokenId]);

  const selectedService = useMemo(
    () => serviceById.get(serviceId) ?? services[0],
    [serviceId],
  );

  function navigate(nextView: PortalView) {
    setView(nextView);
    setMenuOpen(false);
    setNotice("");
  }

  async function submitBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setApiError("");
    setBusyAction("booking");
    try {
      const result = await bookToken({
        customer_name: customerName.trim(),
        service_id: serviceId,
        priority_level: priority,
      });
      setBookingResult(result);
      setTokenQuery(result.token.token_id);
      setTokenResult({
        token: result.token,
        optimal_path: result.recommendation.optimal_path,
        eta_min: result.recommendation.total_cost,
      });
      setCustomerName("");
      setNotice(`Appointment confirmed. Your token is ${result.token.token_id}.`);
      await refreshData();
    } catch (error) {
      setApiError(errorText(error));
    } finally {
      setBusyAction("");
    }
  }

  async function submitTokenSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = tokenQuery.trim().toUpperCase();
    if (!normalized) {
      setTokenError("Enter a token ID to search.");
      return;
    }
    setTokenSearchBusy(true);
    setTokenError("");
    setTokenResult(null);
    setBookingResult(null);
    try {
      setTokenResult(await findToken(normalized));
    } catch (error) {
      setTokenError(errorText(error));
    } finally {
      setTokenSearchBusy(false);
    }
  }

  async function handleCounterAction(counter: Counter) {
    setNotice("");
    setApiError("");
    setBusyAction(counter.counter_id);
    try {
      const response = await advanceCounter(counter.counter_id);
      const token = response.token;
      const actionLabel =
        token.status === "S5_IN_PROGRESS" ? "called to the counter" : "completed";
      setNotice(`${token.token_id} ${actionLabel}.`);
      await refreshData();
    } catch (error) {
      setApiError(errorText(error));
    } finally {
      setBusyAction("");
    }
  }

  const pageTitle =
    navigation.find((item) => item.id === view)?.label ?? "Customer booking";

  return (
    <div className="app-shell">
      {menuOpen && (
        <button
          aria-label="Close navigation"
          className="mobile-backdrop"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="brand-copy">
            <strong>QueueLess</strong>
            <span>DIAGNOSTIC SYSTEMS</span>
          </div>
          <button
            className="icon-button sidebar-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar">QL</div>
          <div className="workspace-name">
            <strong>Central Laboratory</strong>
            <span>Workspace</span>
          </div>
          <Icon name="chevron-down" size={15} className="muted-icon" />
        </div>

        <div className="nav-section-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              className={`nav-item ${view === item.id ? "nav-item-active" : ""}`}
              key={item.id}
              onClick={() => navigate(item.id)}
              aria-current={view === item.id ? "page" : undefined}
            >
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
              {item.id === "staff" && snapshot && (
                <span className="nav-count">
                  {snapshot.stats.in_progress_count}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span className={`status-dot ${snapshot && !apiError ? "status-dot-live" : ""}`} />
            <span>{snapshot && !apiError ? "API connected" : "API unavailable"}</span>
            <button
              className="text-icon-button"
              onClick={() => void refreshData()}
              aria-label="Refresh API status"
              title="Refresh data"
            >
              <Icon name="refresh" size={15} />
            </button>
          </div>
          <div className="sidebar-footer">
            <button
              className="nav-item appearance-button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              <Icon name={theme === "dark" ? "sun" : "moon"} size={17} />
              <span>{theme === "dark" ? "Light appearance" : "Dark appearance"}</span>
            </button>
            <div className="profile-row">
              <div className="profile-avatar">CL</div>
              <div className="profile-copy">
                <strong>Clinic operator</strong>
                <span>Staff account</span>
              </div>
              <Icon name="more" size={17} className="muted-icon" />
            </div>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button
            className="icon-button mobile-menu-button"
            onClick={() => setMenuOpen(true)}
            aria-label="Open navigation"
          >
            <Icon name="menu" />
          </button>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="breadcrumb-separator">/</span>
            <strong>{pageTitle}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`connection-pill ${snapshot && !apiError ? "connection-live" : ""}`}>
              <span className="status-dot" />
              {snapshot && !apiError ? "Connected" : "Connecting"}
            </span>
            <button
              className="icon-button"
              onClick={() => void refreshData()}
              aria-label="Refresh dashboard"
              title="Refresh dashboard"
            >
              <Icon name="refresh" size={16} />
            </button>
            <button
              className="avatar-button"
              aria-label="Clinic operator account"
              title="Clinic operator"
            >
              CL
            </button>
          </div>
        </header>

        <main className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">QUEUELESS AI / OPERATIONS</div>
              <h1>{pageTitle}</h1>
              <p>
                {view === "booking" &&
                  "Appointments, queue status, and token tracking in one place."}
                {view === "staff" &&
                  "Coordinate active service counters and move the queue forward."}
                {view === "inspector" &&
                  "Inspect the live data structures that power each queue decision."}
              </p>
            </div>
            <div className="heading-meta">
              <span className="live-indicator">
                <span className="status-dot status-dot-live" />
                LIVE DATA
              </span>
              <span className="meta-divider" />
              <span>Auto-refresh · 7 sec</span>
            </div>
          </div>

          {apiError && (
            <div className="alert alert-error" role="alert">
              <Icon name="warning" size={17} />
              <div>
                <strong>Unable to sync with the backend</strong>
                <span>{apiError}</span>
              </div>
              <button className="button button-secondary button-small" onClick={() => void refreshData()}>
                Retry
              </button>
            </div>
          )}
          {notice && (
            <div className="alert alert-success" role="status">
              <Icon name="check" size={17} />
              <span>{notice}</span>
              <button
                className="alert-dismiss"
                aria-label="Dismiss message"
                onClick={() => setNotice("")}
              >
                <Icon name="close" size={15} />
              </button>
            </div>
          )}

          {view === "booking" && (
            <BookingView
              snapshot={snapshot}
              loading={initialLoading}
              customerName={customerName}
              onCustomerNameChange={setCustomerName}
              serviceId={serviceId}
              onServiceChange={setServiceId}
              priority={priority}
              onPriorityChange={setPriority}
              selectedService={selectedService}
              onBook={submitBooking}
              bookingBusy={busyAction === "booking"}
              bookingResult={bookingResult}
              tokenQuery={tokenQuery}
              onTokenQueryChange={setTokenQuery}
              tokenResult={tokenResult}
              tokenError={tokenError}
              tokenSearchBusy={tokenSearchBusy}
              onTokenSearch={submitTokenSearch}
            />
          )}
          {view === "staff" && (
            <StaffView
              snapshot={snapshot}
              loading={initialLoading}
              busyAction={busyAction}
              onCounterAction={handleCounterAction}
            />
          )}
          {view === "inspector" && (
            <InspectorView snapshot={inspector} loading={initialLoading} />
          )}
          <footer className="page-footer">
            <span>QueueLess AI</span>
            <span>Diagnostic operations platform</span>
            <span className="footer-version">API · {API_URL}</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

interface BookingViewProps {
  snapshot: StateSnapshot | null;
  loading: boolean;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  serviceId: string;
  onServiceChange: (value: string) => void;
  priority: PriorityLevel;
  onPriorityChange: (value: PriorityLevel) => void;
  selectedService: Service;
  onBook: (event: FormEvent<HTMLFormElement>) => void;
  bookingBusy: boolean;
  bookingResult: BookResponse | null;
  tokenQuery: string;
  onTokenQueryChange: (value: string) => void;
  tokenResult: TokenResponse | null;
  tokenError: string;
  tokenSearchBusy: boolean;
  onTokenSearch: (event: FormEvent<HTMLFormElement>) => void;
}

function BookingView({
  snapshot,
  loading,
  customerName,
  onCustomerNameChange,
  serviceId,
  onServiceChange,
  priority,
  onPriorityChange,
  selectedService,
  onBook,
  bookingBusy,
  bookingResult,
  tokenQuery,
  onTokenQueryChange,
  tokenResult,
  tokenError,
  tokenSearchBusy,
  onTokenSearch,
}: BookingViewProps) {
  const stats = snapshot?.stats;

  return (
    <>
      <section className="metric-grid" aria-label="Queue summary">
        {loading || !stats ? (
          <>
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
          </>
        ) : (
          <>
            <MetricCard
              label="Active tokens"
              value={stats.active_token_count}
              note="Across all service counters"
              icon="ticket"
            />
            <MetricCard
              label="Waiting"
              value={stats.waiting_count}
              note="Assigned and awaiting service"
              icon="clock"
            />
            <MetricCard
              label="In service"
              value={stats.in_progress_count}
              note="Currently being processed"
              icon="activity"
            />
            <MetricCard
              label="Average wait"
              value={`${Math.round(stats.average_eta_min)} min`}
              note="Estimated end-to-end"
              icon="bars"
            />
          </>
        )}
      </section>

      <div className="booking-layout">
        <section className="panel booking-panel">
          <PanelHeading
            eyebrow="NEW APPOINTMENT"
            title="Book a diagnostic service"
            detail="Create a queue token and see the recommended service route."
            icon="beaker"
          />
          <form className="booking-form" onSubmit={onBook}>
            <label className="field-label" htmlFor="customer-name">
              Patient name <span className="required-mark">*</span>
            </label>
            <input
              id="customer-name"
              className="text-input"
              value={customerName}
              onChange={(event) => onCustomerNameChange(event.target.value)}
              placeholder="Enter patient name"
              autoComplete="name"
              required
              minLength={1}
            />

            <div className="field-label-row">
              <label className="field-label" htmlFor="service-select">
                Diagnostic service
              </label>
              <span className="field-hint">8 services available</span>
            </div>
            <div className="select-wrap">
              <select
                id="service-select"
                className="text-input select-input"
                value={serviceId}
                onChange={(event) => onServiceChange(event.target.value)}
              >
                {services.map((service) => (
                  <option value={service.id} key={service.id}>
                    {service.name} · {service.description}
                  </option>
                ))}
              </select>
              <Icon name="chevron-down" size={16} />
            </div>
            <div className="service-detail">
              <div className="service-icon">
                <Icon name="flask" size={17} />
              </div>
              <div>
                <strong>{selectedService.category}</strong>
                <span>Typical service time · {selectedService.duration}</span>
              </div>
              <span className="service-code">{selectedService.id}</span>
            </div>

            <label className="field-label" htmlFor="priority-select">
              Priority level
            </label>
            <div className="select-wrap">
              <select
                id="priority-select"
                className="text-input select-input"
                value={priority}
                onChange={(event) => {
                  const nextPriority = event.target.value;
                  if (
                    nextPriority === "STANDARD" ||
                    nextPriority === "APPOINTMENT" ||
                    nextPriority === "PRIORITY"
                  ) {
                    onPriorityChange(nextPriority);
                  }
                }}
              >
                <option value="STANDARD">Standard</option>
                <option value="APPOINTMENT">Appointment</option>
                <option value="PRIORITY">Priority</option>
              </select>
              <Icon name="chevron-down" size={16} />
            </div>

            <button
              className="button button-primary booking-submit"
              type="submit"
              disabled={bookingBusy}
            >
              {bookingBusy ? (
                <>
                  <span className="button-spinner" />
                  Creating token…
                </>
              ) : (
                <>
                  Confirm appointment
                  <Icon name="arrow-right" size={16} />
                </>
              )}
            </button>
            <p className="form-footnote">
              Token assignment and counter routing are handled by the live queue.
            </p>
          </form>
        </section>

        <section className="panel tracker-panel">
          <PanelHeading
            eyebrow="TOKEN TRACKER"
            title="Find your place in line"
            detail="Search any token ID to see its current status and route."
            icon="search"
          />
          <form className="token-search-form" onSubmit={onTokenSearch}>
            <div className="search-input-wrap">
              <Icon name="search" size={17} />
              <input
                className="search-input"
                value={tokenQuery}
                onChange={(event) => onTokenQueryChange(event.target.value)}
                placeholder="Search token, e.g. Q101"
                aria-label="Token ID"
                autoCapitalize="characters"
              />
              <button
                className="button button-secondary button-small"
                type="submit"
                disabled={tokenSearchBusy}
              >
                {tokenSearchBusy ? "Searching…" : "Search"}
              </button>
            </div>
          </form>
          {tokenError && (
            <div className="inline-error" role="alert">
              <Icon name="warning" size={15} />
              {tokenError}
            </div>
          )}
          {tokenResult ? (
            <TokenResultCard result={tokenResult} />
          ) : bookingResult ? (
            <TokenResultCard
              result={{
                token: bookingResult.token,
                optimal_path: bookingResult.recommendation.optimal_path,
                eta_min: bookingResult.recommendation.total_cost,
              }}
              fresh
            />
          ) : (
            <div className="tracker-empty">
              <div className="empty-icon">
                <Icon name="ticket" size={20} />
              </div>
              <strong>Your token details will appear here</strong>
              <span>
                Search an existing token or book a service to begin tracking.
              </span>
              <div className="example-tokens">
                <span>Try a sample</span>
                {["Q101", "Q105", "Q110"].map((id) => (
                  <button
                    key={id}
                    className="token-link"
                    onClick={() => onTokenQueryChange(id)}
                    type="button"
                  >
                    {id}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="tracker-foot">
            <span>
              <Icon name="activity" size={14} />
              Updates automatically
            </span>
            <span>Token range · Q101–Q999</span>
          </div>
        </section>
      </div>

      <section className="panel recent-panel">
        <div className="panel-heading panel-heading-row">
          <div>
            <div className="panel-eyebrow">CURRENT QUEUE</div>
            <h2>Recent tokens</h2>
            <p>Latest active appointments across the service floor.</p>
          </div>
          <span className="subtle-count">
            {snapshot?.active_tokens.length ?? "—"} active
          </span>
        </div>
        {loading || !snapshot ? (
          <TableSkeleton />
        ) : (
          <TokenTable tokens={snapshot.active_tokens.slice(-6).reverse()} />
        )}
      </section>
    </>
  );
}

function TokenResultCard({
  result,
  fresh = false,
}: {
  result: TokenResponse;
  fresh?: boolean;
}) {
  const { token } = result;
  return (
    <div className="token-result">
      <div className="result-topline">
        <span className="result-label">{fresh ? "APPOINTMENT CONFIRMED" : "TOKEN FOUND"}</span>
        <StatusBadge status={token.status} />
      </div>
      <div className="result-main">
        <div>
          <span className="token-caption">QUEUE TOKEN</span>
          <strong className="large-token">{token.token_id}</strong>
        </div>
        <div className="result-eta">
          <span>Estimated route</span>
          <strong>{Math.round(result.eta_min)} min</strong>
        </div>
      </div>
      <div className="result-person">
        <span className="person-initials">{token.customer_name.slice(0, 1).toUpperCase()}</span>
        <div>
          <strong>{token.customer_name}</strong>
          <span>{serviceName(token.service_id)}</span>
        </div>
        <span className="counter-chip">{counterLabel(token.counter_id)}</span>
      </div>
      <PathDisplay path={result.optimal_path} />
      <div className="result-meta">
        <span>Priority · {token.priority_level.toLowerCase()}</span>
        <span>Updated {formatTime(token.updated_at)}</span>
      </div>
    </div>
  );
}

function PathDisplay({ path }: { path: string[] }) {
  if (!path.length) return null;
  return (
    <div className="path-display">
      <div className="path-heading">
        <span>A* RECOMMENDED ROUTE</span>
        <span>{Math.max(path.length - 1, 0)} stages</span>
      </div>
      <div className="path-steps">
        {path.map((node, index) => (
          <div className="path-step" key={`${node}-${index}`}>
            <span className={`path-node ${index === 0 || index === path.length - 1 ? "path-node-edge" : ""}`}>
              {index === path.length - 1 ? <Icon name="check" size={12} /> : index + 1}
            </span>
            <span>{formatPathNode(node)}</span>
            {index < path.length - 1 && <span className="path-connector" />}
          </div>
        ))}
      </div>
    </div>
  );
}

function StaffView({
  snapshot,
  loading,
  busyAction,
  onCounterAction,
}: {
  snapshot: StateSnapshot | null;
  loading: boolean;
  busyAction: string;
  onCounterAction: (counter: Counter) => void;
}) {
  return (
    <>
      <section className="metric-grid staff-metrics">
        {loading || !snapshot ? (
          <>
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
          </>
        ) : (
          <>
            <MetricCard label="Open counters" value={`${snapshot.counters.filter((counter) => counter.status === "OPEN").length} / 3`} note="Available for service" icon="users" />
            <MetricCard label="Waiting in line" value={snapshot.stats.waiting_count} note="Across all counters" icon="clock" />
            <MetricCard label="In progress" value={snapshot.stats.in_progress_count} note="Active service sessions" icon="activity" />
            <MetricCard label="Completed today" value={snapshot.stats.completed_count} note="Tokens served" icon="check" />
          </>
        )}
      </section>
      <div className="section-title-row">
        <div>
          <div className="panel-eyebrow">SERVICE FLOOR</div>
          <h2>Counter board</h2>
          <p>Each counter shows its active token and linked-list queue.</p>
        </div>
        <span className="live-indicator">
          <span className="status-dot status-dot-live" />
          LIVE QUEUES
        </span>
      </div>
      <div className="counter-grid">
        {loading || !snapshot
          ? [1, 2, 3].map((item) => <CounterSkeleton key={item} />)
          : snapshot.counters.map((counter) => {
              const waiting = snapshot.queues[counter.counter_id] ?? [];
              const activeToken = counter.current_token_id
                ? snapshot.active_tokens.find(
                    (token) => token.token_id === counter.current_token_id,
                  )
                : undefined;
              const busy = busyAction === counter.counter_id;
              const canAdvance = Boolean(activeToken);
              const disabled =
                counter.status !== "OPEN" || (!canAdvance && waiting.length === 0) || busy;

              return (
                <section className="panel counter-card" key={counter.counter_id}>
                  <div className="counter-card-heading">
                    <div className="counter-number">0{counter.counter_id}</div>
                    <div className="counter-card-title">
                      <strong>{counter.name}</strong>
                      <span>
                        <span className={`status-dot ${counter.status === "OPEN" ? "status-dot-live" : ""}`} />
                        {counter.status === "OPEN" ? "Open" : "Closed"}
                      </span>
                    </div>
                    <span className="counter-queue-count">{waiting.length} waiting</span>
                  </div>
                  <div className="current-service">
                    <div className="current-label">
                      <span className="panel-eyebrow">NOW SERVING</span>
                      <Icon name="more" size={16} className="muted-icon" />
                    </div>
                    {activeToken ? (
                      <div className="active-token-card">
                        <div>
                          <span className="token-caption">CURRENT TOKEN</span>
                          <strong>{activeToken.token_id}</strong>
                        </div>
                        <div>
                          <strong>{activeToken.customer_name}</strong>
                          <span>{serviceName(activeToken.service_id)}</span>
                        </div>
                        <StatusBadge status={activeToken.status} />
                      </div>
                    ) : (
                      <div className="no-active-token">
                        <span className="empty-dot" />
                        <span>No active service</span>
                      </div>
                    )}
                  </div>
                  <div className="counter-queue">
                    <div className="queue-heading">
                      <span>UP NEXT</span>
                      <span>{waiting.length} {waiting.length === 1 ? "patient" : "patients"}</span>
                    </div>
                    {waiting.length ? (
                      <div className="queue-list">
                        {waiting.slice(0, 4).map((token, index) => (
                          <div className="queue-row" key={token.token_id}>
                            <span className="queue-position">{String(index + 1).padStart(2, "0")}</span>
                            <span className="queue-patient">
                              <strong>{token.token_id}</strong>
                              <span>{token.customer_name}</span>
                            </span>
                            <span className={`priority-mark priority-${token.priority_level.toLowerCase()}`}>
                              {token.priority_level === "PRIORITY" ? "PRIORITY" : token.priority_level === "APPOINTMENT" ? "APPT" : "STD"}
                            </span>
                          </div>
                        ))}
                        {waiting.length > 4 && (
                          <span className="queue-more">+{waiting.length - 4} more in queue</span>
                        )}
                      </div>
                    ) : (
                      <div className="queue-empty">Queue is clear</div>
                    )}
                  </div>
                  <button
                    className={`button ${canAdvance ? "button-secondary" : "button-primary"} counter-action`}
                    onClick={() => onCounterAction(counter)}
                    disabled={disabled}
                  >
                    {busy ? (
                      <>
                        <span className="button-spinner" />
                        Updating queue…
                      </>
                    ) : canAdvance ? (
                      <>
                        Advance stage
                        <Icon name="arrow-right" size={16} />
                      </>
                    ) : (
                      <>
                        Call next
                        <Icon name="arrow-right" size={16} />
                      </>
                    )}
                  </button>
                  <p className="counter-action-hint">
                    {canAdvance
                      ? "Advance the active token to completion."
                      : "Call the next scheduled token to this counter."}
                  </p>
                </section>
              );
            })}
      </div>
      <div className="notice-strip">
        <Icon name="activity" size={16} />
        <span>
          Counter actions follow the API lifecycle: assigned <b>S4</b> → in progress <b>S5</b> → completed <b>S6</b>.
        </span>
      </div>
    </>
  );
}

function InspectorView({
  snapshot,
  loading,
}: {
  snapshot: InspectorSnapshot | null;
  loading: boolean;
}) {
  if (loading || !snapshot) {
    return (
      <div className="inspector-grid">
        <InspectorSkeleton wide />
        <InspectorSkeleton />
        <InspectorSkeleton wide />
        <InspectorSkeleton wide />
      </div>
    );
  }

  const heap = [...snapshot.priority_queue].sort((a, b) => a.index - b.index);
  const heapByIndex = new Map(heap.map((entry) => [entry.index, entry] as const));

  return (
    <>
      <section className="metric-grid inspector-metrics">
        <MetricCard label="Array occupancy" value={`${snapshot.token_array.size} / ${snapshot.token_array.capacity}`} note="TokenArray slots" icon="database" />
        <MetricCard label="Queue heap" value={heap.length} note="Scheduled tokens" icon="bars" />
        <MetricCard label="Linked queues" value={Object.keys(snapshot.counter_linked_lists).length} note="Service counters" icon="layers" />
        <MetricCard label="BST nodes" value={snapshot.bst.inorder.length} note="Indexed token records" icon="command" />
      </section>

      <div className="inspector-grid">
        <section className="panel inspector-card inspector-wide">
          <PanelHeading
            eyebrow="CONTIGUOUS STORAGE"
            title="TokenArray"
            detail={`${snapshot.token_array.size} occupied slots · ${snapshot.token_array.capacity} total capacity`}
            icon="database"
          />
          <div className="slot-grid">
            {snapshot.token_array.slots.map((token, index) => (
              <div className={`array-slot ${token ? "array-slot-filled" : ""}`} key={index}>
                <span className="slot-index">{String(index).padStart(2, "0")}</span>
                <span className="slot-value">{token ? token.token_id : "—"}</span>
              </div>
            ))}
          </div>
          <div className="structure-caption">
            <span><span className="legend-square legend-filled" /> Occupied</span>
            <span><span className="legend-square" /> Empty slot</span>
            <span className="structure-code">O(1) index · O(n) insertion</span>
          </div>
        </section>

        <section className="panel inspector-card">
          <PanelHeading
            eyebrow="MIN-HEAP"
            title="SchedulingPriorityQueue"
            detail="Aging-adjusted priority order"
            icon="bars"
          />
          {heap.length ? (
            <div className="heap-tree" aria-label="Min heap tree">
              <HeapTreeNode entry={heap[0]} entries={heapByIndex} />
            </div>
          ) : (
            <div className="empty-state-compact">No tokens scheduled.</div>
          )}
          <div className="heap-array">
            <span className="array-label">ARRAY VIEW</span>
            <div className="heap-array-row">
              {heap.slice(0, 12).map((entry) => (
                <span className="heap-array-cell" key={entry.index} title={`Index ${entry.index} · priority ${entry.effective_priority}`}>
                  <small>{entry.index}</small>
                  {entry.token_id}
                </span>
              ))}
              {heap.length > 12 && <span className="heap-array-overflow">+{heap.length - 12}</span>}
            </div>
          </div>
        </section>

        <section className="panel inspector-card inspector-wide">
          <PanelHeading
            eyebrow="SINGLY LINKED QUEUES"
            title="ServiceLinkedList"
            detail="Waiting tokens grouped by assigned counter"
            icon="layers"
          />
          <div className="linked-lists">
            {Object.entries(snapshot.counter_linked_lists).map(([counterId, tokens]) => (
              <div className="linked-row" key={counterId}>
                <div className="linked-counter">Counter {counterId}</div>
                <div className="linked-chain">
                  {tokens.length ? (
                    <>
                      {tokens.slice(0, 7).map((token) => (
                        <div className="linked-node-wrap" key={token.token_id}>
                          <div className="linked-node">
                            <strong>{token.token_id}</strong>
                            <span>{token.customer_name.split(" ")[0]}</span>
                          </div>
                          <Icon name="arrow-right" size={14} />
                        </div>
                      ))}
                      {tokens.length > 7 && <span className="linked-overflow">+{tokens.length - 7}</span>}
                      <span className="linked-null">NULL</span>
                    </>
                  ) : (
                    <span className="empty-state-compact">Empty list · head = NULL</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel inspector-card inspector-wide">
          <PanelHeading
            eyebrow="BINARY SEARCH TREE"
            title="TokenBST traversals"
            detail="Live token index traversal orders"
            icon="command"
          />
          <div className="traversal-grid">
            {([
              ["Inorder", snapshot.bst.inorder],
              ["Preorder", snapshot.bst.preorder],
              ["Postorder", snapshot.bst.postorder],
            ] as const).map(([name, tokens]) => (
              <div className="traversal-card" key={name}>
                <div className="traversal-heading">
                  <strong>{name}</strong>
                  <span>{tokens.length} nodes</span>
                </div>
                <div className="traversal-values">
                  {tokens.length ? (
                    tokens.map((token, index) => (
                      <span className="traversal-token" key={`${name}-${token.token_id}-${index}`}>
                        {token.token_id}
                      </span>
                    ))
                  ) : (
                    <span className="empty-state-compact">No indexed tokens</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

function HeapTreeNode({
  entry,
  entries,
}: {
  entry: InspectorSnapshot["priority_queue"][number];
  entries: Map<number, InspectorSnapshot["priority_queue"][number]>;
}) {
  const left = entries.get(entry.index * 2 + 1);
  const right = entries.get(entry.index * 2 + 2);
  const hasChildren = Boolean(left || right);

  return (
    <div className="heap-tree-node">
      <div className={`heap-node ${hasChildren ? "heap-parent" : ""}`}>
        <strong>{entry.token_id}</strong>
        <span>priority {entry.effective_priority}</span>
        <small>index {entry.index}</small>
      </div>
      {hasChildren && (
        <div className="heap-children">
          {left ? (
            <HeapTreeNode entry={left} entries={entries} />
          ) : (
            <span className="heap-child-empty" />
          )}
          {right ? (
            <HeapTreeNode entry={right} entries={entries} />
          ) : (
            <span className="heap-child-empty" />
          )}
        </div>
      )}
    </div>
  );
}

function TokenTable({ tokens }: { tokens: Token[] }) {
  if (!tokens.length) {
    return <div className="empty-table">No active tokens in the queue.</div>;
  }
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Token</th>
            <th>Patient</th>
            <th>Service</th>
            <th>Counter</th>
            <th>Status</th>
            <th>ETA</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => (
            <tr key={token.token_id}>
              <td><span className="table-token">{token.token_id}</span></td>
              <td>
                <div className="table-person">
                  <span className="person-initials">{token.customer_name.slice(0, 1).toUpperCase()}</span>
                  <span>{token.customer_name}</span>
                </div>
              </td>
              <td>{serviceName(token.service_id)}</td>
              <td>{counterLabel(token.counter_id)}</td>
              <td><StatusBadge status={token.status} /></td>
              <td>{Math.round(token.eta_min)} min</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricCard({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string | number;
  note: string;
  icon: IconName;
}) {
  return (
    <div className="metric-card">
      <div className="metric-card-top">
        <span>{label}</span>
        <span className="metric-icon"><Icon name={icon} size={16} /></span>
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-note">{note}</span>
    </div>
  );
}

function MetricSkeleton() {
  return (
    <div className="metric-card skeleton-card" aria-hidden="true">
      <span className="skeleton skeleton-label" />
      <span className="skeleton skeleton-value" />
      <span className="skeleton skeleton-note" />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="table-scroll" aria-label="Loading token table">
      <table className="data-table">
        <thead><tr>{["Token", "Patient", "Service", "Counter", "Status", "ETA"].map((label) => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>
          {[1, 2, 3, 4].map((row) => (
            <tr key={row}>
              {[1, 2, 3, 4, 5, 6].map((cell) => (
                <td key={cell}><span className="skeleton skeleton-table-cell" /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CounterSkeleton() {
  return (
    <section className="panel counter-card skeleton-counter" aria-hidden="true">
      <span className="skeleton skeleton-label" />
      <span className="skeleton skeleton-current" />
      <span className="skeleton skeleton-line" />
      <span className="skeleton skeleton-line" />
      <span className="skeleton skeleton-action" />
    </section>
  );
}

function InspectorSkeleton({ wide = false }: { wide?: boolean }) {
  return (
    <section className={`panel inspector-card skeleton-inspector ${wide ? "inspector-wide" : ""}`} aria-hidden="true">
      <span className="skeleton skeleton-label" />
      <span className="skeleton skeleton-heading" />
      <span className="skeleton skeleton-inspector-body" />
    </section>
  );
}

function PanelHeading({
  eyebrow,
  title,
  detail,
  icon,
}: {
  eyebrow: string;
  title: string;
  detail: string;
  icon: IconName;
}) {
  return (
    <div className="panel-heading">
      <div className="panel-heading-icon"><Icon name={icon} size={17} /></div>
      <div>
        <div className="panel-eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const className =
    status === "S6_COMPLETED"
      ? "badge badge-complete"
      : status === "S5_IN_PROGRESS"
        ? "badge badge-progress"
        : status === "S4_COUNTER_ASSIGNED"
          ? "badge badge-assigned"
          : "badge";
  return <span className={className}>{statusLabel(status)}</span>;
}

export default App;
