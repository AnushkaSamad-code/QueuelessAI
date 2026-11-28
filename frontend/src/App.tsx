import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  API_URL,
  bookToken,
  callNext,
  completeService,
  createCounter,
  createService,
  findToken,
  getCurrentUser,
  getDSPlayground,
  getReports,
  getServices,
  getState,
  login,
  logout,
  operateDSArray,
  operateDSBST,
  operateDSLinkedList,
  operateDSPriorityQueue,
  signup,
  startService,
  statusLabel,
  updateCounter,
  updateService,
} from "./api";
import Icon from "./Icons";
import type { IconName } from "./Icons";
import GraphVisualizer from "./components/GraphVisualizer.jsx";
import type {
  AuthResponse,
  AuthUser,
  Counter,
  DSOperationResult,
  DSPlaygroundSnapshot,
  ReportSummary,
  Service,
  StaffView,
  StateSnapshot,
  Theme,
  Token,
  TokenResponse,
} from "./types";

const navigation: Array<{
  group: string;
  items: Array<{ label: StaffView; icon: IconName }>;
}> = [
  {
    group: "OPERATIONS",
    items: [
      { label: "Dashboard", icon: "activity" },
      { label: "Customer Booking", icon: "ticket" },
      { label: "Counter Console", icon: "users" },
      { label: "Queue Management", icon: "bars" },
      { label: "Services & Counters", icon: "settings" },
    ],
  },
  {
    group: "ACADEMIC WORKSPACE",
    items: [
      { label: "AI Search & Graph Visualizer", icon: "command" },
      { label: "DS Visualizer", icon: "layers" },
    ],
  },
  {
    group: "MANAGEMENT",
    items: [{ label: "Reports & Analytics", icon: "database" }],
  },
];

function readTheme(): Theme {
  return localStorage.getItem("queueless-theme") === "dark" ? "dark" : "light";
}

