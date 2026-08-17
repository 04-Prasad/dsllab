"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  ShieldAlert,
  AlertTriangle,
  Zap,
  Network,
  ArrowLeft,
  Calendar,
  Building,
  Activity,
  ExternalLink
} from "lucide-react";

export default function AccountDetailPage() {
  const params = useParams();
  const accountId = params.id as string;

  const [detail, setDetail] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [accDetail, graph, txs] = await Promise.all([
        api.getAccountDetail(accountId),
        api.getAccountGraph(accountId, 1, 40),
        api.getAccountTransactions(accountId, 50),
      ]);
      setDetail(accDetail);
      setGraphData(graph);
      setTransactions(txs);
    } catch (err: any) {
      setError(err.message || `Failed to load details for account ${accountId}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (accountId) loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 font-mono text-sm animate-pulse">
          Loading Account {accountId} Graph Investigation…
        </p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl space-y-4">
        <div className="flex items-center space-x-3 text-red-400 font-bold">
          <AlertTriangle className="w-6 h-6" />
          <span>Account Not Found</span>
        </div>
        <p className="text-gray-300 text-sm">{error}</p>
        <Link
          href="/accounts"
          className="px-4 py-2 bg-gray-800 text-white rounded-lg text-xs font-semibold inline-block"
        >
          ← Back to Accounts
        </Link>
      </div>
    );
  }

  const { account, features, risk_summary, ews_signals } = detail;
  const riskLevel: string = account.current_risk_level ?? "LOW";
  const riskScore: number = account.current_risk_score ?? 0;

  const riskBorderColor =
    riskLevel === "CRITICAL"
      ? "border-red-500"
      : riskLevel === "HIGH"
      ? "border-amber-500"
      : riskLevel === "MEDIUM"
      ? "border-yellow-500"
      : "border-emerald-500";

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-3">
        <Link
          href="/accounts"
          className="text-xs text-gray-400 hover:text-white flex items-center space-x-1 font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Accounts</span>
        </Link>
        <span className="text-xs text-indigo-400 font-mono">
          INVESTIGATION FILE #{account.account_id}
        </span>
      </div>

      {/* Account Hero Card */}
      <div className="p-6 bg-[#111827] border border-gray-800 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <h1 className="text-3xl font-bold text-white font-mono">
              {account.account_id}
            </h1>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold font-mono tracking-wider ${
                riskLevel === "CRITICAL"
                  ? "bg-red-950 text-red-400 border border-red-800"
                  : riskLevel === "HIGH"
                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                  : riskLevel === "MEDIUM"
                  ? "bg-yellow-950 text-yellow-400 border border-yellow-800"
                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
              }`}
            >
              {riskLevel} RISK
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400">
            <span className="flex items-center space-x-1.5">
              <Building className="w-4 h-4 text-gray-500" />
              <span>
                Type:{" "}
                <strong className="text-gray-200">{account.account_type}</strong>
              </span>
            </span>
            <span className="flex items-center space-x-1.5">
              <Calendar className="w-4 h-4 text-gray-500" />
              <span>
                Created:{" "}
                <strong className="text-gray-200">
                  {account.account_created_at?.slice(0, 10) ?? "N/A"}
                </strong>
              </span>
            </span>
            <span className="flex items-center space-x-1.5">
              <Activity className="w-4 h-4 text-gray-500" />
              <span>
                Status:{" "}
                <strong className="text-emerald-400">{account.status}</strong>
              </span>
            </span>
          </div>
        </div>

        {/* Risk Score Gauge */}
        <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl flex items-center space-x-4 min-w-[220px]">
          <div
            className={`w-16 h-16 rounded-full border-4 ${riskBorderColor} flex items-center justify-center font-mono font-bold text-xl text-white bg-gray-950/40`}
          >
            {Math.round(riskScore)}
          </div>
          <div>
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider">
              Risk Score
            </div>
            <div className="text-sm font-bold text-white">
              {Math.round(riskScore)} / 100
            </div>
            <div className="text-[11px] text-gray-500">Combined Fusion</div>
          </div>
        </div>
      </div>

      {/* Main 3-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Why Flagged + EWS + Transactions */}
        <div className="space-y-6 lg:col-span-2">
          {/* Why Flagged */}
          <div className="p-5 bg-[#111827] border border-gray-800 rounded-xl space-y-4">
            <div className="flex items-center space-x-2 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="text-base font-bold text-white">
                Why Flagged — Explainable Risk Reasons
              </h3>
            </div>
            <ul className="space-y-2.5">
              {risk_summary?.reasons?.length > 0 ? (
                risk_summary.reasons.map((reason: string, idx: number) => (
                  <li
                    key={idx}
                    className="p-3 bg-[#0F1423] border border-gray-800 rounded-lg text-xs text-gray-200 flex items-start space-x-2"
                  >
                    <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                    <span className="leading-relaxed">{reason}</span>
                  </li>
                ))
              ) : (
                <li className="text-xs text-gray-400">
                  No specific risk triggers recorded. Account behaviour appears
                  normal.
                </li>
              )}
            </ul>
          </div>

          {/* Triggered EWS Signals */}
          <div className="p-5 bg-[#111827] border border-gray-800 rounded-xl space-y-4">
            <div className="flex items-center space-x-2 text-amber-400">
              <Zap className="w-5 h-5" />
              <h3 className="text-base font-bold text-white">
                Triggered Early Warning Signals ({ews_signals?.length ?? 0})
              </h3>
            </div>

            {ews_signals?.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {ews_signals.map((sig: any) => (
                  <div
                    key={sig.id}
                    className="p-3.5 bg-[#0F1423] border border-gray-800 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-amber-400">
                        {sig.signal_code}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                          sig.severity === "CRITICAL"
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : "bg-amber-950 text-amber-400 border border-amber-800"
                        }`}
                      >
                        {sig.severity}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-white">
                      {sig.signal_type}
                    </div>
                    <p className="text-[11px] text-gray-400 leading-snug">
                      {sig.description}
                    </p>
                    <div className="pt-2 border-t border-gray-800/80 flex items-center justify-between text-[11px] font-mono">
                      <span className="text-gray-500">
                        Observed:{" "}
                        <strong className="text-white">{sig.observed_value}</strong>
                      </span>
                      <span className="text-gray-500">
                        Threshold:{" "}
                        <strong className="text-gray-400">
                          {sig.threshold_value}
                        </strong>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500">No EWS signals triggered.</p>
            )}
          </div>

          {/* Transaction History */}
          <div className="p-5 bg-[#111827] border border-gray-800 rounded-xl space-y-4">
            <h3 className="text-base font-bold text-white">
              Transaction History ({transactions.length})
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-900/80 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="p-3">TX ID</th>
                    <th className="p-3">Sender</th>
                    <th className="p-3">Receiver</th>
                    <th className="p-3">Amount</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-mono">
                  {transactions.slice(0, 25).map((tx: any) => (
                    <tr
                      key={tx.transaction_id}
                      className="hover:bg-gray-800/40"
                    >
                      <td className="p-3 text-gray-500">{tx.transaction_id}</td>
                      <td
                        className={`p-3 font-bold ${
                          tx.sender_account_id === accountId
                            ? "text-amber-400"
                            : "text-gray-300"
                        }`}
                      >
                        {tx.sender_account_id}
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          tx.receiver_account_id === accountId
                            ? "text-indigo-400"
                            : "text-gray-300"
                        }`}
                      >
                        {tx.receiver_account_id}
                      </td>
                      <td className="p-3 font-bold text-white">
                        ₹{Number(tx.amount).toLocaleString("en-IN")}
                      </td>
                      <td className="p-3 text-gray-400">{tx.transaction_type}</td>
                      <td className="p-3 text-gray-500">
                        {String(tx.timestamp).replace("T", " ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Signal Breakdown + Graph Summary */}
        <div className="space-y-6">
          {/* Multi-Signal Breakdown */}
          <div className="p-5 bg-[#111827] border border-gray-800 rounded-xl space-y-4">
            <h3 className="text-base font-bold text-white">
              Multi-Signal Score Breakdown
            </h3>
            <div className="space-y-4 text-xs">
              {[
                {
                  label: "GNN Model Score (50%)",
                  value: risk_summary?.ml_score ?? 0,
                  color: "bg-indigo-500",
                  textColor: "text-indigo-400",
                },
                {
                  label: "EWS Rule Score (35%)",
                  value: risk_summary?.ews_score ?? 0,
                  color: "bg-amber-500",
                  textColor: "text-amber-400",
                },
                {
                  label: "Graph Context Score (15%)",
                  value: risk_summary?.graph_score ?? 0,
                  color: "bg-cyan-500",
                  textColor: "text-cyan-400",
                },
              ].map(({ label, value, color, textColor }) => (
                <div key={label}>
                  <div className="flex justify-between font-medium text-gray-300 mb-1">
                    <span>{label}</span>
                    <span className={`font-mono font-bold ${textColor}`}>
                      {Math.round(Number(value))}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-900 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${color} transition-all`}
                      style={{ width: `${Math.min(100, Number(value))}%` }}
                    />
                  </div>
                </div>
              ))}

              <div className="mt-3 pt-3 border-t border-gray-800 flex justify-between items-center">
                <span className="font-semibold text-gray-300">Final Score</span>
                <span
                  className={`font-mono font-bold text-lg ${
                    riskLevel === "CRITICAL"
                      ? "text-red-400"
                      : riskLevel === "HIGH"
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {Math.round(riskScore)} / 100
                </span>
              </div>
            </div>
          </div>

          {/* Graph Neighbourhood Summary */}
          <div className="p-5 bg-[#111827] border border-gray-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-cyan-400">
                <Network className="w-5 h-5" />
                <h3 className="text-base font-bold text-white">
                  Graph Neighbourhood
                </h3>
              </div>
              <Link
                href={`/graph?account_id=${accountId}`}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
              >
                <span>Full Explorer</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>

            <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl space-y-3 text-xs">
              {[
                {
                  label: "Unique Senders (In-Degree)",
                  val: features?.unique_senders ?? 0,
                  cls: "text-white",
                },
                {
                  label: "Unique Receivers (Out-Degree)",
                  val: features?.unique_receivers ?? 0,
                  cls: "text-white",
                },
                {
                  label: "Velocity (1h peak)",
                  val: `${features?.velocity_1h ?? 0} txns/hr`,
                  cls: "text-white",
                },
                {
                  label: "Risky Counterparty Ratio",
                  val: `${Math.round((features?.risky_neighbor_ratio ?? 0) * 100)}%`,
                  cls: "text-rose-400",
                },
                {
                  label: "Dormancy Gap (days)",
                  val: `${features?.dormancy_days?.toFixed(1) ?? 0}`,
                  cls: "text-white",
                },
              ].map(({ label, val, cls }) => (
                <div key={label} className="flex justify-between text-gray-400">
                  <span>{label}:</span>
                  <span className={`font-mono font-bold ${cls}`}>{val}</span>
                </div>
              ))}
            </div>

            {/* Graph node mini-preview */}
            {graphData?.nodes?.length > 0 && (
              <div className="pt-2 border-t border-gray-800 space-y-2">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Connected Nodes ({graphData.nodes.length})
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {graphData.nodes.slice(0, 12).map((n: any) => (
                    <Link
                      key={n.id}
                      href={`/accounts/${n.id}`}
                      className={`px-2 py-1 rounded text-[10px] font-mono font-bold transition-colors ${
                        n.risk_level === "CRITICAL"
                          ? "bg-red-950 text-red-400 border border-red-800 hover:bg-red-900"
                          : n.risk_level === "HIGH"
                          ? "bg-amber-950 text-amber-400 border border-amber-800 hover:bg-amber-900"
                          : "bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700"
                      }`}
                    >
                      {n.id}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
