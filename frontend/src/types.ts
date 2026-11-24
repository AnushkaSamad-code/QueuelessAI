export type PriorityLevel = "STANDARD" | "APPOINTMENT" | "PRIORITY";
export type PortalView = "booking" | "staff" | "inspector";
export type Theme = "dark" | "light";

export interface Token {
  token_id: string;
  customer_name: string;
  service_id: string;
  priority_level: PriorityLevel;
  status: string;
  counter_id: string | null;
  assigned_path: string[];
  eta_min: number;
  arrival_timestamp: string;
  updated_at: string;
}

export interface Counter {
  counter_id: string;
  name: string;
  status: "OPEN" | "CLOSED" | string;
  queue_length: number;
  current_token_id: string | null;
}

export interface StateSnapshot {
  counters: Counter[];
  active_tokens: Token[];
  queues: Record<string, Token[]>;
  stats: {
    active_token_count: number;
    waiting_count: number;
    in_progress_count: number;
    completed_count: number;
    average_eta_min: number;
    priority_queue_size: number;
  };
}

export interface BookResponse {
  token: Token;
  recommendation: {
    counter_id: string;
    optimal_path: string[];
    total_cost: number;
  };
}

export interface TokenResponse {
  token: Token;
  optimal_path: string[];
  eta_min: number;
}

export interface SearchResponse {
  algorithm: string;
  optimal_path: string[];
  total_cost: number | null;
  nodes_expanded: number;
  trace_steps: Array<Record<string, unknown>>;
  graph?: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
}

export interface ArraySnapshot {
  capacity: number;
  size: number;
  elements: Token[];
  slots: Array<Token | null>;
}

export interface HeapEntry {
  index: number;
  token_id: string;
  base_priority: number;
  effective_priority: number;
  arrival_timestamp: string;
}

export interface InspectorSnapshot {
  token_array: ArraySnapshot;
  counter_linked_lists: Record<string, Token[]>;
  priority_queue: HeapEntry[];
  bst: {
    inorder: Token[];
    preorder: Token[];
    postorder: Token[];
  };
}

export interface Service {
  id: string;
  name: string;
  category: string;
  duration: string;
  description: string;
}
