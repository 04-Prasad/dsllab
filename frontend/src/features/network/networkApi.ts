// GraphGuard 3D Network — API client for /api/v1/graph/network

import type { EnrichedGraphNetworkOut } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface NetworkQueryParams {
  account_id?: string;
  risk_threshold?: number;
  fraud_only?: boolean;
  ring_members_only?: boolean;
  limit?: number;
}

export async function fetchNetworkGraph(
  params: NetworkQueryParams = {}
): Promise<EnrichedGraphNetworkOut> {
  const qs = new URLSearchParams();
  if (params.account_id) qs.set("account_id", params.account_id);
  if (params.risk_threshold !== undefined && params.risk_threshold > 0)
    qs.set("risk_threshold", String(params.risk_threshold));
  if (params.fraud_only) qs.set("fraud_only", "true");
  if (params.ring_members_only) qs.set("ring_members_only", "true");
  if (params.limit) qs.set("limit", String(params.limit));

  const url = `${API_BASE}/graph/network${qs.toString() ? `?${qs}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });

  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`Graph API error [${res.status}]: ${msg}`);
  }

  return res.json() as Promise<EnrichedGraphNetworkOut>;
}