function readStoredUser(): AuthUser | null {
  try {
    const stored = localStorage.getItem("queueless-user");
    return stored ? (JSON.parse(stored) as AuthUser) : null;
  } catch {
    return null;
  }
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function serviceName(serviceId: string, services: Service[]): string {
  return services.find((service) => service.service_id === serviceId)?.name ?? serviceId;
}

function App() {
  const [user, setUser] = useState<AuthUser | null>(readStoredUser);
  const [view, setView] = useState<StaffView>("Dashboard");
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [services, setServices] = useState<Service[]>([]);
  const [snapshot, setSnapshot] = useState<StateSnapshot | null>(null);
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const staffAccess = user?.role === "STAFF" || user?.role === "ADMIN";

  const refreshOperations = useCallback(async () => {
    if (!staffAccess) return;
    try {
      const [nextSnapshot, nextReport, nextServices] = await Promise.all([
        getState(),
        getReports(),
        getServices(),
      ]);
      setSnapshot(nextSnapshot);
      setReport(nextReport);
      setServices(nextServices);
      setApiError("");
    } catch (error) {
      if (localStorage.getItem("queueless-access-token")) {
        setApiError(errorText(error));
      }
    } finally {
      setLoading(false);
    }
  }, [staffAccess]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("queueless-theme", theme);
    const themeColor = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (themeColor) themeColor.content = theme === "dark" ? "#111827" : "#f7f8fc";
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    void getServices()
      .then((items) => {
        if (!cancelled) setServices(items);
      })
      .catch((error: unknown) => {
        if (!cancelled) setApiError(errorText(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    const token = localStorage.getItem("queueless-access-token");
    if (token) {
      void getCurrentUser()
        .then((currentUser) => {
          if (!cancelled) {
            setUser(currentUser);
            localStorage.setItem("queueless-user", JSON.stringify(currentUser));
          }
        })
        .catch(() => {
          localStorage.removeItem("queueless-access-token");
          localStorage.removeItem("queueless-user");
          if (!cancelled) setUser(null);
        });
    }
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!staffAccess) {
      setSnapshot(null);
      setReport(null);
      return;
    }
    void refreshOperations();
    const interval = window.setInterval(() => void refreshOperations(), 7000);
    return () => window.clearInterval(interval);
  }, [staffAccess, refreshOperations]);

  function navigate(nextView: StaffView) {
    setView(nextView);
    setMenuOpen(false);
    setNotice("");
  }

  function saveAuth(response: AuthResponse) {
    localStorage.setItem("queueless-access-token", response.access_token);
    localStorage.setItem("queueless-user", JSON.stringify(response.user));
    setUser(response.user);
    setView(response.user.role === "CUSTOMER" ? "Customer Booking" : "Dashboard");
    setAuthOpen(false);
    setApiError("");
    setNotice(`Welcome, ${response.user.full_name}.`);
  }

  async function signOut() {
    let logoutMessage = "";
    try {
      if (localStorage.getItem("queueless-access-token")) await logout();
    } catch (error) {
      logoutMessage = `Signed out locally; the server session could not be revoked: ${errorText(error)}`;
    } finally {
      localStorage.removeItem("queueless-access-token");
      localStorage.removeItem("queueless-user");
      setUser(null);
      setSnapshot(null);
      setReport(null);
      setView("Dashboard");
      setAuthOpen(false);
      setNotice(logoutMessage);
    }
  }

  async function runCounterAction(counter: Counter, action: "call" | "start" | "complete") {
    setApiError("");
    setNotice("");
    try {
      const response =
        action === "call"
          ? await callNext(counter.counter_id)
          : action === "start"
            ? await startService(counter.counter_id)
            : await completeService(counter.counter_id);
      const labels = {
        call: "called to the counter",
        start: "service started",
        complete: "service completed",
      };
      setNotice(`${response.token.token_id} ${labels[action]}.`);
      await refreshOperations();
    } catch (error) {
      setApiError(errorText(error));
    }
  }

  async function onConfigurationSaved(message: string) {
    setNotice(message);
    await refreshOperations();
  }

  if (!staffAccess) {
    return (
      <CustomerPortal
        user={user}
        services={services}
        loading={loading}
        error={apiError}
        notice={notice}
        onDismissNotice={() => setNotice("")}
        onOpenAuth={() => setAuthOpen(true)}
        onSignOut={() => void signOut()}
        authOpen={authOpen}
        onCloseAuth={() => setAuthOpen(false)}
        onAuthenticated={saveAuth}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
      />
    );
  }

  const currentTitle = view;

  return (
    <div className="app-shell">
      {menuOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true"><span /><span /><span /><span /></div>
          <div className="brand-copy"><strong>QueueLess</strong><span>DIAGNOSTIC SYSTEMS</span></div>
          <button className="icon-button sidebar-close" aria-label="Close menu" onClick={() => setMenuOpen(false)}><Icon name="close" /></button>
        </div>
        {navigation.map((group) => (
          <div className="nav-group" key={group.group}>
            <div className="nav-section-label">{group.group}</div>
            <nav className="main-nav" aria-label={group.group}>
              {group.items.map((item) => (
                <button
                  className={`nav-item ${view === item.label ? "nav-item-active" : ""}`}
                  key={item.label}
                  onClick={() => navigate(item.label)}
                  aria-current={view === item.label ? "page" : undefined}
                >
                  <Icon name={item.icon} size={17} />
                  <span>{item.label}</span>
                  {item.label === "Counter Console" && snapshot && <span className="nav-count">{snapshot.stats.in_progress_count}</span>}
                </button>
              ))}
            </nav>
          </div>
        ))}
        <div className="nav-group">
          <div className="nav-section-label">ACCOUNT</div>
          <nav className="main-nav" aria-label="ACCOUNT">
            <button
              className={`nav-item ${view === "Profile" ? "nav-item-active" : ""}`}
              onClick={() => navigate("Profile")}
              aria-current={view === "Profile" ? "page" : undefined}
            >
              <Icon name="users" size={17} />
              <span>Profile</span>
            </button>
            <button className="nav-item" onClick={() => void signOut()}>
              <Icon name="close" size={17} />
              <span>Sign Out</span>
            </button>
          </nav>
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <span className={`status-dot ${snapshot && !apiError ? "status-dot-live" : ""}`} />
            <span>{snapshot && !apiError ? "API connected" : apiError ? "API unavailable" : "Connecting"}</span>
            <button className="text-icon-button" onClick={() => void refreshOperations()} aria-label="Refresh data"><Icon name="refresh" size={15} /></button>
          </div>
          <div className="sidebar-footer">
            <button className="nav-item appearance-button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              <Icon name={theme === "dark" ? "sun" : "moon"} size={17} />
              <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
            </button>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button className="icon-button mobile-menu-button" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Icon name="menu" /></button>
          <div className="breadcrumbs"><span>QueueLess AI</span><span className="breadcrumb-separator">/</span><strong>{currentTitle}</strong></div>
          <div className="topbar-actions">
            <span className={`connection-pill ${snapshot && !apiError ? "connection-live" : ""}`}><span className="status-dot" />{snapshot && !apiError ? "Connected" : "Connecting"}</span>
            <button className="icon-button" onClick={() => void refreshOperations()} aria-label="Refresh dashboard"><Icon name="refresh" size={16} /></button>
            <button className="account-pill" onClick={() => navigate("Profile")} title="View profile">{user?.role}</button>
          </div>
        </header>

        <main className="page-content">
          <div className="page-heading">
            <div><div className="eyebrow">QUEUELESS AI / {currentTitle.toUpperCase()}</div><h1>{currentTitle}</h1><p>{pageDescription(view)}</p></div>
            <div className="heading-meta"><span className="live-indicator"><span className="status-dot status-dot-live" />LIVE DATA</span><span className="meta-divider" /><span>Auto-refresh · 7 sec</span></div>
          </div>
          {apiError && <Alert kind="error" message={apiError} onDismiss={() => setApiError("")} />}
          {notice && <Alert kind="success" message={notice} onDismiss={() => setNotice("")} />}

          {view === "Dashboard" && <Dashboard snapshot={snapshot} report={report} loading={loading} services={services} />}
          {view === "Customer Booking" && <BookingWorkspace services={services} onNotice={setNotice} onError={setApiError} onRefresh={refreshOperations} />}
          {view === "Counter Console" && <CounterConsole snapshot={snapshot} services={services} loading={loading} onAction={(counter, action) => void runCounterAction(counter, action)} />}
          {view === "Queue Management" && <QueueManagement snapshot={snapshot} services={services} />}
          {view === "Services & Counters" && <ServicesCounters services={services} counters={snapshot?.counters ?? []} onSaved={onConfigurationSaved} onError={setApiError} />}
          {view === "AI Search & Graph Visualizer" && <GraphVisualizer services={services} />}
          {view === "DS Visualizer" && <DSVisualizer />}
          {view === "Reports & Analytics" && <ReportsPage report={report} loading={!report} />}
          {view === "Profile" && user && <ProfileWorkspace user={user} />}

          <footer className="page-footer"><span>QueueLess AI</span><span>Operations + Academic Demo Workspace</span><span className="footer-version">API · {API_URL}</span></footer>
        </main>
      </div>
    </div>
  );
}

function pageDescription(view: StaffView): string {
  const descriptions: Record<StaffView, string> = {
    Dashboard: "Live operational overview for diagnostic services and counters.",
    "Customer Booking": "Create a patient booking and track its digital queue token.",
    "Counter Console": "Call, start, and complete each service with explicit lifecycle actions.",
    "Queue Management": "Review active patient tokens and their current queue state.",
    "Services & Counters": "Manage diagnostic services, stage durations, counters, and compatibility.",
    "AI Search & Graph Visualizer": "Compare BFS, UCS, and A* on the diagnostic service route.",
    "DS Visualizer": "Perform operations on isolated manual array, linked-list, priority-queue, and BST structures.",
    "Reports & Analytics": "Review token outcomes, measured waiting time, and counter utilization.",
    Profile: "View your account identity and authorization role.",
  };
  return descriptions[view];
}

function Alert({ kind, message, onDismiss }: { kind: "error" | "success"; message: string; onDismiss?: () => void }) {
  return <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}><Icon name={kind === "error" ? "warning" : "check"} size={17} /><span>{message}</span>{onDismiss && <button className="alert-dismiss" onClick={onDismiss} aria-label="Dismiss message"><Icon name="close" size={15} /></button>}</div>;
}

function CustomerPortal({
  user,
  services,
  loading,
  error,
  notice,
  onDismissNotice,
  onOpenAuth,
  onSignOut,
  authOpen,
  onCloseAuth,
  onAuthenticated,
  theme,
  onToggleTheme,
}: {
  user: AuthUser | null;
  services: Service[];
  loading: boolean;
  error: string;
  notice: string;
  onDismissNotice: () => void;
  onOpenAuth: () => void;
  onSignOut: () => void;
  authOpen: boolean;
  onCloseAuth: () => void;
  onAuthenticated: (response: AuthResponse) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  if (authOpen) {
    return <AuthPage onAuthenticated={onAuthenticated} onContinueAsGuest={onCloseAuth} />;
  }
  return (
    <div className="customer-shell">
      <header className="customer-header">
        <a className="customer-brand" href="/" aria-label="QueueLess home"><span className="brand-mark"><span /><span /><span /><span /></span><span><strong>QueueLess</strong><small>DIAGNOSTIC CARE</small></span></a>
        <div className="customer-header-actions">
          <button className="icon-button" onClick={onToggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}><Icon name={theme === "dark" ? "sun" : "moon"} /></button>
          {user ? <button className="button button-secondary button-small" onClick={onSignOut}>Sign out</button> : <button className="button button-secondary button-small" onClick={onOpenAuth}>Login / Sign Up</button>}
        </div>
      </header>
      <main className="customer-content">
        <div className="customer-welcome"><div className="eyebrow">YOUR DIAGNOSTIC VISIT</div><h1>{user ? `Welcome, ${user.full_name.split(" ")[0]}` : "Your diagnostic visit, simplified."}</h1><p>Book a service, receive your digital token, and follow your estimated wait from one place.</p></div>
        {error && <Alert kind="error" message={error} />}
        {notice && <Alert kind="success" message={notice} onDismiss={onDismissNotice} />}
        <BookingWorkspace services={services} customerMode onNotice={() => {}} onError={() => {}} onRefresh={async () => {}} loadingServices={loading} />
        <footer className="customer-footer">QueueLess AI · Diagnostic service portal</footer>
      </main>
    </div>
  );
}

function AuthPage({
  onAuthenticated,
  onContinueAsGuest,
}: {
  onAuthenticated: (response: AuthResponse) => void;
  onContinueAsGuest: () => void;
}) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = mode === "login"
        ? await login(email, password)
        : await signup({ full_name: name.trim(), email: email.trim(), password });
      onAuthenticated(response);
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function demo(emailValue: string, passwordValue: string) {
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await login(emailValue, passwordValue));
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="panel auth-card">
        <div className="auth-brand"><span className="brand-mark"><span /><span /><span /><span /></span><strong>QueueLess</strong></div>
        <div className="panel-eyebrow">SECURE ACCESS</div>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p>Sign in to your QueueLess account or continue as a guest customer.</p>
        <div className="auth-tabs"><button className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => { setMode("login"); setError(""); }}>Login</button><button className={mode === "signup" ? "auth-tab active" : "auth-tab"} onClick={() => { setMode("signup"); setError(""); }}>Sign Up</button></div>
        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          {mode === "signup" && <><label className="field-label" htmlFor="signup-name">Full name</label><input id="signup-name" className="text-input" value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" required minLength={1} /></>}
          <label className="field-label" htmlFor="auth-email">Email</label><input id="auth-email" className="text-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
          <label className="field-label" htmlFor="auth-password">Password</label><input id="auth-password" className="text-input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "signup" ? 8 : undefined} />
          {error && <div className="inline-error" role="alert"><Icon name="warning" size={15} />{error}</div>}
          <button className="button button-primary auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Login" : "Create account"}</button>
        </form>
        <div className="demo-login">
          <div className="panel-eyebrow">ONE-CLICK DEMO ACCESS</div>
          <button className="demo-role-button" disabled={busy} onClick={() => void demo("admin@queueless.ai", "admin123")}><span>Login as Admin</span><small>Full workspace access</small></button>
          <button className="demo-role-button" disabled={busy} onClick={() => void demo("staff@queueless.ai", "staff123")}><span>Login as Staff</span><small>Operations + academic modules</small></button>
          <button className="demo-role-button" disabled={busy} onClick={() => void demo("patient@queueless.ai", "patient123")}><span>Continue as Customer</span><small>Customer portal access</small></button>
        </div>
        <button className="guest-link" onClick={onContinueAsGuest}>Continue as guest without an account</button>
      </section>
    </main>
  );
}

function BookingWorkspace({
  services,
  customerMode = false,
  onNotice,
  onError,
  onRefresh,
  loadingServices = false,
}: {
  services: Service[];
  customerMode?: boolean;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
  onRefresh: () => Promise<void>;
  loadingServices?: boolean;
}) {
  const [customerName, setCustomerName] = useState("");
  const [serviceId, setServiceId] = useState(services[0]?.service_id ?? "");
  const [tokenQuery, setTokenQuery] = useState("");
  const [tokenResult, setTokenResult] = useState<TokenResponse | null>(null);
  const [localError, setLocalError] = useState("");
  const [busy, setBusy] = useState(false);
  const [searchBusy, setSearchBusy] = useState(false);

  useEffect(() => {
    if (services.length && !services.some((service) => service.service_id === serviceId)) {
      setServiceId(services[0].service_id);
    }
  }, [serviceId, services]);

  useEffect(() => {
    const trackedId = tokenResult?.token.token_id;
    if (!trackedId) return undefined;
    let cancelled = false;
    const interval = window.setInterval(() => {
      void findToken(trackedId)
        .then((result) => { if (!cancelled) setTokenResult(result); })
        .catch((error: unknown) => { if (!cancelled) setLocalError(errorText(error)); });
    }, 7000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [tokenResult?.token.token_id]);

  const selectedService = services.find((service) => service.service_id === serviceId);

  async function submitBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setLocalError("");
    onError("");
    const patientName = customerName.trim();
    if (!patientName) {
      const message = "Enter the patient name before booking.";
      setLocalError(message);
      onError(message);
      setBusy(false);
      return;
    }
    try {
      const response = await bookToken({
        customer_name: patientName,
        service_id: serviceId,
      });
      const nextToken: TokenResponse = {
        token: response.token,
        optimal_path: response.recommendation.optimal_path,
        eta_min: response.recommendation.estimated_wait_min,
      };
      setTokenResult(nextToken);
      setTokenQuery(response.token.token_id);
      setCustomerName("");
      onNotice(`Booking confirmed. Your token is ${response.token.token_id}.`);
      await onRefresh();
    } catch (error) {
      const message = errorText(error);
      setLocalError(message);
      onError(message);
    } finally {
      setBusy(false);
    }
  }

  async function submitTokenSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = tokenQuery.trim().toUpperCase();
    if (!normalized) {
      setLocalError("Enter your token ID to check its status.");
      return;
    }
    setSearchBusy(true);
    setLocalError("");
    try {
      setTokenResult(await findToken(normalized));
    } catch (error) {
      setLocalError(errorText(error));
    } finally {
      setSearchBusy(false);
    }
  }

  return (
    <>
      <div className="booking-layout customer-booking-layout">
        <section className="panel booking-panel">
          <PanelHeading eyebrow="PATIENT BOOKING" title="Book a diagnostic service" detail="Choose a service and receive your digital queue token." icon="beaker" />
          <form className="booking-form" onSubmit={(event) => void submitBooking(event)}>
            <label className="field-label" htmlFor={customerMode ? "portal-patient-name" : "booking-patient-name"}>Patient name <span className="required-mark">*</span></label>
            <input id={customerMode ? "portal-patient-name" : "booking-patient-name"} className="text-input" value={customerName} onChange={(event) => setCustomerName(event.target.value)} placeholder="Enter your name" autoComplete="off" required minLength={1} />
            <div className="field-label-row"><label className="field-label" htmlFor={customerMode ? "portal-service" : "booking-service"}>Diagnostic service <span className="required-mark">*</span></label><span className="field-hint">{services.length} available</span></div>
            <div className="select-wrap"><select id={customerMode ? "portal-service" : "booking-service"} className="text-input select-input" value={serviceId} onChange={(event) => setServiceId(event.target.value)} required disabled={!services.length}>{services.map((service) => <option value={service.service_id} key={service.service_id}>{service.name}</option>)}</select><Icon name="chevron-down" size={16} /></div>
            {selectedService && <div className="service-detail"><div className="service-icon"><Icon name="flask" size={17} /></div><div><strong>{selectedService.category}</strong><span>Estimated service time · {selectedService.duration}</span></div><span className="service-code">{selectedService.service_id}</span></div>}
            <div className="booking-form-actions">
              <button className="button button-secondary" type="button" disabled={busy} onClick={() => { setCustomerName(""); setLocalError(""); }}>
                Clear form
              </button>
              <button className="button button-primary booking-submit" type="submit" disabled={busy || loadingServices || services.length === 0}>{busy ? <><span className="button-spinner" />Creating token…</> : <>Generate digital token <Icon name="arrow-right" size={16} /></>}</button>
            </div>
            <p className="form-footnote">Your token status and estimated wait update automatically.</p>
          </form>
        </section>

        <section className="panel tracker-panel">
          <PanelHeading eyebrow="TOKEN STATUS TRACKER" title="Track your visit" detail="Enter your token to see its current status and estimated wait." icon="search" />
          <form className="token-search-form" onSubmit={(event) => void submitTokenSearch(event)}>
            <div className="search-input-wrap"><Icon name="ticket" size={17} /><input className="search-input" value={tokenQuery} onChange={(event) => setTokenQuery(event.target.value)} placeholder="Enter your token ID" aria-label="Digital token ID" autoCapitalize="characters" /><button className="button button-secondary button-small" type="submit" disabled={searchBusy}>{searchBusy ? "Checking…" : "Track token"}</button></div>
          </form>
          {localError && <div className="inline-error" role="alert"><Icon name="warning" size={15} />{localError}</div>}
          {tokenResult ? <TokenStatusCard result={tokenResult} services={services} /> : <div className="tracker-empty"><div className="empty-icon"><Icon name="ticket" size={20} /></div><strong>Your token details will appear here</strong><span>Book a service or enter your token ID to see your estimated wait.</span></div>}
          <div className="tracker-foot"><span><Icon name="activity" size={14} />Updates automatically</span></div>
        </section>
      </div>
    </>
  );
}

function TokenStatusCard({ result, services }: { result: TokenResponse; services: Service[] }) {
  const { token } = result;
  const completed = token.status === "S6_COMPLETED";
  return (
    <div className="token-result customer-token-result">
      <div className="result-topline"><span className="result-label">DIGITAL TOKEN</span><StatusBadge status={token.status} /></div>
      <div className="result-main"><div><span className="token-caption">YOUR TOKEN</span><strong className="large-token">{token.token_id}</strong></div>{result.eta_min !== null && token.status === "S3_WAITING" && <div className="result-eta"><span>Estimated wait</span><strong>{Math.max(0, Math.round(result.eta_min))} min</strong></div>}</div>
      <div className="result-person"><span className="person-initials">{token.customer_name.slice(0, 1).toUpperCase()}</span><div><strong>{token.customer_name}</strong><span>{serviceName(token.service_id, services)}</span></div></div>
      {!completed && token.counter_id && <div className="token-counter">Assigned counter · Counter {token.counter_id}</div>}
      <div className="customer-status-note">{completed ? "Service Completed. Thank you for visiting." : token.status === "S5_IN_PROGRESS" ? "Your service is currently in progress." : token.status === "S4_COUNTER_ASSIGNED" ? "Your token has been called. Please proceed to the service counter." : "You are in the queue. We will update your status as service progresses."}</div>
      <div className="result-meta"><span>Updated {formatTime(token.updated_at)}</span></div>
    </div>
  );
}

function Dashboard({
  snapshot,
  report,
  loading,
  services,
}: {
  snapshot: StateSnapshot | null;
  report: ReportSummary | null;
  loading: boolean;
  services: Service[];
}) {
  return (
    <>
      <section className="metric-grid" aria-label="Operational summary">
        {loading || !snapshot || !report ? Array.from({ length: 7 }, (_, index) => <MetricSkeleton key={index} />) : <>
          <MetricCard label="Total tokens" value={report.total_appointments} note="All recorded visits" icon="ticket" />
          <MetricCard label="Waiting" value={report.waiting_count} note="Waiting or called" icon="clock" />
          <MetricCard label="Currently serving" value={report.in_progress_count} note="Active service sessions" icon="activity" />
          <MetricCard label="Completed services" value={report.completed_count} note="Completed token records" icon="check" />
          <MetricCard label="Active counters" value={report.open_counters} note="Currently open" icon="users" />
          <MetricCard label="Average waiting time" value={report.average_wait_min === null ? "—" : `${report.average_wait_min.toFixed(1)} min`} note={`${report.waiting_time_sample_count} valid started visits`} icon="clock" />
          <MetricCard label="Counter utilization" value={`${report.utilization_pct.toFixed(0)}%`} note={`${report.busy_counters} busy of ${report.open_counters} open now`} icon="bars" />
        </>}
      </section>
      <div className="dashboard-lower">
        <section className="panel">
          <PanelHeading eyebrow="LIVE QUEUE" title="Recent patient tokens" detail="Latest active tokens across service counters." icon="ticket" />
          {snapshot ? <TokenTable tokens={[...snapshot.active_tokens].reverse().slice(0, 8)} services={services} /> : <div className="empty-state-compact">Queue data will appear when the API is available.</div>}
        </section>
        <section className="panel">
          <PanelHeading eyebrow="SERVICE FLOOR" title="Counter availability" detail="Current status and queue sizes." icon="users" />
          <div className="dashboard-counters">{snapshot?.counters.map((counter) => <div className="dashboard-counter" key={counter.counter_id}><span className={`status-dot ${counter.status === "OPEN" ? "status-dot-live" : ""}`} /><strong>{counter.name}</strong><span>{counter.queue_length} waiting</span><StatusBadge status={counter.status} /></div>)}</div>
        </section>
      </div>
    </>
  );
}

function ProfileWorkspace({ user }: { user: AuthUser }) {
  return (
    <section className="panel profile-workspace">
      <PanelHeading eyebrow="ACCOUNT PROFILE" title="Profile" detail="Your account name is a display identity; permissions are determined by the authorization role." icon="users" />
      <div className="profile-details">
        <div className="profile-detail"><span>Display name</span><strong>{user.full_name}</strong></div>
        <div className="profile-detail"><span>Email</span><strong>{user.email}</strong></div>
        <div className="profile-detail"><span>Authorization role</span><strong className="role-badge">{user.role}</strong></div>
      </div>
      <p className="profile-note">Role-based access is enforced by the API. Profile display text does not grant or change permissions.</p>
    </section>
  );
}

function CounterConsole({ snapshot, services, loading, onAction }: { snapshot: StateSnapshot | null; services: Service[]; loading: boolean; onAction: (counter: Counter, action: "call" | "start" | "complete") => void }) {
  return (
    <>
      <div className="section-title-row"><div><div className="panel-eyebrow">COUNTER WORKFLOW</div><h2>Counter console</h2><p>Every action advances one explicit lifecycle transition.</p></div><span className="live-indicator"><span className="status-dot status-dot-live" />LIVE QUEUES</span></div>
      <div className="counter-grid">
        {loading || !snapshot ? [1, 2, 3].map((counter) => <CounterSkeleton key={counter} />) : snapshot.counters.map((counter) => {
          const waiting = snapshot.queues[counter.counter_id] ?? [];
          const active = snapshot.active_tokens.find((token) => token.token_id === counter.current_token_id);
          const busy = counter.status !== "OPEN";
          const action: "call" | "start" | "complete" | null = active?.status === "S4_COUNTER_ASSIGNED" ? "start" : active?.status === "S5_IN_PROGRESS" ? "complete" : !active && waiting.length ? "call" : null;
          const label = action === "call" ? "Call Next" : action === "start" ? "Start Service (S4 → S5)" : action === "complete" ? "Complete Service (S5 → S6)" : counter.status === "CLOSED" ? "Counter closed" : "Queue clear";
          return (
            <section className="panel counter-card" key={counter.counter_id}>
              <div className="counter-card-heading"><div className="counter-number">{counter.counter_id.padStart(2, "0")}</div><div className="counter-card-title"><strong>{counter.name}</strong><span><span className={`status-dot ${counter.status === "OPEN" ? "status-dot-live" : ""}`} />{counter.status}</span></div><span className="counter-queue-count">{waiting.length} waiting</span></div>
              <div className="current-service"><div className="current-label"><span className="panel-eyebrow">{active ? "CURRENT TOKEN" : "NOW SERVING"}</span></div>{active ? <div className="active-token-card"><div><span className="token-caption">{active.token_id}</span><strong>{active.customer_name}</strong></div><div><span>{serviceName(active.service_id, services)}</span></div><StatusBadge status={active.status} /></div> : <div className="no-active-token"><span className="empty-dot" /><span>No token called</span></div>}</div>
              <div className="counter-queue"><div className="queue-heading"><span>UP NEXT</span><span>{waiting.length} {waiting.length === 1 ? "patient" : "patients"}</span></div>{waiting.length ? <div className="queue-list">{waiting.slice(0, 4).map((token, index) => <div className="queue-row" key={token.token_id}><span className="queue-position">{String(index + 1).padStart(2, "0")}</span><span className="queue-patient"><strong>{token.token_id}</strong><span>{token.customer_name}</span></span><span className={`priority-mark priority-${token.priority_level.toLowerCase()}`}>{token.priority_level}</span></div>)}</div> : <div className="queue-empty">Queue is clear</div>}</div>
              <button className={`button ${action === "call" || action === "start" || action === "complete" ? "button-primary" : "button-secondary"} counter-action`} disabled={!action || busy} onClick={() => action && onAction(counter, action)}>{label}{action && <Icon name="arrow-right" size={16} />}</button>
              <p className="counter-action-hint">{active?.status === "S4_COUNTER_ASSIGNED" ? "Start the called token's service." : active?.status === "S5_IN_PROGRESS" ? "Complete the in-progress service." : "Call the next scheduled token."}</p>
            </section>
          );
        })}
      </div>
      <div className="notice-strip"><Icon name="activity" size={16} /><span>Workflow order: waiting → called <b>S4</b> → Start Service <b>S5</b> → Complete Service <b>S6</b>.</span></div>
    </>
  );
}

function QueueManagement({ snapshot, services }: { snapshot: StateSnapshot | null; services: Service[] }) {
  const [query, setQuery] = useState("");
  const tokens = useMemo(() => (snapshot?.active_tokens ?? []).filter((token) => {
    const term = query.trim().toLowerCase();
    return !term || token.token_id.toLowerCase().includes(term) || token.customer_name.toLowerCase().includes(term) || token.status.toLowerCase().includes(term);
  }), [snapshot, query]);
  return <section className="panel queue-management"><PanelHeading eyebrow="ACTIVE QUEUE" title="Queue management" detail="Search waiting, called, and in-progress patient tokens." icon="bars" /><input className="text-input queue-filter" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by token, patient, or status" /><TokenTable tokens={tokens} services={services} /></section>;
}

function ServicesCounters({ services, counters, onSaved, onError }: { services: Service[]; counters: Counter[]; onSaved: (message: string) => Promise<void>; onError: (message: string) => void }) {
  const [mode, setMode] = useState<"add" | "edit">("add");
  const [serviceId, setServiceId] = useState("");
  const [serviceNameValue, setServiceNameValue] = useState("");
  const [category, setCategory] = useState("");
  const [registration, setRegistration] = useState("5");
  const [sample, setSample] = useState("8");
  const [report, setReport] = useState("3");
  const [selectedCounter, setSelectedCounter] = useState("");
  const [counterId, setCounterId] = useState("");
  const [counterName, setCounterName] = useState("");
  const [counterStatus, setCounterStatus] = useState<"OPEN" | "CLOSED">("OPEN");
  const [supportedServices, setSupportedServices] = useState<string[]>(services.map((service) => service.service_id));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedCounter) return;
    const current = counters.find((counter) => counter.counter_id === selectedCounter);
    if (current) {
      setCounterId(current.counter_id);
      setCounterName(current.name);
      setCounterStatus(current.status === "CLOSED" ? "CLOSED" : "OPEN");
      setSupportedServices(current.supported_services ?? []);
    }
  }, [counters, selectedCounter]);

  useEffect(() => {
    if (!selectedCounter && supportedServices.length === 0 && services.length > 0) {
      setSupportedServices(services.map((service) => service.service_id));
    }
  }, [selectedCounter, services, supportedServices.length]);

  function loadService(value: string) {
    setServiceId(value);
    const current = services.find((service) => service.service_id === value);
    if (!current) return;
    setServiceNameValue(current.name);
    setCategory(current.category);
    setRegistration(String(current.estimated_durations_min.registration ?? current.estimated_durations_min.Registration ?? 5));
    setSample(String(current.estimated_durations_min.sample_collection ?? current.estimated_durations_min["Sample Collection"] ?? 8));
    setReport(String(current.estimated_durations_min.report_collection ?? current.estimated_durations_min["Report Collection"] ?? 3));
  }

  async function submitService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    onError("");
    try {
      const values = {
        name: serviceNameValue.trim(),
        category: category.trim(),
        estimated_durations_min: { Registration: Number(registration), "Sample Collection": Number(sample), "Report Collection": Number(report) },
      };
      if (!values.name || !values.category || (mode === "add" && !serviceId.trim())) {
        throw new Error("Complete all required service fields.");
      }
      if (services.some((service) => service.service_id !== (mode === "edit" ? serviceId : "") && service.name.trim().toLocaleLowerCase() === values.name.toLocaleLowerCase())) {
        throw new Error("A service with this name already exists.");
      }
      if (mode === "add") {
        await createService({ service_id: serviceId.trim(), ...values });
        await onSaved("Service added and available for booking.");
      } else {
        await updateService(serviceId, values);
        await onSaved("Service details updated.");
      }
    } catch (error) {
      onError(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  async function submitCounter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    onError("");
    try {
      const payload = { counter_id: counterId.trim(), name: counterName.trim(), status: counterStatus, supported_services: supportedServices };
      if (!payload.name || (!selectedCounter && !payload.counter_id)) {
        throw new Error("Complete all required counter fields.");
      }
      if (counters.some((counter) => counter.counter_id !== selectedCounter && counter.name.trim().toLocaleLowerCase() === payload.name.toLocaleLowerCase())) {
        throw new Error("A counter with this name already exists.");
      }
      if (selectedCounter) {
        await updateCounter(selectedCounter, { name: payload.name, status: payload.status, supported_services: payload.supported_services });
        await onSaved("Counter configuration updated.");
      } else {
        await createCounter(payload);
        await onSaved("Counter added.");
      }
      setSelectedCounter("");
      setCounterId("");
      setCounterName("");
      setSupportedServices(services.map((service) => service.service_id));
    } catch (error) {
      onError(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="management-grid">
      <section className="panel management-panel">
        <PanelHeading eyebrow="DIAGNOSTIC CATALOG" title="Service management" detail="Add or edit service stage durations. Changes apply to booking and route estimates." icon="beaker" />
        <div className="form-mode-tabs"><button className={mode === "add" ? "active" : ""} onClick={() => { setMode("add"); setServiceId(""); setServiceNameValue(""); setCategory(""); }}>Add service</button><button className={mode === "edit" ? "active" : ""} onClick={() => { setMode("edit"); if (services[0]) loadService(services[0].service_id); }}>Edit service</button></div>
        <form className="management-form" onSubmit={(event) => void submitService(event)}>
          <div className="management-section"><h3>Service details</h3>
            {mode === "edit" ? <><label className="field-label" htmlFor="edit-service-id">Service <span className="required-mark">*</span></label><select className="text-input" id="edit-service-id" value={serviceId} onChange={(event) => loadService(event.target.value)} required>{services.map((service) => <option value={service.service_id} key={service.service_id}>{service.service_id} · {service.name}</option>)}</select></> : <><label className="field-label" htmlFor="new-service-id">Service ID <span className="required-mark">*</span></label><input id="new-service-id" className="text-input" value={serviceId} onChange={(event) => setServiceId(event.target.value)} placeholder="SVC-009" required /></>}
            <label className="field-label" htmlFor="service-name">Service name <span className="required-mark">*</span></label><input id="service-name" className="text-input" value={serviceNameValue} onChange={(event) => setServiceNameValue(event.target.value)} required />
            <label className="field-label" htmlFor="service-category">Category <span className="required-mark">*</span></label><input id="service-category" className="text-input" value={category} onChange={(event) => setCategory(event.target.value)} required />
          </div>
          <div className="management-section"><h3>Estimated stage durations</h3><div className="duration-input-grid"><DurationInput id="duration-registration" label="Registration (min)" value={registration} onChange={setRegistration} /><DurationInput id="duration-sample" label="Sample collection (min)" value={sample} onChange={setSample} /><DurationInput id="duration-report" label="Report collection (min)" value={report} onChange={setReport} /></div></div>
          <button className="button button-primary" type="submit" disabled={busy || (mode === "edit" && !services.length)}>{busy ? "Saving…" : mode === "add" ? "Add service" : "Save service changes"}</button>
        </form>
        <div className="configuration-list">{services.map((service) => <button className="configuration-row" key={service.service_id} onClick={() => { setMode("edit"); loadService(service.service_id); }}><span><strong>{service.name}</strong><small>{service.service_id} · {service.category}</small></span><span>{service.duration}</span></button>)}</div>
      </section>

      <section className="panel management-panel">
        <PanelHeading eyebrow="SERVICE FLOOR" title="Counter management" detail="Add counters or update availability and supported services." icon="users" />
        <form className="management-form" onSubmit={(event) => void submitCounter(event)}>
          {counters.length > 0 && <><label className="field-label" htmlFor="counter-edit-select">Edit existing counter</label><select id="counter-edit-select" className="text-input" value={selectedCounter} onChange={(event) => { const next = event.target.value; setSelectedCounter(next); if (!next) { setCounterId(""); setCounterName(""); setCounterStatus("OPEN"); setSupportedServices(services.map((service) => service.service_id)); } }}><option value="">Add a new counter…</option>{counters.map((counter) => <option value={counter.counter_id} key={counter.counter_id}>{counter.name}</option>)}</select></>}
          <div className="management-section"><h3>Counter details</h3>
            {!selectedCounter && <><label className="field-label" htmlFor="new-counter-id">Counter ID <span className="required-mark">*</span></label><input id="new-counter-id" className="text-input" value={counterId} onChange={(event) => setCounterId(event.target.value)} placeholder="4" required /></>}
            <label className="field-label" htmlFor="counter-name">Counter name <span className="required-mark">*</span></label><input id="counter-name" className="text-input" value={counterName} onChange={(event) => setCounterName(event.target.value)} required />
            <label className="field-label" htmlFor="counter-availability">Availability <span className="required-mark">*</span></label><select id="counter-availability" className="text-input" value={counterStatus} onChange={(event) => setCounterStatus(event.target.value as "OPEN" | "CLOSED")}><option value="OPEN">OPEN</option><option value="CLOSED">CLOSED</option></select>
          </div>
          <fieldset className="service-checkboxes"><legend className="field-label">Supported services</legend>{services.map((service) => <label key={service.service_id}><input type="checkbox" checked={supportedServices.includes(service.service_id)} onChange={(event) => setSupportedServices((current) => event.target.checked ? [...current, service.service_id] : current.filter((id) => id !== service.service_id))} /><span>{service.name}</span></label>)}</fieldset>
          <button className="button button-primary" type="submit" disabled={busy}>{busy ? "Saving…" : selectedCounter ? "Save counter changes" : "Add counter"}</button>
        </form>
        <div className="configuration-list">{counters.map((counter) => <button className="configuration-row" key={counter.counter_id} onClick={() => setSelectedCounter(counter.counter_id)}><span><strong>{counter.name}</strong><small>{counter.supported_services?.length ?? 0} supported services</small></span><StatusBadge status={counter.status} /></button>)}</div>
      </section>
    </div>
  );
}

function DurationInput({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return <label className="duration-input" htmlFor={id}><span>{label} <span className="required-mark">*</span></span><input id={id} className="text-input" type="number" min="1" step="0.5" value={value} onChange={(event) => onChange(event.target.value)} required /></label>;
}

const DS_TABS = ["Array", "Linked List", "Priority Queue", "BST"] as const;
type DSTab = (typeof DS_TABS)[number];
const DS_OPERATIONS: Record<DSTab, readonly string[]> = {
  Array: ["insert", "delete", "search", "update", "traverse"],
  "Linked List": ["insert_beginning", "insert_end", "insert_position", "delete", "search", "traverse"],
  "Priority Queue": ["enqueue", "dequeue", "peek", "update_priority", "display"],
  BST: ["insert", "search", "delete", "inorder", "preorder", "postorder"],
};
const DS_COMPLEXITIES: Record<DSTab, Record<string, string>> = {
  Array: { insert: "O(n)", delete: "O(n)", search: "O(n)", update: "O(1)", traverse: "O(n)" },
  "Linked List": { insert_beginning: "O(1)", insert_end: "O(1)", insert_position: "O(n)", delete: "O(n)", search: "O(n)", traverse: "O(n)" },
  "Priority Queue": {
    enqueue: "O(n) including duplicate-key validation; heap insertion is O(log n).",
    dequeue: "O(log n)",
    peek: "O(1)",
    update_priority: "O(n) lookup plus O(log n) heap repair.",
    display: "O(n)",
  },
  BST: {
    insert: "O(log n) average; O(n) worst case.",
    search: "O(log n) average; O(n) worst case.",
    delete: "O(log n) average; O(n) worst case.",
    inorder: "O(n)",
    preorder: "O(n)",
    postorder: "O(n)",
  },
};

function DSVisualizer() {
  const [tab, setTab] = useState<DSTab>("Array");
  const [operation, setOperation] = useState<string>("insert");
  const [snapshot, setSnapshot] = useState<DSPlaygroundSnapshot | null>(null);
  const [lastResult, setLastResult] = useState<DSOperationResult | null>(null);
  const [value, setValue] = useState("");
  const [index, setIndex] = useState("");
  const [itemId, setItemId] = useState("");
  const [priority, setPriority] = useState("5");
  const [bstKey, setBstKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getDSPlayground()
      .then((result) => {
        if (active) setSnapshot(result);
      })
      .catch((requestError: unknown) => {
        if (active) setError(errorText(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function changeTab(nextTab: DSTab) {
    setTab(nextTab);
    setOperation(DS_OPERATIONS[nextTab][0]);
    setValue("");
    setIndex("");
    setItemId("");
    setBstKey("");
    setLastResult(null);
    setError("");
  }

  async function submitOperation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setLastResult(null);
    try {
      let result: DSOperationResult;
      if (tab === "Array") {
        const selected = DS_OPERATIONS.Array.find((item) => item === operation);
        if (!selected) throw new Error("Choose a valid array operation.");
        result = await operateDSArray({
          operation: selected as "insert" | "delete" | "search" | "update" | "traverse",
          ...(value.trim() ? { value: value.trim() } : {}),
          ...(index !== "" ? { index: Number(index) } : {}),
        });
      } else if (tab === "Linked List") {
        const selected = DS_OPERATIONS["Linked List"].find((item) => item === operation);
        if (!selected) throw new Error("Choose a valid linked-list operation.");
        result = await operateDSLinkedList({
          operation: selected as "insert_beginning" | "insert_end" | "insert_position" | "delete" | "search" | "traverse",
          ...(value.trim() ? { value: value.trim() } : {}),
          ...(index !== "" ? { position: Number(index) } : {}),
          ...(itemId.trim() ? { item_id: itemId.trim() } : {}),
        });
      } else if (tab === "Priority Queue") {
        const selected = DS_OPERATIONS["Priority Queue"].find((item) => item === operation);
        if (!selected) throw new Error("Choose a valid priority-queue operation.");
        result = await operateDSPriorityQueue({
          operation: selected as "enqueue" | "dequeue" | "peek" | "update_priority" | "display",
          ...(value.trim() ? { value: value.trim() } : {}),
          ...(priority !== "" ? { priority: Number(priority) } : {}),
          ...(itemId.trim() ? { item_id: itemId.trim() } : {}),
        });
      } else {
        const selected = DS_OPERATIONS.BST.find((item) => item === operation);
        if (!selected) throw new Error("Choose a valid BST operation.");
        result = await operateDSBST({
          operation: selected as "insert" | "search" | "delete" | "inorder" | "preorder" | "postorder",
          ...(bstKey.trim() ? { key: bstKey.trim() } : {}),
          ...(value.trim() ? { value: value.trim() } : {}),
        });
      }
      setSnapshot(result.snapshot);
      setLastResult(result);
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  }

  const needsValue = tab === "Array"
    ? ["insert", "search", "update"].includes(operation)
    : tab === "Linked List"
      ? ["insert_beginning", "insert_end", "insert_position", "search"].includes(operation)
      : tab === "Priority Queue"
        ? operation === "enqueue"
        : operation === "insert";
  const needsIndex = (tab === "Array" && ["insert", "delete", "update"].includes(operation))
    || (tab === "Linked List" && operation === "insert_position");
  const needsItemId = (tab === "Linked List" && operation === "delete")
    || (tab === "Priority Queue" && operation === "update_priority");
  const needsPriority = tab === "Priority Queue" && ["enqueue", "update_priority"].includes(operation);
  const needsBSTKey = tab === "BST" && ["insert", "search", "delete"].includes(operation);

  if (!snapshot) {
    return <div className="inspector-grid">{error && <div className="alert alert-error" role="alert">{error}</div>}{loading && <><InspectorSkeleton wide /><InspectorSkeleton /></>}</div>;
  }

  return (
    <section className="panel ds-visualizer">
      <div className="panel-heading">
        <div className="panel-eyebrow">INTERACTIVE DATA STRUCTURES</div>
        <h2>DS Visualizer</h2>
        <p>Every operation runs on the backend's manual implementation in an isolated playground, never on live queue data.</p>
      </div>
      <div className="ds-tabs" role="tablist" aria-label="Choose a data structure">
        {DS_TABS.map((name) => <button role="tab" aria-selected={tab === name} className={tab === name ? "active" : ""} onClick={() => changeTab(name)} key={name}>{name === "BST" ? "Binary Search Tree" : name}</button>)}
      </div>
      <div className="ds-playground-grid">
        <section className="ds-tab-panel">
          <PanelHeading eyebrow="OPERATION CONTROLS" title={`${tab} operations`} detail="Select an operation and run it against the current backend structure." icon="command" />
          <form className="ds-operation-form" onSubmit={(event) => void submitOperation(event)}>
            <label className="field-label" htmlFor="ds-operation">Operation</label>
            <select id="ds-operation" className="text-input" value={operation} onChange={(event) => { setOperation(event.target.value); setLastResult(null); }}>
              {DS_OPERATIONS[tab].map((item) => <option value={item} key={item}>{item.replaceAll("_", " ")}</option>)}
            </select>
            {needsBSTKey && <label className="field-label" htmlFor="ds-key">Key<input id="ds-key" className="text-input" value={bstKey} onChange={(event) => setBstKey(event.target.value)} required /></label>}
            {needsValue && <label className="field-label" htmlFor="ds-value">{tab === "BST" ? "Value" : "Value"}<input id="ds-value" className="text-input" value={value} onChange={(event) => setValue(event.target.value)} required /></label>}
            {needsIndex && <label className="field-label" htmlFor="ds-index">{tab === "Linked List" ? "Position (0-based)" : "Index (0-based)"}<input id="ds-index" className="text-input" type="number" min="0" value={index} onChange={(event) => setIndex(event.target.value)} required={operation !== "insert"} /></label>}
            {needsItemId && <label className="field-label" htmlFor="ds-item-id">Item ID<input id="ds-item-id" className="text-input" value={itemId} onChange={(event) => setItemId(event.target.value)} placeholder="e.g. L001 or P001" required /></label>}
            {needsPriority && <label className="field-label" htmlFor="ds-priority">Priority (0 = highest)<input id="ds-priority" className="text-input" type="number" min="0" max="9" value={priority} onChange={(event) => setPriority(event.target.value)} required /></label>}
            <p className="ds-complexity-hint">Expected time complexity · {lastResult?.operation === operation ? lastResult.complexity : DS_COMPLEXITIES[tab][operation]}</p>
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <button className="button button-primary" type="submit" disabled={busy}>{busy ? "Running…" : `Run ${operation.replaceAll("_", " ")}`}</button>
          </form>
          {lastResult && <div className="ds-operation-result" role="status"><span>OPERATION RESULT</span><strong>{lastResult.message}</strong><small>Time complexity · {lastResult.complexity}</small></div>}
        </section>
        <section className="ds-tab-panel ds-structure-panel">
          <PanelHeading eyebrow="CURRENT STRUCTURE" title={tab} detail="Visualization refreshes from the operation response." icon="database" />
          {tab === "Array" && <div className="ds-array-visual" aria-label="Array elements">{snapshot.array.elements.length ? snapshot.array.elements.map((item, position) => <div className="array-slot array-slot-filled" key={item.token_id}><span className="slot-index">{position}</span><span className="slot-value">{item.value}</span><small>{item.token_id}</small></div>) : <div className="empty-state-compact">Array is empty. Insert a value to begin.</div>}<div className="ds-structure-meta">{snapshot.array.size} items · capacity {snapshot.array.capacity}</div></div>}
          {tab === "Linked List" && <div className="linked-chain ds-linked-chain">{snapshot.linked_list.length ? <>{snapshot.linked_list.map((item, position) => <div className="linked-node-wrap" key={item.token_id}><div className="linked-node"><strong>{item.value}</strong><span>{item.token_id} · node {position}</span></div><Icon name="arrow-right" size={14} /></div>)}<span className="linked-null">NULL</span></> : <div className="empty-state-compact">Linked list is empty. Insert at either end.</div>}</div>}
          {tab === "Priority Queue" && <>{snapshot.priority_queue.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Heap index</th><th>Value · ID</th><th>Priority</th><th>Effective</th></tr></thead><tbody>{snapshot.priority_queue.map((entry) => <tr key={entry.token_id}><td>{entry.index}</td><td>{entry.value} · {entry.token_id}</td><td>{entry.base_priority}</td><td>{entry.effective_priority}</td></tr>)}</tbody></table></div> : <div className="empty-state-compact">Priority queue is empty. Enqueue a value to begin.</div>}</>}
          {tab === "BST" && <>{snapshot.bst.root ? <div className="bst-visualization"><BSTStructureNode node={snapshot.bst.root} /></div> : <div className="empty-state-compact">BST is empty. Insert a key and value to begin.</div>}<div className="traversal-grid">{([["Inorder", snapshot.bst.inorder], ["Preorder", snapshot.bst.preorder], ["Postorder", snapshot.bst.postorder]] as const).map(([name, items]) => <div className="traversal-card" key={name}><div className="traversal-heading"><strong>{name}</strong><span>{items.length} nodes</span></div><div className="traversal-values">{items.length ? items.map((item) => <span className="traversal-token" key={`${name}-${item.token_id}`}>{item.token_id}: {item.value}</span>) : <span className="empty-state-compact">No nodes</span>}</div></div>)}</div></>}
        </section>
      </div>
    </section>
  );
}

function BSTStructureNode({ node }: { node: NonNullable<DSPlaygroundSnapshot["bst"]["root"]> }) {
  return (
    <div className="bst-node-branch">
      <div className="bst-node"><strong>{node.key}</strong><span>{node.value}</span></div>
      {(node.left || node.right) && <div className="bst-node-children">{node.left ? <BSTStructureNode node={node.left} /> : <span className="bst-empty-child">∅</span>}{node.right ? <BSTStructureNode node={node.right} /> : <span className="bst-empty-child">∅</span>}</div>}
    </div>
  );
}

function ReportsPage({ report, loading }: { report: ReportSummary | null; loading: boolean }) {
  if (loading || !report) return <section className="metric-grid"><MetricSkeleton /><MetricSkeleton /><MetricSkeleton /><MetricSkeleton /></section>;
  return (
    <>
      <section className="metric-grid"><MetricCard label="Total tokens" value={report.total_appointments} note="All recorded visits" icon="ticket" /><MetricCard label="Waiting" value={report.waiting_count} note="Waiting and called tokens" icon="clock" /><MetricCard label="In progress" value={report.in_progress_count} note="Active service sessions" icon="activity" /><MetricCard label="Completed" value={report.completed_count} note="Completed services" icon="check" /></section>
      <div className="dashboard-lower">
        <section className="panel"><PanelHeading eyebrow="WAIT-TIME ANALYTICS" title="Average waiting time" detail="Mean arrival-to-service-start time for in-progress and completed tokens with valid timestamps." icon="clock" /><div className="report-highlight"><strong>{report.average_wait_min === null ? "No valid data" : `${report.average_wait_min.toFixed(1)} min`}</strong><span>{report.waiting_time_sample_count} valid started visits; waiting and called tokens are not included.</span><div className="report-data-quality"><span>Excluded · missing {report.waiting_time_excluded.missing_timestamp}</span><span>invalid {report.waiting_time_excluded.invalid_timestamp}</span><span>negative {report.waiting_time_excluded.negative_duration}</span></div></div></section>
        <section className="panel"><PanelHeading eyebrow="OVERALL UTILIZATION" title="Counter utilization" detail={`${report.busy_counters} busy of ${report.open_counters} open counters right now.`} icon="bars" /><div className="report-highlight"><strong>{report.utilization_pct.toFixed(0)}%</strong><span>currently active counter capacity</span></div></section>
      </div>
      <section className="panel report-table-panel"><PanelHeading eyebrow="COUNTER BREAKDOWN" title="Utilization by counter" detail="Live waiting, active, and completed service counts." icon="users" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Counter</th><th>Availability</th><th>Waiting</th><th>In progress</th><th>Completed</th><th>Utilization</th></tr></thead><tbody>{report.counters.map((counter) => <tr key={counter.counter_id}><td>{counter.name}</td><td><StatusBadge status={counter.status} /></td><td>{counter.waiting_count}</td><td>{counter.in_progress_count}</td><td>{counter.completed_count}</td><td><div className="utilization-cell"><span className="utilization-track"><i style={{ width: `${counter.utilization_pct}%` }} /></span><strong>{counter.utilization_pct}%</strong></div></td></tr>)}</tbody></table></div></section>
    </>
  );
}

function TokenTable({ tokens, services }: { tokens: Token[]; services: Service[] }) {
  if (!tokens.length) return <div className="empty-state-compact">No patient tokens to display.</div>;
  return <div className="table-scroll"><table className="data-table token-data-table"><thead><tr><th>Token</th><th>Patient</th><th>Service</th><th>Counter</th><th>Status</th><th>Est. wait</th></tr></thead><tbody>{tokens.map((token) => <tr key={token.token_id}><td><strong>{token.token_id}</strong></td><td>{token.customer_name}</td><td>{serviceName(token.service_id, services)}</td><td>{token.counter_id ? `Counter ${token.counter_id}` : "—"}</td><td><StatusBadge status={token.status} /></td><td>{token.status === "S3_WAITING" && token.eta_min !== null ? `${Math.max(0, Math.round(token.eta_min))} min` : "—"}</td></tr>)}</tbody></table></div>;
}

function MetricCard({ label, value, note, icon }: { label: string; value: string | number; note: string; icon: IconName }) {
  return <article className="metric-card"><div className="metric-card-top"><span>{label}</span><span className="metric-icon"><Icon name={icon} size={17} /></span></div><strong>{value}</strong><small>{note}</small></article>;
}

function MetricSkeleton() {
  return <div className="metric-card metric-skeleton"><span /><strong /><small /></div>;
}

function CounterSkeleton() {
  return <div className="panel counter-card counter-skeleton"><span /><span /><span /><span /></div>;
}

function InspectorSkeleton({ wide = false }: { wide?: boolean }) {
  return <div className={`panel inspector-card inspector-skeleton ${wide ? "inspector-wide" : ""}`}><span /><span /><span /><span /></div>;
}

function PanelHeading({ eyebrow, title, detail, icon }: { eyebrow: string; title: string; detail: string; icon: IconName }) {
  return <div className="panel-heading"><div className="panel-heading-icon"><Icon name={icon} size={17} /></div><div><div className="panel-eyebrow">{eyebrow}</div><h2>{title}</h2><p>{detail}</p></div></div>;
}

function StatusBadge({ status }: { status: string }) {
  const tone = status === "OPEN" || status === "S5_IN_PROGRESS" ? "badge-positive" : status === "S6_COMPLETED" ? "badge-complete" : status === "CLOSED" ? "badge-muted" : "badge-waiting";
  return <span className={`status-badge ${tone}`}>{statusLabel(status)}</span>;
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

export default App;
