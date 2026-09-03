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
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[rgba(186,215,247,0.12)]">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-eyebrow text-[#9da7ba] mb-1">
            <span>Triage Queue</span>
            <span>•</span>
            <span>Alert Operations</span>
          </div>
          <h1 className="text-3xl font-display font-medium text-skywash tracking-tight">
            Investigator Alert Queue
          </h1>
          <p className="text-sm text-[#9da7ba] mt-1">
            Triaged fraud alerts generated from EWS rules and GNN node classification.
          </p>
        </div>
        <button
          onClick={loadAlerts}
          className="btn-pill-ghost flex items-center space-x-2 shrink-0 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#b6d9fc]" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Status Filter */}
      <div className="glass-card p-4 flex flex-wrap items-center gap-2">
        <Filter className="w-4 h-4 text-[#9da7ba]" />
        <span className="text-xs font-eyebrow text-[#9da7ba] mr-1">Status:</span>
        {STATUSES.map((st) => (
          <button
            key={st || "ALL"}
            onClick={() => setStatusFilter(st)}
            className={`px-3.5 py-1 rounded-full text-xs font-semibold border transition-all ${
              statusFilter === st
                ? "bg-[#663af3] text-white border-[#663af3] shadow-[0_0_12px_rgba(102,58,243,0.4)]"
                : "bg-[rgba(186,214,247,0.03)] text-[#c7d3ea] border-[rgba(186,215,247,0.12)] hover:bg-[rgba(186,214,247,0.08)]"
            }`}
          >
            {st || "ALL"}
          </button>
        ))}
      </div>

      {/* Alert Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-[#9da7ba] font-mono text-sm animate-pulse">
            Loading Alert Queue…
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
            <p className="text-sm font-semibold text-[#c7d3ea]">
              No alerts match status filter "{statusFilter || "ALL"}".
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[rgba(186,214,247,0.04)] text-[#9da7ba] border-b border-[rgba(186,215,247,0.12)]">
                <tr>
                  <th className="p-3.5 font-eyebrow text-[10px]">Alert ID</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Account</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Severity</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Score</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Title</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Status</th>
                  <th className="p-3.5 font-eyebrow text-[10px]">Update Status</th>
                  <th className="p-3.5 font-eyebrow text-[10px] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(186,215,247,0.08)]">
                {alerts.map((alt: any) => (
                  <tr
                    key={alt.alert_id}
                    className="hover:bg-[rgba(186,214,247,0.06)] transition-colors"
                  >
                    <td className="p-3.5 font-mono font-bold text-[#b6d9fc]">
                      {alt.alert_id}
                    </td>
                    <td className="p-3.5 font-mono font-bold">
                      <Link
                        href={`/accounts/${alt.account_id}`}
                        className="text-[#663af3] hover:text-[#b6d9fc] hover:underline"
                      >
                        {alt.account_id}
                      </Link>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${severityBadge(
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
                      <div className="font-semibold text-[#d8ecf8]">
                        {alt.title}
                      </div>
                      <div className="text-[11px] text-[#9da7ba] line-clamp-1">
                        {alt.description}
                      </div>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${statusBadge(
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
                        className="bg-[rgba(199,211,234,0.06)] border border-[rgba(186,215,247,0.12)] text-[11px] text-[#c7d3ea] rounded-md px-2.5 py-1 focus:outline-none focus:border-[rgba(186,215,247,0.3)] disabled:opacity-50"
                      >
                        {STATUSES.filter(Boolean).map((s) => (
                          <option key={s} value={s} className="bg-[#05060f] text-white">
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-3.5 text-right">
                      <Link
                        href={`/accounts/${alt.account_id}`}
                        className="btn-void-violet text-[11px] px-3 py-1 inline-flex items-center space-x-1"
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
