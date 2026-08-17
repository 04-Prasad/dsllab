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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Monitored Accounts
          </h1>
          <p className="text-sm text-gray-400">
            Search, filter, and investigate accounts by risk level and graph
            behaviour score.
          </p>
        </div>
        <button
          onClick={() => loadAccounts()}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 font-medium flex items-center space-x-2 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-4 bg-[#111827] border border-gray-800 rounded-xl flex flex-col md:flex-row items-center justify-between gap-4">
        <form
          onSubmit={handleSearchSubmit}
          className="relative flex-1 w-full flex items-center gap-2"
        >
          <Search className="w-4 h-4 text-gray-500 absolute left-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Account ID (e.g. A102)…"
            className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex items-center space-x-2 flex-wrap">
          <Filter className="w-4 h-4 text-gray-400" />
          {RISK_LEVELS.map((level) => (
            <button
              key={level || "ALL"}
              onClick={() => setRiskFilter(level)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                riskFilter === level
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {level || "ALL"}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-400 font-mono text-sm animate-pulse">
            Loading Accounts…
          </div>
        ) : accounts.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
            <p className="text-sm font-semibold text-gray-300">
              No accounts match the current filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/80 text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="p-3.5">Account ID</th>
                  <th className="p-3.5">Type</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Risk Level</th>
                  <th className="p-3.5">
                    <div className="flex items-center space-x-1">
                      <span>Risk Score</span>
                      <ChevronDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3.5">Created At</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {accounts.map((acc: any) => (
                  <tr
                    key={acc.account_id}
                    className="hover:bg-gray-800/40 transition-colors"
                  >
                    <td className="p-3.5 font-mono font-bold text-indigo-300">
                      {acc.account_id}
                    </td>
                    <td className="p-3.5 text-gray-300">{acc.account_type}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {acc.status}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${riskBadge(
                          acc.current_risk_level
                        )}`}
                      >
                        {acc.current_risk_level}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
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
                    <td className="p-3.5 text-gray-500 font-mono">
                      {acc.account_created_at?.slice(0, 10) ?? "N/A"}
                    </td>
                    <td className="p-3.5 text-right flex items-center justify-end gap-2">
                      <Link
                        href={`/graph?account_id=${acc.account_id}`}
                        className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded text-[11px] font-medium border border-gray-700 transition-colors"
                      >
                        Graph
                      </Link>
                      <Link
                        href={`/accounts/${acc.account_id}`}
                        className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium transition-colors inline-flex items-center space-x-1"
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
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="px-3 py-1.5 bg-gray-900 text-gray-400 rounded">
            Page {page}
          </span>
          <button
            onClick={() => { const p = page + 1; setPage(p); loadAccounts(p); }}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
