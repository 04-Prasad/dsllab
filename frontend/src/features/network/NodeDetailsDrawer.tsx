"use client";

import React from "react";
import Link from "next/link";
import {
  X, ExternalLink, AlertTriangle, Zap, Network,
  TrendingUp, TrendingDown, Shield, Activity,
} from "lucide-react";
import type { EnrichedGraphNode } from "./types";

interface NodeDetailsDrawerProps {
  node: EnrichedGraphNode | null;
  onClose: () => void;
}

const RISK_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-950 text-red-400 border-red-800",
  HIGH:     "bg-orange-950 text-orange-400 border-orange-800",
  MEDIUM:   "bg-yellow-950 text-yellow-400 border-yellow-800",
  LOW:      "bg-emerald-950 text-emerald-400 border-emerald-800",
};

const ROLE_BADGE: Record<string, string> = {
  HUB:                 "bg-indigo-950 text-indigo-300 border-indigo-800",
  BRIDGE:              "bg-blue-950 text-blue-300 border-blue-800",
  MULE:                "bg-orange-950 text-orange-300 border-orange-800",
  RING_MEMBER:         "bg-purple-950 text-purple-300 border-purple-800",
  SUSPICIOUS_NEIGHBOUR:"bg-yellow-950 text-yellow-300 border-yellow-800",
  NORMAL:              "bg-gray-900 text-gray-400 border-gray-700",
};

const ROLE_DESC: Record<string, string> = {
  HUB:                 "Major transaction centre — high degree & PageRank",
  BRIDGE:              "Connects otherwise separate clusters",
  MULE:                "Rapid incoming → outgoing fund forwarding",
  RING_MEMBER:         "Participates in a detected circular money flow",
  SUSPICIOUS_NEIGHBOUR:"High concentration of risky counterparties",
  NORMAL:              "Normal account behaviour",
};

const EWS_COLOURS: Record<string, string> = {
  "EWS-001": "text-yellow-400",
  "EWS-002": "text-red-400",
  "EWS-003": "text-orange-400",
  "EWS-004": "text-purple-400",
  "EWS-005": "text-red-500",
  "EWS-006": "text-amber-400",
  "EWS-007": "text-pink-400",
};

const EWS_LABELS: Record<string, string> = {
  "EWS-001": "Velocity Spike",
  "EWS-002": "Fan-In Spike",
  "EWS-003": "Fan-Out Spike",
  "EWS-004": "Dormancy Burst",
  "EWS-005": "Rapid Fund Movement",
  "EWS-006": "High-Risk Neighbourhood",
  "EWS-007": "Circular Flow",
};

function fmt(n: number): string {
  return n.toLocaleString("en-IN");
}

