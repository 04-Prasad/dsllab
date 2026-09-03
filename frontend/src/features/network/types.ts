// GraphGuard 3D Network — TypeScript types (mirror backend EnrichedGraph* schemas)

export interface EnrichedGraphNode {
  id: string;
  label: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  account_type: string;
  role: "NORMAL" | "HUB" | "BRIDGE" | "MULE" | "RING_MEMBER" | "SUSPICIOUS_NEIGHBOUR";
  ring_id: string | null;
  ews_codes: string[];
  ews_types: string[];
  ews_count: number;
  alert_id: string | null;
  alert_severity: string | null;
  incoming_count: number;
  outgoing_count: number;
  incoming_total: number;
  outgoing_total: number;
  pagerank: number;
  in_degree: number;
  out_degree: number;
  betweenness: number;
  risky_neighbor_ratio: number;
  is_fraud: boolean;
  // Three.js runtime (added by force-graph)
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
}

export interface EnrichedGraphEdge {
  source: string | EnrichedGraphNode;
  target: string | EnrichedGraphNode;
  amount: number;
  count: number;
  tx_id: string | null;
}

export interface GraphStats {
  total_nodes: number;
  fraud_nodes: number;
  total_edges: number;
  rings: number;
  critical_nodes: number;
  high_nodes: number;
}

export interface EnrichedGraphNetworkOut {
  nodes: EnrichedGraphNode[];
  edges: EnrichedGraphEdge[];
  stats: GraphStats;
}

export interface NetworkFilters {
  riskThreshold: number;
  fraudOnly: boolean;
  ringMembersOnly: boolean;
  hasEws: boolean;
  hubsOnly: boolean;
}

export const DEFAULT_FILTERS: NetworkFilters = {
  riskThreshold: 0,
  fraudOnly: false,
  ringMembersOnly: false,
  hasEws: false,
  hubsOnly: false,
};

export type QuickFilter = "ALL" | "FRAUD_ONLY" | "RING_MEMBERS" | "HIGH_RISK";

// Detective Tour stop definition
export interface TourStop {
  id: number;
  targetAccount: string;
  title: string;
  body: string;
  highlightEws?: string[];
}

export const DETECTIVE_TOUR_STOPS: TourStop[] = [
  {
    id: 1,
    targetAccount: "A102",
    title: "Suspicious Hub Detected",
    body: "Account A102 appears at the centre of an unusual transaction cluster. High degree and PageRank signal it may be orchestrating funds movement.",
  },
  {
    id: 2,
    targetAccount: "A102",
    title: "Fan-In Anomaly: 35 Senders",
    body: "35 different accounts transferred approximately ₹9,500 each to A102 within a 20-minute window — a classic mule aggregation pattern.",
    highlightEws: ["EWS-002"],
  },
  {
    id: 3,
    targetAccount: "A102",
    title: "Rapid Fund Dispersion",
    body: "Over 91% of the incoming funds were immediately forwarded outward to just two downstream accounts — A301 and A302.",
    highlightEws: ["EWS-005"],
  },
  {
    id: 4,
    targetAccount: "A102",
    title: "3 Early Warning Signals Triggered",
    body: "GraphGuard's rule engine fired: FAN_IN_SPIKE, VELOCITY_SPIKE, and RAPID_FUND_MOVEMENT simultaneously on this account.",
    highlightEws: ["EWS-001", "EWS-002", "EWS-005"],
  },
  {
    id: 5,
    targetAccount: "A102",
    title: "CRITICAL — Risk Score: 88/100",
    body: "The multi-signal risk fusion engine fused GNN probability, EWS score, and graph context metrics into a final score of 88/100 — CRITICAL.",
  },
];
