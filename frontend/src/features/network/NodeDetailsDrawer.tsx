"use client";

import React from "react";
import Link from "next/link";
import {
  X, ExternalLink, AlertTriangle, Zap, Network,
  TrendingUp, TrendingDown, Shield, Activity,
  ArrowDownRight, ArrowUpRight, Cpu
} from "lucide-react";
import type { EnrichedGraphNode } from "./types";

interface NodeDetailsDrawerProps {
  node: EnrichedGraphNode | null;
  onClose: () => void;
}

const RISK_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-950/80 text-red-400 border-red-800 shadow-[0_0_12px_rgba(239,68,68,0.3)]",
  HIGH:     "bg-orange-950/80 text-orange-400 border-orange-800 shadow-[0_0_12px_rgba(249,115,22,0.3)]",
  MEDIUM:   "bg-amber-950/80 text-amber-400 border-amber-800",
  LOW:      "bg-emerald-950/80 text-emerald-400 border-emerald-800",
};

const ROLE_BADGE: Record<string, string> = {
  HUB:                 "bg-indigo-950/80 text-indigo-300 border-indigo-800",
  BRIDGE:              "bg-blue-950/80 text-blue-300 border-blue-800",
  MULE:                "bg-orange-950/80 text-orange-300 border-orange-800",
  RING_MEMBER:         "bg-purple-950/80 text-purple-300 border-purple-800",
  SUSPICIOUS_NEIGHBOUR:"bg-amber-950/80 text-amber-300 border-amber-800",
  NORMAL:              "bg-[#0f172a] text-[#94a3b8] border-[#1e293b]",
};

