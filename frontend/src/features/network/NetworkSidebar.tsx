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
  { key: "ALL",          label: "All",          color: "bg-gray-700 text-gray-200" },
  { key: "FRAUD_ONLY",   label: "Fraud Only",   color: "bg-red-900/60 text-red-300 border-red-800" },
  { key: "RING_MEMBERS", label: "Ring Members", color: "bg-purple-900/60 text-purple-300 border-purple-800" },
  { key: "HIGH_RISK",    label: "High Risk",    color: "bg-orange-900/60 text-orange-300 border-orange-800" },
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
    <aside className="w-60 min-w-[15rem] bg-[#05060f]/90 border-r border-[rgba(186,215,247,0.12)] backdrop-blur-xl flex flex-col p-4 gap-5 overflow-y-auto z-10">

      {/* Search */}
      <section>
        <label className="text-[11px] font-eyebrow text-[#9da7ba] mb-2 block">
          Search Account
        </label>
        <form onSubmit={handleSearch} className="flex gap-1.5">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#9da7ba]" />
            <input
              type="text"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              placeholder="e.g. A102"
              className="w-full pl-8 pr-2 py-1.5 bg-[rgba(199,211,234,0.06)] border border-[rgba(186,215,247,0.12)] rounded-md text-xs text-white placeholder-[#9da7ba] focus:outline-none focus:border-[rgba(186,215,247,0.3)] transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !searchVal.trim()}
            className="px-3 py-1.5 bg-[#663af3] hover:bg-[#7549f5] text-white rounded-md text-xs font-semibold transition-colors disabled:opacity-40 shadow-[0_0_12px_rgba(102,58,243,0.4)]"
          >
            →
          </button>
        </form>

        {/* Quick account presets */}
        <div className="flex flex-wrap gap-1 mt-2">
          {["A102", "A450", "A601"].map((id) => (
            <button
              key={id}
              onClick={() => { setSearchVal(id); onSearch(id); }}
              className="px-2 py-0.5 rounded-md bg-[rgba(186,214,247,0.06)] hover:bg-[rgba(186,214,247,0.14)] border border-[rgba(186,215,247,0.12)] text-[#c7d3ea] text-[10px] font-mono font-semibold transition-colors"
            >
              {id}
            </button>
          ))}
        </div>
      </section>

      {/* Quick Filters */}
      <section>
        <label className="text-[11px] font-eyebrow text-[#9da7ba] mb-2 block">
          Quick View
        </label>
        <div className="space-y-1">
          {QUICK_FILTERS.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => onQuickFilter(key)}
              className={`w-full text-left px-3 py-2 rounded-full text-xs font-semibold border transition-all ${
                quickFilter === key
                  ? `${color} border-current ring-1 ring-current/30`
                  : "bg-[rgba(186,214,247,0.03)] border-[rgba(186,215,247,0.12)] text-[#c7d3ea] hover:bg-[rgba(186,214,247,0.08)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Risk Threshold Slider */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <label className="text-[11px] font-eyebrow text-[#9da7ba]">
            Risk Threshold
          </label>
          <span className="font-mono text-xs text-[#b6d9fc] font-bold">
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
          className="w-full accent-[#663af3] cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-[#9da7ba] mt-0.5">
          <span>0%</span>
          <span>100%</span>
        </div>
      </section>

      {/* Advanced Filters */}
      <section>
        <div className="flex items-center gap-1.5 mb-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#9da7ba]" />
          <label className="text-[11px] font-eyebrow text-[#9da7ba]">
            Filters
          </label>
        </div>
        <div className="space-y-2">
          {[
            { key: "fraudOnly" as keyof NetworkFilters, label: "Fraud Nodes Only" },
            { key: "ringMembersOnly" as keyof NetworkFilters, label: "Ring Members Only" },
            { key: "hasEws" as keyof NetworkFilters, label: "Has EWS Signal" },
            { key: "hubsOnly" as keyof NetworkFilters, label: "Hubs Only" },
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
                      ? "bg-[#663af3] border-[#663af3]"
                      : "bg-[rgba(199,211,234,0.06)] border-[rgba(186,215,247,0.2)] group-hover:border-[rgba(186,215,247,0.4)]"
                  }`}
                >
                  {filters[key] && (
                    <svg className="w-3 h-3 text-white m-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </div>
              <span className="text-xs text-[#c7d3ea] group-hover:text-white transition-colors">{label}</span>
            </label>
          ))}
        </div>
      </section>

      {/* Stats mini summary */}
      {stats && (
        <section className="mt-auto pt-3 border-t border-[rgba(186,215,247,0.12)]">
          <div className="text-[11px] font-eyebrow text-[#9da7ba] mb-2">
            Network
          </div>
          <div className="space-y-1 text-xs">
            {[
              { label: "Nodes", value: stats.total_nodes },
              { label: "Fraud / High-Risk", value: stats.fraud_nodes, color: "text-red-400" },
              { label: "Edges", value: stats.total_edges },
              { label: "Rings Detected", value: stats.rings, color: "text-purple-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between text-[#9da7ba]">
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
        className="btn-pill-ghost w-full flex items-center justify-center gap-1.5 py-2 text-xs font-medium cursor-pointer disabled:opacity-40"
      >
        <RefreshCw className={`w-3.5 h-3.5 text-[#b6d9fc] ${loading ? "animate-spin" : ""}`} />
        Reset & Reload
      </button>
    </aside>
  );
}
