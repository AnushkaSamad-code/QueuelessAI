import type {
  BookResponse,
  InspectorSnapshot,
  PriorityLevel,
  SearchResponse,
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
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
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

export function getState(): Promise<StateSnapshot> {
  return request<StateSnapshot>("/api/state");
}

export function getInspector(): Promise<InspectorSnapshot> {
  return request<InspectorSnapshot>("/api/ds/inspect");
}

export function bookToken(input: {
  customer_name: string;
  service_id: string;
  priority_level: PriorityLevel;
}): Promise<BookResponse> {
  return request<BookResponse>("/api/tokens/book", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function findToken(tokenId: string): Promise<TokenResponse> {
  return request<TokenResponse>(`/api/tokens/${encodeURIComponent(tokenId)}`);
}

export function advanceCounter(counterId: string): Promise<{ token: Token }> {
  return request<{ token: Token }>(`/api/counters/${encodeURIComponent(counterId)}/next`, {
    method: "POST",
  });
}

export function searchRoute(algorithm: "BFS" | "UCS" | "A*"): Promise<SearchResponse> {
  return request<SearchResponse>("/api/ai/search", {
    method: "POST",
    body: JSON.stringify({ algorithm }),
  });
}
