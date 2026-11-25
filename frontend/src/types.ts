export type PriorityLevel = "STANDARD" | "APPOINTMENT" | "PRIORITY";
export type UserRole = "CUSTOMER" | "STAFF" | "ADMIN";
export type Theme = "dark" | "light";
export type StaffView =
  | "Dashboard"
  | "Customer Booking"
  | "Counter Console"
  | "Queue Management"
  | "Services & Counters"
  | "AI Search & Graph Visualizer"
  | "DS Visualizer"
  | "Reports & Analytics";

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

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
  service_started_at?: string | null;
  completed_at?: string | null;
}

export interface Counter {
  counter_id: string;
  name: string;
  status: "OPEN" | "CLOSED" | string;
  queue_length: number;
  current_token_id: string | null;
  supported_services: string[];
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
    estimated_wait_min: number;
    route_cost: number;
  };
}

export interface TokenResponse {
  token: Token;
  optimal_path: string[];
  eta_min: number;
}

export interface SearchResult {
  algorithm: "BFS" | "UCS" | "A*";
  optimal_path: string[];
  total_cost: number | null;
  nodes_expanded: number;
  trace_steps: SearchTraceStep[];
  heuristic_values?: Record<string, number>;
}

export interface SearchComparison {
  service_id: string;
  graph: {
    nodes: SearchGraphNode[];
    edges: SearchGraphEdge[];
  };
  results: Record<"BFS" | "UCS" | "A*", SearchResult>;
  problem_formulation: {
    initial_state: string;
    goal_state: string;
    actions: string[];
    transition_model: string;
    path_cost_function: string;
    heuristic_function: string;
    goal_test: string;
  };
}

export interface SearchTraceStep {
  step: number;
  current_node: string;
  frontier: string[];
  visited: string[];
  action: string;
}

export interface SearchGraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  lifecycle_state: string;
  counter_id: string | null;
  stage: string | null;
}

export interface SearchGraphEdge {
  source: string;
  target: string;
  action: string;
  cost: number;
  source_x: number;
  source_y: number;
  target_x: number;
  target_y: number;
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
  service_id: string;
  name: string;
  category: string;
  duration: string;
  description: string;
  required_stages: string[];
  estimated_durations_min: Record<string, number>;
}

export interface ReportSummary {
  total_appointments: number;
  waiting_count: number;
  in_progress_count: number;
  completed_count: number;
  average_wait_min: number;
  open_counters: number;
  busy_counters: number;
  utilization_pct: number;
  counters: Array<{
    counter_id: string;
    name: string;
    status: string;
    waiting_count: number;
    in_progress_count: number;
    completed_count: number;
    utilization_pct: number;
  }>;
}
