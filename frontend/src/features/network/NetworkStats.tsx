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
    color: "text-indigo-400",
    bg: "bg-indigo-950/40 border-indigo-900/50",
  },
  {
    key: "fraud_nodes" as keyof GraphStats,
    label: "Fraud Nodes",
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-950/40 border-red-900/50",
  },
  {
    key: "total_edges" as keyof GraphStats,
    label: "Transactions",
    icon: GitBranch,
    color: "text-cyan-400",
    bg: "bg-cyan-950/40 border-cyan-900/50",
  },
  {
    key: "rings" as keyof GraphStats,
    label: "Mule Rings",
    icon: Network,
    color: "text-purple-400",
    bg: "bg-purple-950/40 border-purple-900/50",
  },
];

export default function NetworkStats({ stats, loading }: NetworkStatsProps) {
  return (
    <div className="flex gap-3">
      {STAT_CARDS.map(({ key, label, icon: Icon, color, bg }) => (
        <div
          key={key}
          className={`flex-1 px-3 py-2.5 rounded-xl border ${bg} flex items-center gap-3`}
        >
          <Icon className={`w-5 h-5 ${color} shrink-0`} />
          <div>
            <div className={`text-lg font-bold font-mono ${color}`}>
              {loading ? (
                <span className="inline-block w-8 h-4 bg-gray-800 rounded animate-pulse" />
              ) : (
                stats?.[key] ?? 0
              )}
            </div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