function fmtCurrency(n: number): string {
  if (n >= 1_000_000) return `₹${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `₹${(n / 1_000).toFixed(0)}K`;
  return `₹${fmt(n)}`;
}

export default function NodeDetailsDrawer({ node, onClose }: NodeDetailsDrawerProps) {
  if (!node) return null;

  const riskPct = Math.round(node.risk_score);
  const riskBar =
    node.risk_level === "CRITICAL" ? "bg-red-500" :
    node.risk_level === "HIGH"     ? "bg-orange-500" :
    node.risk_level === "MEDIUM"   ? "bg-yellow-500" : "bg-emerald-500";

  return (
    <aside
      className="w-80 min-w-[18rem] bg-[#0d111e] border-l border-gray-800 flex flex-col overflow-y-auto"
      style={{ height: "100%" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 sticky top-0 bg-[#0d111e] z-10">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-indigo-400" />
          <span className="font-mono font-bold text-white text-base">{node.id}</span>
          {node.alert_id && (
            <span className="animate-pulse w-2 h-2 rounded-full bg-red-500" title="Active Alert" />
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-white transition-colors"
          aria-label="Close panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 px-4 py-4 space-y-5 text-xs">

        {/* Risk Score */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <span
              className={`px-2 py-0.5 rounded-full border font-bold text-[11px] uppercase ${RISK_BADGE[node.risk_level] ?? RISK_BADGE.LOW}`}
            >
              {node.risk_level}
            </span>
            <span className="font-mono font-bold text-white text-sm">{riskPct} / 100</span>
          </div>
          <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${riskBar} transition-all duration-500`}
              style={{ width: `${riskPct}%` }}
            />
          </div>
          <div className="text-gray-500">{node.account_type}</div>
        </section>

        {/* Role */}
        <section>
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Graph Role
          </div>
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border font-semibold ${ROLE_BADGE[node.role] ?? ROLE_BADGE.NORMAL}`}
          >
            <Shield className="w-3 h-3" />
            {node.role.replace("_", " ")}
          </div>
          <p className="text-gray-500 mt-1.5">{ROLE_DESC[node.role]}</p>
          {node.ring_id && (
            <div className="mt-1.5 flex items-center gap-1.5 text-purple-400 font-mono">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              {node.ring_id}
            </div>
          )}
        </section>

        {/* Active Alert */}
        {node.alert_id && (
          <section className="p-3 bg-red-950/40 border border-red-800/50 rounded-lg space-y-2">
            <div className="flex items-center gap-1.5 text-red-400 font-semibold">
              <AlertTriangle className="w-3.5 h-3.5" />
              Active Alert
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400 font-mono">{node.alert_id}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${RISK_BADGE[node.alert_severity ?? "HIGH"] ?? RISK_BADGE.HIGH}`}
              >
                {node.alert_severity}
              </span>
            </div>
            <Link
              href={`/alerts`}
              className="mt-1 flex items-center gap-1 text-red-400 hover:text-red-300 font-medium"
            >
              Open Alert Queue <ExternalLink className="w-3 h-3" />
            </Link>
          </section>
        )}

        {/* EWS Signals */}
        {node.ews_codes.length > 0 && (
          <section>
            <div className="flex items-center gap-1.5 text-amber-400 font-semibold mb-2">
              <Zap className="w-3.5 h-3.5" />
              EWS Signals ({node.ews_count})
            </div>
            <div className="space-y-1.5">
              {node.ews_codes.map((code, i) => (
                <div
                  key={code}
                  className="flex items-center gap-2 p-2 bg-gray-900 rounded border border-gray-800"
                >
                  <span className={`font-mono font-bold ${EWS_COLOURS[code] ?? "text-amber-400"}`}>
                    {code}
                  </span>
                  <span className="text-gray-300">
                    {node.ews_types[i] ?? EWS_LABELS[code] ?? code}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Transaction Stats */}
        <section>
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Transaction Stats
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-900 rounded-lg p-2.5 border border-gray-800">
              <div className="flex items-center gap-1 text-indigo-400 mb-1">
                <TrendingDown className="w-3 h-3" />
                <span className="text-[10px] uppercase tracking-wider">Incoming</span>
              </div>
              <div className="font-mono font-bold text-white">{fmt(node.incoming_count)}</div>
              <div className="text-gray-500">{fmtCurrency(node.incoming_total)}</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-2.5 border border-gray-800">
              <div className="flex items-center gap-1 text-orange-400 mb-1">
                <TrendingUp className="w-3 h-3" />
                <span className="text-[10px] uppercase tracking-wider">Outgoing</span>
              </div>
              <div className="font-mono font-bold text-white">{fmt(node.outgoing_count)}</div>
              <div className="text-gray-500">{fmtCurrency(node.outgoing_total)}</div>
            </div>
          </div>
        </section>

        {/* Graph Intelligence */}
        <section>
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Graph Intelligence
          </div>
          <div className="space-y-1.5">
            {[
              { label: "PageRank", value: node.pagerank.toFixed(5) },
              { label: "In Degree", value: node.in_degree },
              { label: "Out Degree", value: node.out_degree },
              { label: "Betweenness", value: node.betweenness.toFixed(4) },
              { label: "Risky Neighbours %", value: `${Math.round(node.risky_neighbor_ratio * 100)}%` },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-gray-400">
                <span>{label}</span>
                <span className="font-mono text-gray-200">{value}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Actions */}
        <section className="space-y-2 pt-1">
          <Link
            href={`/accounts/${node.id}`}
            className="w-full flex items-center justify-center gap-1.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold transition-colors"
          >
            Investigate Account <ExternalLink className="w-3.5 h-3.5" />
          </Link>
          <Link
            href={`/accounts/${node.id}`}
            className="w-full flex items-center justify-center gap-1.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg font-medium transition-colors border border-gray-700"
          >
            View Transactions <Activity className="w-3.5 h-3.5" />
          </Link>
        </section>
      </div>
    </aside>
  );
}
