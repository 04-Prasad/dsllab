"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Search,
  ExternalLink,
  RefreshCw,
  AlertTriangle,
  Filter,
  ChevronDown,
} from "lucide-react";

const RISK_LEVELS = ["", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const LIMIT = 50;

  const loadAccounts = async (p = page) => {
    try {
      setLoading(true);
      const data = await api.getAccounts({
        search: search.trim() || undefined,
        risk_level: riskFilter || undefined,
        page: p,
        limit: LIMIT,
      });
      setAccounts(data);
    } catch (err) {
      console.error("Failed to load accounts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    loadAccounts(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [riskFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadAccounts(1);
  };

  const riskBadge = (level: string) => {
    if (level === "CRITICAL")
      return "bg-red-950 text-red-400 border border-red-800";
    if (level === "HIGH")
      return "bg-amber-950 text-amber-400 border border-amber-800";
    if (level === "MEDIUM")
      return "bg-yellow-950 text-yellow-400 border border-yellow-800";
    return "bg-emerald-950 text-emerald-400 border border-emerald-800";
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[rgba(186,215,247,0.12)]">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-eyebrow text-[#9da7ba] mb-1">
            <span>Entity Directory</span>
            <span>•</span>
            <span>Risk Scores</span>
          </div>
          <h1 className="text-3xl font-display font-medium text-skywash tracking-tight">
            Monitored Accounts
          </h1>
          <p className="text-sm text-[#9da7ba] mt-1">
            Search, filter, and investigate accounts by risk level and fused topology score.
          </p>
        </div>
        <button
          onClick={() => loadAccounts()}
          className="btn-pill-ghost flex items-center space-x-2 shrink-0 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#b6d9fc]" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <form
          onSubmit={handleSearchSubmit}
          className="relative flex-1 w-full flex items-center gap-2"
        >
          <Search className="w-4 h-4 text-[#9da7ba] absolute left-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Account ID (e.g. A102)…"
            className="w-full pl-9 pr-4 py-2 bg-[rgba(199,211,234,0.06)] border border-[rgba(186,215,247,0.12)] rounded-md text-xs text-white placeholder-[#9da7ba] focus:outline-none focus:border-[rgba(186,215,247,0.3)] transition-colors"
          />
          <button
            type="submit"
            className="btn-void-violet text-xs px-4 py-2"
          >
            Search
          </button>
        </form>

        <div className="flex items-center space-x-2 flex-wrap">
          <Filter className="w-4 h-4 text-[#9da7ba]" />
          {RISK_LEVELS.map((level) => (
            <button
              key={level || "ALL"}
              onClick={() => setRiskFilter(level)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                riskFilter === level
                  ? "bg-[#663af3] text-white border-[#663af3] shadow-[0_0_12px_rgba(102,58,243,0.4)]"
                  : "bg-[rgba(186,214,247,0.03)] text-[#c7d3ea] border-[rgba(186,215,247,0.12)] hover:bg-[rgba(186,214,247,0.08)]"
              }`}
            >
              {level || "ALL"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-[#9da7ba] font-mono text-sm animate-pulse">
            Loading Accounts…
          </div>
        ) : accounts.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
            <p className="text-sm font-semibold text-[#c7d3ea]">
              No accounts match the current filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[rgba(186,214,247,0.04)] text-[#9da7ba] border-b border-[rgba(186,215,247,0.12)]">
                <tr>
                  <th className="p-3.5 font-eyebrow text-[10px]">Account ID</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Type</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Status</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Risk Level</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">
                    <div className="flex items-center space-x-1">
                      <span>Risk Score</span>
                      <ChevronDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Created At</th>
                  <th className="p-3.5 font-eyebrow text-[10px] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(186,215,247,0.08)]">
                {accounts.map((acc: any) => (
                  <tr
                    key={acc.account_id}
                    className="hover:bg-[rgba(186,214,247,0.06)] transition-colors"
                  >
                    <td className="p-3.5 font-mono font-bold text-[#b6d9fc]">
                      {acc.account_id}
                    </td>
                    <td className="p-3.5 text-[#c7d3ea]">{acc.account_type}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                        {acc.status}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${riskBadge(
                          acc.current_risk_level
                        )}`}
                      >
                        {acc.current_risk_level}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-[rgba(186,214,247,0.12)] rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              acc.current_risk_level === "CRITICAL"
                                ? "bg-red-500"
                                : acc.current_risk_level === "HIGH"
                                ? "bg-amber-500"
                                : acc.current_risk_level === "MEDIUM"
                                ? "bg-yellow-500"
                                : "bg-emerald-500"
                            }`}
                            style={{
                              width: `${acc.current_risk_score}%`,
                            }}
                          />
                        </div>
                        <span className="font-mono font-bold text-white">
                          {Math.round(acc.current_risk_score)}
                        </span>
                      </div>
                    </td>
                    <td className="p-3.5 text-[#9da7ba] font-mono">
                      {acc.account_created_at?.slice(0, 10) ?? "N/A"}
                    </td>
                    <td className="p-3.5 text-right flex items-center justify-end gap-2">
                      <Link
                        href={`/graph?account_id=${acc.account_id}`}
                        className="btn-pill-ghost text-[11px] px-3 py-1"
                      >
                        Graph
                      </Link>
                      <Link
                        href={`/accounts/${acc.account_id}`}
                        className="btn-void-violet text-[11px] px-3 py-1 inline-flex items-center space-x-1"
                      >
                        <span>Investigate</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination row */}
      {!loading && accounts.length >= LIMIT && (
        <div className="flex justify-end gap-2 text-xs">
          <button
            onClick={() => { const p = Math.max(1, page - 1); setPage(p); loadAccounts(p); }}
            disabled={page === 1}
            className="btn-pill-ghost disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="px-3.5 py-1.5 bg-[rgba(186,214,247,0.06)] text-[#c7d3ea] rounded-full border border-[rgba(186,215,247,0.12)] font-mono">
            Page {page}
          </span>
          <button
            onClick={() => { const p = page + 1; setPage(p); loadAccounts(p); }}
            className="btn-pill-ghost"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
