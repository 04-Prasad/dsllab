"use client";

import React, { useState } from "react";
import { Search, SlidersHorizontal, RefreshCw } from "lucide-react";
import type { NetworkFilters, GraphStats, QuickFilter } from "./types";

interface NetworkSidebarProps {
  stats: GraphStats | null;
  filters: NetworkFilters;
  quickFilter: QuickFilter;
  onFilterChange: (f: Partial<NetworkFilters>) => void;
  onQuickFilter: (qf: QuickFilter) => void;
  onResetFilters: () => void;
  onSearch: (accountId: string) => void;
  onReload: () => void;
  loading: boolean;
}

const QUICK_FILTERS: { key: QuickFilter; label: string; color: string }[] = [
  { key: "ALL",          label: "All Accounts", color: "bg-[#1e293b] text-[#f8fafc] border-[#334155]" },
  { key: "FRAUD_ONLY",   label: "Suspicious Only", color: "bg-red-950/70 text-red-300 border-red-800" },
  { key: "RING_MEMBERS", label: "Ring Members", color: "bg-purple-950/70 text-purple-300 border-purple-800" },
  { key: "HIGH_RISK",    label: "High Risk",    color: "bg-orange-950/70 text-orange-300 border-orange-800" },
];

export default function NetworkSidebar({
  stats,
  filters,
  quickFilter,
  onFilterChange,
  onQuickFilter,
  onResetFilters,
  onSearch,
  onReload,
  loading,
}: NetworkSidebarProps) {
  const [searchVal, setSearchVal] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) onSearch(searchVal.trim().toUpperCase());
  };

  return (
    <aside className="w-64 min-w-[16rem] bg-[#020617]/95 border-r border-[#1e293b] backdrop-blur-xl flex flex-col p-4 gap-5 overflow-y-auto z-10 text-[#f8fafc]">

      {/* Search */}
      <section>
        <label className="text-[10px] font-eyebrow text-[#94a3b8] mb-2 block">
          SEARCH ACCOUNT ID
        </label>
        <form onSubmit={handleSearch} className="flex gap-1.5">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#94a3b8]" />
            <input
              type="text"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              placeholder="Search Account ID..."
              className="w-full pl-8 pr-2 py-1.5 bg-[#0f172a] border border-[#1e293b] rounded-lg text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#38bdf8] transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !searchVal.trim()}
            className="px-3 py-1.5 bg-[#38bdf8] hover:bg-[#0284c7] text-[#020617] rounded-lg text-xs font-bold transition-colors disabled:opacity-40 shadow-[0_0_12px_rgba(56,189,248,0.3)] cursor-pointer"
          >
            →
          </button>
        </form>

        {/* Quick account presets */}
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {["A102", "A450", "A601"].map((id) => (
            <button
              key={id}
              onClick={() => { setSearchVal(id); onSearch(id); }}
              className="px-2.5 py-0.5 rounded-md bg-[#0f172a] hover:bg-[#1e293b] border border-[#1e293b] text-[#38bdf8] text-[10px] font-mono font-semibold transition-colors cursor-pointer"
            >
              {id}
            </button>
          ))}
        </div>
      </section>

      {/* Quick Filters */}
      <section>
        <label className="text-[10px] font-eyebrow text-[#94a3b8] mb-2 block">
          INVESTIGATION PRESETS
        </label>
        <div className="space-y-1.5">
          {QUICK_FILTERS.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => onQuickFilter(key)}
              className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                quickFilter === key
                  ? `${color} border-current ring-1 ring-current/40 shadow-sm`
                  : "bg-[#0f172a]/60 border-[#1e293b] text-[#94a3b8] hover:text-white hover:bg-[#1e293b]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Risk Threshold Slider */}
      <section className="p-3 bg-[#0f172a]/60 border border-[#1e293b] rounded-xl space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-[10px] font-eyebrow text-[#94a3b8]">
            RISK THRESHOLD
          </label>
          <span className="font-mono text-xs text-[#38bdf8] font-bold">
            {filters.riskThreshold}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={filters.riskThreshold}
          onChange={(e) => onFilterChange({ riskThreshold: Number(e.target.value) })}
          className="w-full accent-[#38bdf8] cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-[#64748b] font-mono">
          <span>0%</span>
          <span>100%</span>
        </div>
      </section>

      {/* Advanced Filters */}
      <section>
        <div className="flex items-center gap-1.5 mb-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#38bdf8]" />
          <label className="text-[10px] font-eyebrow text-[#94a3b8]">
            NETWORK FILTERS
          </label>
        </div>
        <div className="space-y-2">
          {[
            { key: "fraudOnly" as keyof NetworkFilters, label: "Suspicious Accounts Only" },
            { key: "ringMembersOnly" as keyof NetworkFilters, label: "Fraud Ring Members" },
            { key: "hasEws" as keyof NetworkFilters, label: "Has EWS Rule Signal" },
            { key: "hubsOnly" as keyof NetworkFilters, label: "High-Degree Hubs" },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={!!filters[key]}
                  onChange={(e) => onFilterChange({ [key]: e.target.checked })}
                  className="sr-only"
                />
                <div
                  className={`w-4 h-4 rounded border transition-colors ${
                    filters[key]
                      ? "bg-[#38bdf8] border-[#38bdf8]"
                      : "bg-[#0f172a] border-[#1e293b] group-hover:border-[#38bdf8]/50"
                  }`}
                >
                  {filters[key] && (
                    <svg className="w-3 h-3 text-[#020617] m-auto font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.5} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </div>
              <span className="text-xs text-[#94a3b8] group-hover:text-white transition-colors">{label}</span>
            </label>
          ))}
        </div>
      </section>

      {/* Stats mini summary */}
      {stats && (
        <section className="mt-auto pt-3 border-t border-[#1e293b]">
          <div className="text-[10px] font-eyebrow text-[#94a3b8] mb-2">
            EXPLORED SUBSET
          </div>
          <div className="space-y-1 text-xs">
            {[
              { label: "Accounts", value: stats.total_nodes },
              { label: "Suspicious", value: stats.fraud_nodes, color: "text-red-400" },
              { label: "Transactions", value: stats.total_edges },
              { label: "Rings", value: stats.rings, color: "text-purple-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between text-[#94a3b8]">
                <span>{label}</span>
                <span className={`font-mono font-bold ${color ?? "text-white"}`}>{value}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Reload */}
      <button
        onClick={() => { onResetFilters(); onReload(); }}
        disabled={loading}
        className="w-full flex items-center justify-center gap-1.5 py-2 bg-[#0f172a] hover:bg-[#1e293b] text-[#f8fafc] rounded-lg border border-[#1e293b] text-xs font-medium transition-colors cursor-pointer disabled:opacity-40"
      >
        <RefreshCw className={`w-3.5 h-3.5 text-[#38bdf8] ${loading ? "animate-spin" : ""}`} />
        Reset & Reload View
      </button>
    </aside>
  );
}
