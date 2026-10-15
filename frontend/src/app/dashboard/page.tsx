"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  LayoutDashboard,
  Users,
  ArrowLeftRight,
  AlertTriangle,
  ShieldAlert,
  Zap,
  TrendingUp,
  ArrowUpRight,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

const RISK_COLORS: Record<string, string> = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  CRITICAL: "#DC2626",
};

const KPI_CONFIGS = [
  {
    key: "total_accounts",
    label: "Monitored Accounts",
    sub: "Active graph nodes",
    icon: Users,
    iconColor: "text-blue-400",
    valueColor: "text-white",
  },
  {
    key: "total_transactions",
    label: "Transactions",
    sub: "Graph transfer edges",
    icon: ArrowLeftRight,
    iconColor: "text-indigo-400",
    valueColor: "text-white",
  },
  {
    key: "active_alerts",
    label: "Active Alerts",
    sub: "Investigator queue",
    icon: AlertTriangle,
    iconColor: "text-rose-400",
    valueColor: "text-rose-400",
  },
  {
    key: "critical_accounts",
    label: "Critical Risk",
    sub: "Score >= 80 / 100",
    icon: ShieldAlert,
    iconColor: "text-red-500",
    valueColor: "text-red-400",
  },
  {
    key: "high_risk_accounts",
    label: "High Risk",
    sub: "Score 60 - 79",
    icon: TrendingUp,
    iconColor: "text-amber-500",
    valueColor: "text-amber-400",
  },
  {
    key: "ews_count",
    label: "EWS Signals",
    sub: "Rule triggers total",
    icon: Zap,
    iconColor: "text-amber-400",
    valueColor: "text-white",
  },
];

