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
    <aside className="w-60 min-w-[15rem] bg-[#0d111e] border-r border-gray-800 flex flex-col p-4 gap-5 overflow-y-auto">

      {/* Search */}
      <section>
        <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2 block">
          Search Account
        </label>
        <form onSubmit={handleSearch} className="flex gap-1.5">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              placeholder="e.g. A102"
              className="w-full pl-8 pr-2 py-1.5 bg-gray-900 border border-gray-800 rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !searchVal.trim()}
            className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-40"
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
              className="px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 text-[10px] font-mono font-semibold transition-colors"
            >
              {id}
            </button>
          ))}
        </div>
      </section>

      {/* Quick Filters */}
      <section>
        <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2 block">
          Quick View
        </label>
        <div className="space-y-1">
          {QUICK_FILTERS.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => onQuickFilter(key)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold border transition-colors ${
                quickFilter === key
                  ? `${color} border-current ring-1 ring-current/30`
                  : "bg-gray-900 border-gray-800 text-gray-400 hover:bg-gray-800"
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
          <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
            Risk Threshold
          </label>
          <span className="font-mono text-xs text-indigo-400 font-bold">
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
          className="w-full accent-indigo-500 cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-gray-600 mt-0.5">
          <span>0%</span>
          <span>100%</span>
        </div>
      </section>

      {/* Advanced Filters */}
      <section>
        <div className="flex items-center gap-1.5 mb-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-gray-400" />
          <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
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
                      ? "bg-indigo-600 border-indigo-500"
                      : "bg-gray-800 border-gray-600 group-hover:border-gray-500"
                  }`}
                >
                  {filters[key] && (
                    <svg className="w-3 h-3 text-white m-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </div>
              <span className="text-xs text-gray-300 group-hover:text-white transition-colors">{label}</span>
            </label>
          ))}
        </div>
      </section>

      {/* Stats mini summary */}
      {stats && (
        <section className="mt-auto">
          <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Network
          </div>
          <div className="space-y-1 text-xs">
            {[
              { label: "Nodes", value: stats.total_nodes },
              { label: "Fraud / High-Risk", value: stats.fraud_nodes, color: "text-red-400" },
              { label: "Edges", value: stats.total_edges },
              { label: "Rings Detected", value: stats.rings, color: "text-purple-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between text-gray-400">
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
        className="w-full flex items-center justify-center gap-1.5 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        Reset & Reload
      </button>
    </aside>
  );
}
