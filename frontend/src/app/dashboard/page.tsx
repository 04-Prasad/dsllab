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
          <code className="font-mono">python scripts/setup_demo.py</code>.
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
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Fraud Monitoring Overview
          </h1>
          <p className="text-sm text-gray-400">
            Graph intelligence, EWS rule signals, and GNN node classification
            metrics.
          </p>
        </div>
        <button
          onClick={loadData}
          className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-200 font-medium flex items-center space-x-2 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {KPI_CONFIGS.map(({ key, label, sub, icon: Icon, iconColor, valueColor }) => (
          <div
            key={key}
            className="p-4 bg-[#111827] border border-gray-800 rounded-xl space-y-2 hover:border-gray-700 transition-colors"
          >
            <div className="flex items-center justify-between text-gray-400">
              <span className="text-xs font-medium">{label}</span>
              <Icon className={`w-4 h-4 ${iconColor}`} />
            </div>
            <div className={`text-2xl font-bold font-mono ${valueColor}`}>
              {(summary[key] ?? 0).toLocaleString()}
            </div>
            <div className="text-[11px] text-gray-500">{sub}</div>
          </div>
        ))}
      </div>

      {/* Main 2-section grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2/3: Tables */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top Risk Accounts Table */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">
                  Top High-Risk Accounts
                </h3>
                <p className="text-xs text-gray-400">
                  Accounts requiring immediate investigator review.
                </p>
              </div>
              <Link
                href="/accounts?risk_level=CRITICAL"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
              >
                <span>View All</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-900/60 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="p-3">Account ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Risk Level</th>
                    <th className="p-3">Score</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {summary.top_risk_accounts?.map((acc: any) => (
                    <tr
                      key={acc.account_id}
                      className="hover:bg-gray-800/40 transition-colors"
                    >
                      <td className="p-3 font-mono font-bold text-indigo-300">
                        {acc.account_id}
                      </td>
                      <td className="p-3 text-gray-300">{acc.account_type}</td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            acc.risk_level === "CRITICAL"
                              ? "bg-red-950 text-red-400 border border-red-800"
                              : acc.risk_level === "HIGH"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          }`}
                        >
                          {acc.risk_level}
                        </span>
                      </td>
                      <td className="p-3 font-mono font-bold text-white">
                        {Math.round(acc.risk_score)} / 100
                      </td>
                      <td className="p-3 text-right">
                        <Link
                          href={`/accounts/${acc.account_id}`}
                          className="px-2.5 py-1 bg-indigo-600/80 hover:bg-indigo-600 text-white rounded text-[11px] font-medium transition-colors inline-flex items-center space-x-1"
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
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">
                  Recent Investigator Alerts
                </h3>
                <p className="text-xs text-gray-400">
                  Latest high-severity fraud detection alerts.
                </p>
              </div>
              <Link
                href="/alerts"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
              >
                <span>Alert Queue</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {summary.recent_alerts?.map((alert: any) => (
                <div
                  key={alert.alert_id}
                  className="p-3 bg-[#0F1423] border border-gray-800 rounded-lg flex items-start justify-between gap-3 hover:border-gray-700 transition-colors"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {alert.alert_id}
                      </span>
                      <span className="font-mono text-xs font-bold text-white">
                        {alert.account_id}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          alert.severity === "CRITICAL"
                            ? "bg-red-950 text-red-400"
                            : "bg-amber-950 text-amber-400"
                        }`}
                      >
                        {alert.severity}
                      </span>
                    </div>
                    <p className="text-xs text-gray-300 truncate">{alert.title}</p>
                  </div>

                  <Link
                    href={`/accounts/${alert.account_id}`}
                    className="px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 text-[11px] font-medium rounded transition-colors shrink-0"
                  >
                    View
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 1/3: Charts */}
        <div className="space-y-6">
          {/* Donut Chart */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
            <div>
              <h3 className="text-base font-bold text-white">
                Risk Distribution
              </h3>
              <p className="text-xs text-gray-400">Account breakdown by level.</p>
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
                      backgroundColor: "#1F2937",
                      borderColor: "#374151",
                      color: "#FFF",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2 pt-1 border-t border-gray-800">
              {riskPieData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-gray-300">{item.name}</span>
                  </div>
                  <span className="font-mono text-white font-bold">
                    {item.value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar Chart */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
            <h3 className="text-base font-bold text-white">Account Risk Counts</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskBarData} barCategoryGap="30%">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#1F2937"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="level"
                    tick={{ fill: "#9CA3AF", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#9CA3AF", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1F2937",
                      borderColor: "#374151",
                      fontSize: "12px",
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
