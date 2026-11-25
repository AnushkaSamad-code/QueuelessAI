import type {
  AuthResponse,
  Counter,
  InspectorSnapshot,
  ReportSummary,
  SearchComparison,
  Service,
  StateSnapshot,
  Token,
  TokenResponse,
} from "./types";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
export const API_URL = (configuredApiUrl || "http://localhost:8000").replace(
  /\/+$/,
  "",
);

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const token = localStorage.getItem("queueless-access-token");
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      `Could not connect to the API at ${API_URL}. Check that the backend is running.`,
      0,
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function signup(input: {
  full_name: string;
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCurrentUser(): Promise<AuthResponse["user"]> {
  return request<AuthResponse["user"]>("/api/auth/me");
}

export function logout(): Promise<{ logged_out: boolean }> {
  return request<{ logged_out: boolean }>("/api/auth/logout", { method: "POST" });
}

export async function getServices(): Promise<Service[]> {
  const services = await request<Array<Record<string, unknown>>>("/api/services");
  return services.map((service) => ({
    service_id: String(service.service_id),
    id: String(service.service_id),
    name: String(service.name),
    category: String(service.category),
    duration: String(service.duration),
    description: String(service.description),
    required_stages: Array.isArray(service.required_stages)
      ? service.required_stages.map(String)
      : [],
    estimated_durations_min:
      (service.estimated_durations_min as Record<string, number> | undefined) ?? {},
  }));
}

export function getState(): Promise<StateSnapshot> {
  return request<StateSnapshot>("/api/state");
}

export function getInspector(): Promise<InspectorSnapshot> {
  return request<InspectorSnapshot>("/api/ds/inspect");
}

export function getCounters(): Promise<Counter[]> {
  return request<Counter[]>("/api/counters");
}

export function getReports(): Promise<ReportSummary> {
  return request<ReportSummary>("/api/reports/summary");
}

export function bookToken(input: {
  customer_name: string;
  service_id: string;
  priority_level: "STANDARD" | "APPOINTMENT" | "PRIORITY";
}): Promise<{ token: Token; recommendation: { optimal_path: string[]; total_cost: number } }> {
  return request("/api/tokens/book", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function findToken(tokenId: string): Promise<TokenResponse> {
  return request<TokenResponse>(`/api/tokens/${encodeURIComponent(tokenId)}`);
}

export function callNext(counterId: string): Promise<{ token: Token }> {
  return request<{ token: Token }>(
    `/api/counters/${encodeURIComponent(counterId)}/next`,
    { method: "POST" },
  );
}

export function startService(counterId: string): Promise<{ token: Token }> {
  return request<{ token: Token }>(
    `/api/counters/${encodeURIComponent(counterId)}/start`,
    { method: "POST" },
  );
}

export function completeService(counterId: string): Promise<{ token: Token }> {
  return request<{ token: Token }>(
    `/api/counters/${encodeURIComponent(counterId)}/complete`,
    { method: "POST" },
  );
}

export function createService(input: {
  service_id: string;
  name: string;
  category: string;
  estimated_durations_min: Record<string, number>;
}): Promise<unknown> {
  return request("/api/services", { method: "POST", body: JSON.stringify(input) });
}

export function updateService(
  serviceId: string,
  input: {
    name: string;
    category: string;
    estimated_durations_min: Record<string, number>;
  },
): Promise<unknown> {
  return request(`/api/services/${encodeURIComponent(serviceId)}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function createCounter(input: {
  counter_id: string;
  name: string;
  status: "OPEN" | "CLOSED";
  supported_services: string[];
}): Promise<Counter> {
  return request<Counter>("/api/counters", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCounter(
  counterId: string,
  input: {
    name: string;
    status: "OPEN" | "CLOSED";
    supported_services: string[];
  },
): Promise<Counter> {
  return request<Counter>(`/api/counters/${encodeURIComponent(counterId)}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function compareRoute(serviceId: string): Promise<SearchComparison> {
  return request<SearchComparison>("/api/ai/compare", {
    method: "POST",
    body: JSON.stringify({ service_id: serviceId }),
  });
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    S3_WAITING: "Waiting",
    S4_COUNTER_ASSIGNED: "Called",
    S5_IN_PROGRESS: "In progress",
    S6_COMPLETED: "Completed",
  };
  return labels[status] ?? status.replaceAll("_", " ").toLowerCase();
}
