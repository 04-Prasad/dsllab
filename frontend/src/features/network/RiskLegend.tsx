"use client";

import React from "react";

const RISK_LEVELS = [
  { label: "Low",      color: "bg-[#22c55e] shadow-[0_0_6px_rgba(34,197,94,0.4)]" },
  { label: "Medium",   color: "bg-[#facc15] shadow-[0_0_6px_rgba(250,204,21,0.4)]" },
  { label: "High",     color: "bg-[#f97316] shadow-[0_0_6px_rgba(249,115,22,0.4)]" },
  { label: "Critical", color: "bg-[#ef4444] shadow-[0_0_8px_rgba(239,68,68,0.6)]" },
  { label: "Ring",     color: "bg-[#a855f7] shadow-[0_0_6px_rgba(168,85,247,0.4)]" },
];

export default function RiskLegend() {
  return (
    <div className="flex items-center gap-5 px-4 py-2.5 bg-[#0f172a]/90 border border-[#1e293b] rounded-xl text-xs backdrop-blur-md shadow-lg">
      {/* Risk Scale */}
      <div>
        <div className="text-[10px] text-[#94a3b8] font-eyebrow mb-1">RISK LEVEL</div>
        <div className="flex items-center gap-2.5">
          {RISK_LEVELS.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
              <span className="text-[#f8fafc] text-[11px] font-medium">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-[#1e293b]" />

      {/* Transaction flow indicator */}
      <div>
        <div className="text-[10px] text-[#94a3b8] font-eyebrow mb-1">TRANSACTION FLOW</div>
        <div className="flex items-center gap-3 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-[#64748b]/50 rounded" />
            <span className="text-[#94a3b8]">Normal</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-orange-500 rounded" />
            <span className="text-orange-300 font-medium">Suspicious</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#38bdf8] font-bold">→</span>
            <span className="text-[#38bdf8] font-medium">Money Flow</span>
          </div>
        </div>
      </div>
    </div>
  );
}