export default function DashboardPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDashboardSummary();
      setSummary(data);
    } catch (err: any) {
      setError(err.message ?? "Failed to load dashboard summary");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 font-mono text-sm animate-pulse">
          Loading GraphGuard Dashboard…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl space-y-4">
        <div className="flex items-center space-x-3 text-red-400 font-bold">
          <AlertTriangle className="w-6 h-6" />
          <span>Dashboard Load Error</span>
        </div>
        <p className="text-gray-300 text-sm">{error}</p>
        <p className="text-gray-500 text-xs">
          Make sure the FastAPI backend is running on{" "}
          <code className="font-mono">localhost:8000</code> and the database has
          been seeded with{" "}
          <code className="font-mono">python scripts/setup_ibm.py</code>.
        </p>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center space-x-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  if (!summary) return null;

  const riskPieData = [
    { name: "Low Risk", value: summary.risk_distribution?.LOW ?? 0, color: RISK_COLORS.LOW },
    { name: "Medium", value: summary.risk_distribution?.MEDIUM ?? 0, color: RISK_COLORS.MEDIUM },
    { name: "High", value: summary.risk_distribution?.HIGH ?? 0, color: RISK_COLORS.HIGH },
    { name: "Critical", value: summary.risk_distribution?.CRITICAL ?? 0, color: RISK_COLORS.CRITICAL },
  ].filter((d) => d.value > 0);

  const riskBarData = [
    { level: "LOW", count: summary.risk_distribution?.LOW ?? 0, fill: RISK_COLORS.LOW },
    { level: "MEDIUM", count: summary.risk_distribution?.MEDIUM ?? 0, fill: RISK_COLORS.MEDIUM },
    { level: "HIGH", count: summary.risk_distribution?.HIGH ?? 0, fill: RISK_COLORS.HIGH },
    { level: "CRITICAL", count: summary.risk_distribution?.CRITICAL ?? 0, fill: RISK_COLORS.CRITICAL },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[rgba(186,215,247,0.12)]">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-eyebrow text-[#9da7ba] mb-1">
            <span>Graph Intelligence</span>
            <span>•</span>
            <span>Realtime Fraud Analytics</span>
          </div>
          <h1 className="text-3xl font-display font-medium text-skywash tracking-tight">
            Fraud Monitoring Overview
          </h1>
          <p className="text-sm text-[#9da7ba] mt-1">
            Deterministic EWS rule signals, PyG GraphSAGE classification, and fused risk scores.
          </p>
        </div>
        <button
          onClick={loadData}
          className="btn-pill-ghost flex items-center space-x-2 shrink-0 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#b6d9fc]" />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {KPI_CONFIGS.map(({ key, label, sub, icon: Icon, iconColor, valueColor }) => (
          <div
            key={key}
            className="glass-card p-4 space-y-2 relative overflow-hidden group"
          >
            <div className="flex items-center justify-between text-[#9da7ba]">
              <span className="text-xs font-medium">{label}</span>
              <div className="w-7 h-7 rounded-full bg-[rgba(186,214,247,0.06)] border border-[rgba(186,215,247,0.12)] flex items-center justify-center">
                <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
              </div>
            </div>
            <div className={`text-2xl font-bold font-mono ${valueColor}`}>
              {(summary[key] ?? 0).toLocaleString()}
            </div>
            <div className="text-[11px] text-[#9da7ba] truncate">{sub}</div>
          </div>
        ))}
      </div>

      {/* Main 2-section grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2/3: Tables */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top Risk Accounts Table */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-display font-medium text-[#d8ecf8]">
                  Top High-Risk Accounts
                </h3>
                <p className="text-xs text-[#9da7ba]">
                  Accounts requiring immediate investigator triage and deep-dive graph audit.
                </p>
              </div>
              <Link
                href="/accounts?risk_level=CRITICAL"
                className="text-xs text-[#663af3] hover:text-[#b6d9fc] font-medium flex items-center space-x-1 transition-colors"
              >
                <span>View All Accounts</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[rgba(186,214,247,0.04)] text-[#9da7ba] border-b border-[rgba(186,215,247,0.12)]">
                  <tr>
                    <th className="p-3.5 font-eyebrow text-[10px]">Account ID</th>
                    <th className="p-3.5 font-eyebrow text-[10px]">Type</th>
                    <th className="p-3.5 font-eyebrow text-[10px]">Risk Level</th>
                    <th className="p-3.5 font-eyebrow text-[10px]">Fused Score</th>
                    <th className="p-3.5 font-eyebrow text-[10px] text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(186,215,247,0.08)]">
                  {summary.top_risk_accounts?.map((acc: any) => (
                    <tr
                      key={acc.account_id}
                      className="hover:bg-[rgba(186,214,247,0.06)] transition-colors"
                    >
                      <td className="p-3.5 font-mono font-bold text-[#b6d9fc]">
                        {acc.account_id}
                      </td>
                      <td className="p-3.5 text-[#c7d3ea]">{acc.account_type}</td>
                      <td className="p-3.5">
                        <span
                          className={`px-2.5 py-1 rounded-md text-[10px] font-bold border ${
                            acc.risk_level === "CRITICAL"
                              ? "bg-red-950/60 text-red-400 border-red-800/80"
                              : acc.risk_level === "HIGH"
                              ? "bg-amber-950/60 text-amber-400 border-amber-800/80"
                              : "bg-emerald-950/60 text-emerald-400 border-emerald-800/80"
                          }`}
                        >
                          {acc.risk_level}
                        </span>
                      </td>
                      <td className="p-3.5 font-mono font-bold text-[#ffffff]">
                        {Math.round(acc.risk_score)} / 100
                      </td>
                      <td className="p-3.5 text-right">
                        <Link
                          href={`/accounts/${acc.account_id}`}
                          className="btn-void-violet text-[11px] px-3 py-1.5 inline-flex items-center space-x-1"
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
          </div>

          {/* Recent Alerts */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-display font-medium text-[#d8ecf8]">
                  Recent Investigator Alerts
                </h3>
                <p className="text-xs text-[#9da7ba]">
                  Realtime triggered EWS & GNN alerts queued for investigator workflow.
                </p>
              </div>
              <Link
                href="/alerts"
                className="text-xs text-[#663af3] hover:text-[#b6d9fc] font-medium flex items-center space-x-1 transition-colors"
              >
                <span>Alert Queue</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {summary.recent_alerts?.map((alert: any) => (
                <div
                  key={alert.alert_id}
                  className="p-3.5 bg-[rgba(5,6,15,0.6)] border border-[rgba(186,215,247,0.12)] rounded-xl flex items-start justify-between gap-3 hover:border-[rgba(186,215,247,0.24)] transition-all"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span className="font-mono text-xs font-bold text-[#b6d9fc]">
                        {alert.alert_id}
                      </span>
                      <span className="font-mono text-xs font-bold text-[#ffffff]">
                        {alert.account_id}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-md text-[9px] font-bold border ${
                          alert.severity === "CRITICAL"
                            ? "bg-red-950/60 text-red-400 border-red-800/60"
                            : "bg-amber-950/60 text-amber-400 border-amber-800/60"
                        }`}
                      >
                        {alert.severity}
                      </span>
                    </div>
                    <p className="text-xs text-[#c7d3ea] truncate">{alert.title}</p>
                  </div>

                  <Link
                    href={`/accounts/${alert.account_id}`}
                    className="btn-pill-ghost text-[11px] px-3 py-1 shrink-0"
                  >
                    View Alert
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 1/3: Charts */}
        <div className="space-y-6">
          {/* Donut Chart */}
          <div className="glass-card p-6 space-y-4">
            <div>
              <h3 className="text-lg font-display font-medium text-[#d8ecf8]">
                Risk Distribution
              </h3>
              <p className="text-xs text-[#9da7ba]">Systemwide account risk tier classification.</p>
            </div>

            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={82}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {riskPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#05060f",
                      borderColor: "rgba(186, 215, 247, 0.2)",
                      color: "#FFF",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2 pt-2 border-t border-[rgba(186,215,247,0.12)]">
              {riskPieData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-[#c7d3ea]">{item.name}</span>
                  </div>
                  <span className="font-mono text-[#ffffff] font-bold">
                    {item.value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar Chart */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-lg font-display font-medium text-[#d8ecf8]">Account Risk Counts</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskBarData} barCategoryGap="30%">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(186, 215, 247, 0.08)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="level"
                    tick={{ fill: "#9da7ba", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#9da7ba", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#05060f",
                      borderColor: "rgba(186, 215, 247, 0.2)",
                      fontSize: "12px",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {riskBarData.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
