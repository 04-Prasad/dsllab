"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Network,
  Search,
  RefreshCw,
  ExternalLink,
  AlertCircle,
} from "lucide-react";

type GraphNode = {
  id: string;
  label: string;
  risk_score: number;
  risk_level: string;
  account_type: string;
};

type GraphEdge = {
  source: string;
  target: string;
  amount: number;
  count: number;
};

// ── Inner component uses useSearchParams (needs Suspense wrapper) ──────────────

function GraphExplorerInner() {
  const searchParams = useSearchParams();
  const initialAccount = searchParams.get("account_id") ?? "A102";

  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({
    nodes: [],
    edges: [],
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchAccount, setSearchAccount] = useState<string>(initialAccount);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const loadGraph = useCallback(async (accId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const target = accId ?? searchAccount;
      const data = await api.searchGraph({
        account_id: target || undefined,
        limit: 80,
      });
      setGraphData(data);
      if (data.nodes?.length > 0) {
        const found =
          data.nodes.find((n: GraphNode) => n.id === target) ?? data.nodes[0];
        setSelectedNode(found);
      } else {
        setSelectedNode(null);
      }
    } catch (err: any) {
      setError(err.message ?? "Failed to load graph data");
    } finally {
      setLoading(false);
    }
  }, [searchAccount]);

  useEffect(() => {
    loadGraph(initialAccount);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadGraph(searchAccount);
  };

  const riskColor = (level: string) => {
    if (level === "CRITICAL") return "bg-red-950 border-red-700 text-red-300";
    if (level === "HIGH") return "bg-amber-950 border-amber-700 text-amber-300";
    if (level === "MEDIUM") return "bg-yellow-950 border-yellow-700 text-yellow-300";
    return "bg-gray-900 border-gray-700 text-gray-300";
  };

  const riskDot = (level: string) => {
    if (level === "CRITICAL") return "bg-red-500";
    if (level === "HIGH") return "bg-amber-500";
    if (level === "MEDIUM") return "bg-yellow-500";
    return "bg-emerald-500";
  };

  const selectedNodeEdges = selectedNode
    ? graphData.edges.filter(
        (e) => e.source === selectedNode.id || e.target === selectedNode.id
      )
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Interactive Graph Explorer
          </h1>
          <p className="text-sm text-gray-400">
            Visualise transaction networks, fan-in mule patterns, and circular
            money flows. Click any node to inspect.
          </p>
        </div>
      </div>

      {/* Control Bar */}
      <div className="p-4 bg-[#111827] border border-gray-800 rounded-xl flex flex-col md:flex-row items-center justify-between gap-4">
        <form
          onSubmit={handleSearchSubmit}
          className="relative flex-1 w-full flex items-center gap-2"
        >
          <Search className="w-4 h-4 text-gray-500 absolute left-3" />
          <input
            type="text"
            value={searchAccount}
            onChange={(e) => setSearchAccount(e.target.value)}
            placeholder="Enter Account ID (e.g. A102, A450, A500)…"
            className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Load
          </button>
        </form>

        <div className="flex items-center gap-2 flex-wrap">
          {["A102", "A450", "A500", "A601", "A700"].map((id) => (
            <button
              key={id}
              onClick={() => {
                setSearchAccount(id);
                loadGraph(id);
              }}
              className={`px-3 py-1.5 rounded text-xs font-mono font-semibold border transition-colors ${
                searchAccount === id
                  ? "bg-indigo-600 border-indigo-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {id}
            </button>
          ))}
          <button
            onClick={() => loadGraph(searchAccount)}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded text-xs font-medium transition-colors flex items-center space-x-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload</span>
          </button>
        </div>
      </div>

      {/* Canvas + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Canvas */}
        <div className="lg:col-span-3 bg-[#111827] border border-gray-800 rounded-xl p-6 min-h-[520px] flex flex-col gap-4">
          {/* Legend */}
          <div className="flex items-center justify-between text-xs text-gray-400 border-b border-gray-800/80 pb-3">
            <span className="font-mono">
              Nodes:{" "}
              <strong className="text-white">{graphData.nodes.length}</strong>
              {" "}| Edges:{" "}
              <strong className="text-white">{graphData.edges.length}</strong>
            </span>
            <div className="flex items-center space-x-4">
              {[
                { label: "Low", dot: "bg-emerald-500" },
                { label: "Medium", dot: "bg-yellow-500" },
                { label: "High", dot: "bg-amber-500" },
                { label: "Critical", dot: "bg-red-500 animate-pulse" },
              ].map(({ label, dot }) => (
                <span key={label} className="flex items-center space-x-1">
                  <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
                  <span>{label}</span>
                </span>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center flex-1 space-y-3">
              <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-mono text-gray-400">
                Rendering financial graph topology…
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center flex-1 space-y-3 text-red-400">
              <AlertCircle className="w-8 h-8" />
              <p className="text-sm font-semibold">{error}</p>
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center flex-1 text-gray-500 text-sm">
              No graph data returned. Try a different account.
            </div>
          ) : (
            <div className="flex-1 flex flex-wrap gap-3 items-start content-start p-4 bg-gray-950/50 rounded-xl border border-gray-800/80 min-h-[380px] overflow-y-auto">
              {graphData.nodes.map((node) => (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  title={`${node.id} — ${node.risk_level} (${node.risk_score}/100)`}
                  className={`relative p-3 rounded-xl border flex flex-col items-center gap-1 transition-all hover:scale-105 ${riskColor(node.risk_level)} ${
                    selectedNode?.id === node.id
                      ? "ring-2 ring-indigo-400 ring-offset-1 ring-offset-gray-950 shadow-lg shadow-indigo-500/20 scale-105"
                      : ""
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${riskDot(node.risk_level)}`} />
                  <span className="font-mono text-xs font-bold">{node.id}</span>
                  <span className="text-[10px] opacity-75">
                    {node.risk_score}/100
                  </span>
                </button>
              ))}
            </div>
          )}

          <p className="text-[11px] text-gray-500 font-mono text-center">
            Click any account node to inspect risk details and connections.
          </p>
        </div>

        {/* Inspector */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-5 overflow-y-auto max-h-[600px]">
          <h3 className="text-base font-bold text-white flex items-center space-x-2">
            <Network className="w-4 h-4 text-indigo-400" />
            <span>Node Inspector</span>
          </h3>

          {selectedNode ? (
            <div className="space-y-5 text-xs">
              <div className="p-3 bg-gray-900 border border-gray-800 rounded-lg space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Account ID</span>
                  <span className="font-mono font-bold text-indigo-300">
                    {selectedNode.id}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Type</span>
                  <span className="text-gray-200">{selectedNode.account_type}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Risk Level</span>
                  <span
                    className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                      selectedNode.risk_level === "CRITICAL"
                        ? "bg-red-950 text-red-400 border border-red-800"
                        : selectedNode.risk_level === "HIGH"
                        ? "bg-amber-950 text-amber-400 border border-amber-800"
                        : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                    }`}
                  >
                    {selectedNode.risk_level}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Risk Score</span>
                  <span className="font-mono font-bold text-white">
                    {selectedNode.risk_score} / 100
                  </span>
                </div>
                <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${riskDot(selectedNode.risk_level)} transition-all`}
                    style={{ width: `${selectedNode.risk_score}%` }}
                  />
                </div>
              </div>

              {selectedNodeEdges.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
                    Connections ({selectedNodeEdges.length})
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {selectedNodeEdges.map((edge, i) => {
                      const isOutgoing = edge.source === selectedNode.id;
                      return (
                        <div
                          key={i}
                          className="p-2 bg-gray-900 border border-gray-800 rounded-lg text-[11px] space-y-1"
                        >
                          <div className="flex items-center gap-1 font-mono">
                            <span className={isOutgoing ? "text-amber-400" : "text-indigo-400"}>
                              {edge.source}
                            </span>
                            <span className="text-gray-500">to</span>
                            <span className={!isOutgoing ? "text-amber-400" : "text-indigo-400"}>
                              {edge.target}
                            </span>
                          </div>
                          <div className="flex justify-between text-gray-400">
                            <span>
                              Rs.{Number(edge.amount).toLocaleString("en-IN")}
                            </span>
                            <span>
                              {edge.count} txn{edge.count !== 1 ? "s" : ""}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <Link
                href={`/accounts/${selectedNode.id}`}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-xs flex items-center justify-center space-x-1 transition-colors"
              >
                <span>Full Investigation File</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <p className="text-xs text-gray-500">
              Select a node from the canvas to view its attributes.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Outer page wraps inner component in Suspense (required for useSearchParams) ─

export default function GraphExplorerPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[50vh] space-x-3 text-gray-400">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-mono">Loading Graph Explorer…</span>
        </div>
      }
    >
      <GraphExplorerInner />
    </Suspense>
  );
}
