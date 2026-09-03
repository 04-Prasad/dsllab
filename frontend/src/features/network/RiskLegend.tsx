"use client";

import React from "react";

const RISK_LEVELS = [
  { label: "LOW",      color: "bg-emerald-500" },
  { label: "MEDIUM",   color: "bg-yellow-500" },
  { label: "HIGH",     color: "bg-orange-500" },
  { label: "CRITICAL", color: "bg-red-500" },
];

const ROLES = [
  { symbol: "●", label: "HUB",          desc: "Major transaction centre",    color: "text-indigo-400" },
  { symbol: "◆", label: "BRIDGE",       desc: "Connects separate clusters",  color: "text-blue-400" },
  { symbol: "○", label: "MULE",         desc: "Fund forwarder",              color: "text-orange-400" },
  { symbol: "◉", label: "RING MEMBER",  desc: "Circular flow participant",   color: "text-purple-400" },
];

export default function RiskLegend() {
  return (
    <div className="flex items-start gap-6 px-4 py-3 bg-[#0d111e]/90 border border-gray-800/60 rounded-xl text-xs backdrop-blur-sm">
      {/* Risk Scale */}
      <div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Risk Scale</div>
        <div className="flex items-center gap-1.5">
          {RISK_LEVELS.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1">
              <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
              <span className="text-gray-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="w-px h-8 bg-gray-800 self-center" />

      {/* Node Roles */}
      <div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Node Roles</div>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {ROLES.map(({ symbol, label, desc, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className={`font-bold ${color}`}>{symbol}</span>
              <span className="text-gray-400">
                <span className="font-semibold text-gray-200">{label}</span> — {desc}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Particles note */}
      <div className="ml-auto self-center hidden xl:block">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Edges</div>
        <div className="text-gray-400">
          <span className="text-indigo-400">→</span> Particles = money direction
        </div>
      </div>
    </div>
  );
}
