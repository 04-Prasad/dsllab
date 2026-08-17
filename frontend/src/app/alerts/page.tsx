"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AlertTriangle, Filter, ExternalLink, RefreshCw } from "lucide-react";

const STATUSES = ["", "NEW", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await api.getAlerts({
        status: statusFilter || undefined,
        limit: 100,
      });
      setAlerts(data);
    } catch (err) {
      console.error("Failed to load alerts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const handleStatusUpdate = async (alertId: string, newStatus: string) => {
    setUpdatingId(alertId);
    try {
      await api.updateAlertStatus(alertId, newStatus);
      setAlerts((prev) =>
        prev.map((a) =>
          a.alert_id === alertId ? { ...a, status: newStatus } : a
        )
      );
    } catch (err) {
      console.error("Failed to update alert status", err);
    } finally {
      setUpdatingId(null);
    }
  };

  const severityBadge = (sev: string) =>
    sev === "CRITICAL"
      ? "bg-red-950 text-red-400 border border-red-800"
      : "bg-amber-950 text-amber-400 border border-amber-800";

  const statusBadge = (st: string) => {
    if (st === "NEW") return "bg-blue-950 text-blue-400 border border-blue-800";
    if (st === "UNDER_REVIEW") return "bg-amber-950 text-amber-400 border border-amber-800";
    if (st === "ESCALATED") return "bg-red-950 text-red-400 border border-red-800";
    if (st === "RESOLVED") return "bg-emerald-950 text-emerald-400 border border-emerald-800";
    if (st === "FALSE_POSITIVE") return "bg-gray-800 text-gray-400 border border-gray-700";
    return "bg-gray-800 text-gray-400";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Investigator Alert Queue
          </h1>
          <p className="text-sm text-gray-400">
            Triaged fraud alerts generated from EWS rules and GNN node
            classification.
          </p>
        </div>
        <button
          onClick={loadAlerts}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 font-medium flex items-center space-x-2 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Status Filter */}
      <div className="p-4 bg-[#111827] border border-gray-800 rounded-xl flex flex-wrap items-center gap-2">
        <Filter className="w-4 h-4 text-gray-400" />
        <span className="text-xs text-gray-400 font-medium mr-1">Status:</span>
        {STATUSES.map((st) => (
          <button
            key={st || "ALL"}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === st
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {st || "ALL"}
          </button>
        ))}
      </div>

      {/* Alert Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-400 font-mono text-sm animate-pulse">
            Loading Alert Queue…
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
            <p className="text-sm font-semibold text-gray-300">
              No alerts match status filter "{statusFilter || "ALL"}".
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/80 text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="p-3.5">Alert ID</th>
                  <th className="p-3.5">Account</th>
                  <th className="p-3.5">Severity</th>
                  <th className="p-3.5">Score</th>
                  <th className="p-3.5">Title</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Update Status</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {alerts.map((alt: any) => (
                  <tr
                    key={alt.alert_id}
                    className="hover:bg-gray-800/40 transition-colors"
                  >
                    <td className="p-3.5 font-mono font-bold text-indigo-300">
                      {alt.alert_id}
                    </td>
                    <td className="p-3.5 font-mono font-bold">
                      <Link
                        href={`/accounts/${alt.account_id}`}
                        className="text-indigo-400 hover:underline"
                      >
                        {alt.account_id}
                      </Link>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${severityBadge(
                          alt.severity
                        )}`}
                      >
                        {alt.severity}
                      </span>
                    </td>
                    <td className="p-3.5 font-mono font-bold text-white">
                      {Math.round(alt.risk_score)}
                    </td>
                    <td className="p-3.5 max-w-xs">
                      <div className="font-semibold text-gray-200">
                        {alt.title}
                      </div>
                      <div className="text-[11px] text-gray-400 line-clamp-1">
                        {alt.description}
                      </div>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${statusBadge(
                          alt.status
                        )}`}
                      >
                        {alt.status}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <select
                        value={alt.status}
                        disabled={updatingId === alt.alert_id}
                        onChange={(e) =>
                          handleStatusUpdate(alt.alert_id, e.target.value)
                        }
                        className="bg-gray-900 border border-gray-700 text-[11px] text-gray-300 rounded px-2 py-1 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                      >
                        {STATUSES.filter(Boolean).map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-3.5 text-right">
                      <Link
                        href={`/accounts/${alt.account_id}`}
                        className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium inline-flex items-center space-x-1 transition-colors"
                      >
                        <span>Inspect</span>
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
    </div>
  );
}