const EWS_BADGE_STYLE: Record<string, { label: string; style: string }> = {
  "EWS-001": { label: "HIGH VELOCITY", style: "bg-amber-950/60 text-amber-300 border-amber-800/80" },
  "EWS-002": { label: "FAN-IN", style: "bg-red-950/60 text-red-300 border-red-800/80" },
  "EWS-003": { label: "FAN-OUT", style: "bg-orange-950/60 text-orange-300 border-orange-800/80" },
  "EWS-004": { label: "DORMANCY BURST", style: "bg-purple-950/60 text-purple-300 border-purple-800/80" },
  "EWS-005": { label: "RAPID OUTFLOW", style: "bg-red-950/80 text-red-400 border-red-700" },
  "EWS-006": { label: "RISKY NEIGHBOUR", style: "bg-amber-950/60 text-amber-300 border-amber-800/80" },
  "EWS-007": { label: "CIRCULAR FLOW", style: "bg-pink-950/60 text-pink-300 border-pink-800/80" },
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
  const riskColorHex =
    node.risk_level === "CRITICAL" ? "#ef4444" :
    node.risk_level === "HIGH"     ? "#f97316" :
    node.risk_level === "MEDIUM"   ? "#facc15" : "#22c55e";

  return (
    <aside
      className="w-88 min-w-[21rem] bg-[#020617]/95 backdrop-blur-xl border-l border-[#1e293b] flex flex-col overflow-y-auto text-[#f8fafc] z-20 shadow-2xl"
      style={{ height: "100%" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#1e293b] sticky top-0 bg-[#020617]/95 backdrop-blur-md z-10">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-[#38bdf8]/10 border border-[#38bdf8]/20">
            <Network className="w-4 h-4 text-[#38bdf8]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-white text-base tracking-tight">{node.id}</span>
              {node.alert_id && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                </span>
              )}
            </div>
            <span className="text-[10px] font-mono text-[#64748b] uppercase tracking-wider">{node.account_type}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-[#64748b] hover:text-white hover:bg-[#1e293b] rounded-lg transition-colors cursor-pointer"
          aria-label="Close panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 px-5 py-5 space-y-6 text-xs">

        {/* Risk Score Dial & Status Card */}
        <section className="glass-card p-4 rounded-xl bg-[#0f172a]/70 border border-[#1e293b] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-eyebrow text-[#94a3b8]">ACCOUNT RISK INDEX</span>
            <span
              className={`px-2.5 py-0.5 rounded-full border text-[10px] font-bold tracking-wider uppercase ${RISK_BADGE[node.risk_level] ?? RISK_BADGE.LOW}`}
            >
              {node.risk_level}
            </span>
          </div>

          <div className="flex items-end justify-between py-1">
            <div>
              <div className="text-3xl font-display font-bold text-white tracking-tight flex items-baseline gap-1">
                {riskPct}
                <span className="text-xs text-[#64748b] font-normal">/ 100</span>
              </div>
              <p className="text-[11px] text-[#94a3b8] mt-0.5">
                {riskPct >= 80 ? "Severe fraud signature detected" : riskPct >= 60 ? "Elevated suspicious indicators" : "Low risk profile"}
              </p>
            </div>
            {/* Circular Risk Gauge Indicator */}
            <div className="relative w-12 h-12 flex items-center justify-center">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle cx="24" cy="24" r="18" stroke="#1e293b" strokeWidth="4" fill="transparent" />
                <circle
                  cx="24" cy="24" r="18"
                  stroke={riskColorHex}
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray="113"
                  strokeDashoffset={113 - (113 * riskPct) / 100}
                  strokeLinecap="round"
                />
              </svg>
              <Shield className="w-4 h-4 absolute text-white opacity-80" />
            </div>
          </div>

          {/* Progress bar */}
          <div className="h-1.5 w-full bg-[#1e293b] rounded-full overflow-hidden">
            <div
              className="h-full transition-all duration-700 rounded-full"
              style={{ width: `${riskPct}%`, backgroundColor: riskColorHex }}
            />
          </div>
        </section>

        {/* Fraud Pattern Badges */}
        {node.ews_codes.length > 0 && (
          <section className="space-y-2">
            <div className="text-[10px] font-eyebrow text-[#94a3b8] flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-amber-400" />
              <span>DETECTED FRAUD PATTERNS</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {node.ews_codes.map((code) => {
                const info = EWS_BADGE_STYLE[code] || { label: code, style: "bg-[#1e293b] text-[#94a3b8]" };
                return (
                  <span
                    key={code}
                    className={`px-2.5 py-1 rounded-md text-[10px] font-bold border tracking-wide uppercase ${info.style}`}
                  >
                    [ {info.label} ]
                  </span>
                );
              })}
            </div>
          </section>
        )}

        {/* Graph Role */}
        <section className="p-3.5 bg-[#0f172a]/60 border border-[#1e293b] rounded-xl space-y-2">
          <div className="text-[10px] font-eyebrow text-[#94a3b8]">GRAPHSAGE NODE CLASSIFICATION</div>
          <div className="flex items-center justify-between">
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-bold uppercase ${ROLE_BADGE[node.role] ?? ROLE_BADGE.NORMAL}`}>
              <Cpu className="w-3 h-3" />
              {node.role.replace("_", " ")}
            </div>
            {node.ring_id && (
              <span className="font-mono text-[11px] text-purple-400 font-bold px-2 py-0.5 bg-purple-950/60 border border-purple-800/60 rounded-md">
                {node.ring_id}
              </span>
            )}
          </div>
        </section>

        {/* Active Investigator Alert */}
        {node.alert_id && (
          <section className="p-3.5 bg-red-950/30 border border-red-800/40 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-red-400 font-semibold text-[11px]">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                Active Fraud Alert
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${RISK_BADGE[node.alert_severity ?? "HIGH"]}`}>
                {node.alert_severity}
              </span>
            </div>
            <div className="flex items-center justify-between text-[#94a3b8] font-mono text-[11px]">
              <span>ID: {node.alert_id}</span>
              <Link
                href="/alerts"
                className="text-red-400 hover:text-red-300 hover:underline flex items-center gap-1 font-medium"
              >
                Triage Queue <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </section>
        )}

        {/* Account Behaviour */}
        <section className="space-y-2.5">
          <div className="text-[10px] font-eyebrow text-[#94a3b8] flex items-center justify-between">
            <span>ACCOUNT BEHAVIOUR</span>
            <span>TRANSACTION FLOWS</span>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 bg-[#0f172a]/60 border border-[#1e293b] rounded-xl space-y-1">
              <div className="flex items-center justify-between text-[10px] text-[#94a3b8] font-eyebrow">
                <span>INCOMING</span>
                <ArrowDownRight className="w-3 h-3 text-[#38bdf8]" />
              </div>
              <div className="font-mono font-bold text-white text-base">{fmt(node.incoming_count)} tx</div>
              <div className="text-[11px] font-mono text-[#38bdf8]">{fmtCurrency(node.incoming_total)}</div>
            </div>

            <div className="p-3 bg-[#0f172a]/60 border border-[#1e293b] rounded-xl space-y-1">
              <div className="flex items-center justify-between text-[10px] text-[#94a3b8] font-eyebrow">
                <span>OUTGOING</span>
                <ArrowUpRight className="w-3 h-3 text-orange-400" />
              </div>
              <div className="font-mono font-bold text-white text-base">{fmt(node.outgoing_count)} tx</div>
              <div className="text-[11px] font-mono text-orange-400">{fmtCurrency(node.outgoing_total)}</div>
            </div>
          </div>
        </section>

        {/* Graph Intelligence */}
        <section className="space-y-2">
          <div className="text-[10px] font-eyebrow text-[#94a3b8]">NETWORK INTELLIGENCE & METRICS</div>
          <div className="p-3.5 bg-[#0f172a]/60 border border-[#1e293b] rounded-xl space-y-2">
            {[
              { label: "PageRank Score", value: node.pagerank.toFixed(5) },
              { label: "In Degree / Out Degree", value: `${node.in_degree} in / ${node.out_degree} out` },
              { label: "Betweenness Centrality", value: node.betweenness.toFixed(4) },
              { label: "Risky Counterparty Ratio", value: `${Math.round(node.risky_neighbor_ratio * 100)}%` },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between items-center text-[11px] border-b border-[#1e293b]/60 pb-1.5 last:border-0 last:pb-0">
                <span className="text-[#94a3b8]">{label}</span>
                <span className="font-mono font-semibold text-[#f8fafc]">{value}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Actions */}
        <section className="space-y-2 pt-2">
          <Link
            href={`/accounts/${node.id}`}
            className="btn-void-violet w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
          >
            <span>Investigate Account {node.id}</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
          <Link
            href={`/accounts/${node.id}`}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#0f172a] hover:bg-[#1e293b] text-[#f8fafc] rounded-lg text-xs font-medium border border-[#1e293b] transition-colors cursor-pointer"
          >
            <Activity className="w-3.5 h-3.5 text-[#38bdf8]" />
            <span>View Full Transaction Ledger</span>
          </Link>
        </section>
      </div>
    </aside>
  );
}
