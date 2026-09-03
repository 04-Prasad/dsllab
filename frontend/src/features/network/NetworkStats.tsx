"use client";

import React from "react";
import { Users, AlertTriangle, GitBranch, Network } from "lucide-react";
import type { GraphStats } from "./types";

interface NetworkStatsProps {
  stats: GraphStats | null;
  loading: boolean;
}

const STAT_CARDS = [
  {
    key: "total_nodes" as keyof GraphStats,
    label: "Accounts",
    icon: Users,
    color: "text-[#38bdf8]",
    bg: "bg-[#0f172a]/90 border-[#1e293b]",
  },
  {
    key: "total_edges" as keyof GraphStats,
    label: "Transactions",
    icon: GitBranch,
    color: "text-indigo-400",
    bg: "bg-[#0f172a]/90 border-[#1e293b]",
  },
  {
    key: "fraud_nodes" as keyof GraphStats,
    label: "Suspicious",
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-[#0f172a]/90 border-[#1e293b]",
  },
  {
    key: "rings" as keyof GraphStats,
    label: "Fraud Clusters",
    icon: Network,
    color: "text-purple-400",
    bg: "bg-[#0f172a]/90 border-[#1e293b]",
  },
];

export default function NetworkStats({ stats, loading }: NetworkStatsProps) {
  return (
    <div className="flex gap-2.5">
      {STAT_CARDS.map(({ key, label, icon: Icon, color, bg }) => (
        <div
          key={key}
          className={`px-3 py-1.5 rounded-lg border ${bg} flex items-center gap-2.5 shadow-md`}
        >
          <Icon className={`w-3.5 h-3.5 ${color} shrink-0`} />
          <div className="flex items-baseline gap-1.5">
            <span className={`text-sm font-bold font-mono ${color}`}>
              {loading ? (
                <span className="inline-block w-6 h-3 bg-[#1e293b] rounded animate-pulse" />
              ) : (
                (stats?.[key] ?? 0).toLocaleString()
              )}
            </span>
            <span className="text-[10px] text-[#94a3b8] font-eyebrow uppercase">{label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
