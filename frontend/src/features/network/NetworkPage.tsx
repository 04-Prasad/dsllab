"use client";

import React, {
  useState, useCallback, useEffect, useRef, useMemo
} from "react";
import { AlertCircle, RefreshCw, Network } from "lucide-react";

import { useNetworkData } from "./hooks/useNetworkData";
import { useGraphFilters }  from "./hooks/useGraphFilters";
import NetworkSidebar       from "./NetworkSidebar";
import NetworkStats         from "./NetworkStats";
import NodeDetailsDrawer    from "./NodeDetailsDrawer";
import RiskLegend           from "./RiskLegend";
import NetworkControls      from "./NetworkControls";
import DetectiveTour        from "./DetectiveTour";
import TransactionGraph3D   from "./TransactionGraph3D";
import type { EnrichedGraphNode } from "./types";

// ── Container dimensions hook ─────────────────────────────────────────────────

function useContainerSize(ref: React.RefObject<HTMLDivElement>) {
  const [size, setSize] = useState({ width: 800, height: 600 });
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setSize({ width: Math.floor(width), height: Math.floor(height) });
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [ref]);
  return size;
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function NetworkPage() {
  const { data, loading, error, load } = useNetworkData();
  const {
    filters, quickFilter,
    setFilters, setQuickFilter, resetFilters, applyFilters,
  } = useGraphFilters();

  const [selectedNode, setSelectedNode] = useState<EnrichedGraphNode | null>(null);
  const [hoveredNode,  setHoveredNode]  = useState<EnrichedGraphNode | null>(null);
  const [focusNodeId,  setFocusNodeId]  = useState<string | null>(null);
  const [searchQuery,  setSearchQuery]  = useState<string>("");
  const [searchError,  setSearchError]  = useState<string | null>(null);

  const graphContainerRef = useRef<HTMLDivElement>(null);
  const fgRef             = useRef<any>(null);
  const { width, height } = useContainerSize(graphContainerRef);

  // ── Initial load on mount ─────────────────────────────────────────────────
  useEffect(() => {
    load({ limit: 200 });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Compute filtered graph ────────────────────────────────────────────────
  const { nodes: filteredNodes, edges: filteredEdges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    return applyFilters(data.nodes, data.edges);
  }, [data, applyFilters]);

  // ── Search: find node in loaded data or reload centred on account ─────────
  const handleSearch = useCallback(
    async (accountId: string) => {
      setSearchError(null);
      setSearchQuery(accountId);

      // Check if node is already loaded
      const found = data?.nodes.find((n) => n.id === accountId);
      if (found) {
        setSelectedNode(found);
        setFocusNodeId(accountId);
        return;
      }

      // Reload centred on this account
      try {
        await load({ account_id: accountId, limit: 150 });
        // focusNodeId will be set after load completes — use a small delay
        setTimeout(() => {
          setFocusNodeId(accountId);
        }, 600);
      } catch {
        setSearchError(`Account ${accountId} was not found.`);
      }
    },
    [data, load]
  );

  // ── Camera controls ───────────────────────────────────────────────────────
  const handleZoomIn = useCallback(() => {
    if (!fgRef.current) return;
    const cam = fgRef.current.camera();
    cam.position.multiplyScalar(0.8);
  }, []);

  const handleZoomOut = useCallback(() => {
    if (!fgRef.current) return;
    const cam = fgRef.current.camera();
    cam.position.multiplyScalar(1.25);
  }, []);

  const handleResetView = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.cameraPosition({ x: 0, y: 0, z: 400 }, { x: 0, y: 0, z: 0 }, 800);
    }
    setSelectedNode(null);
    setFocusNodeId(null);
    resetFilters();
  }, [resetFilters]);

  const handleFullscreen = useCallback(() => {
    const el = graphContainerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().catch(console.warn);
    } else {
      document.exitFullscreen().catch(console.warn);
    }
  }, []);

  const handleReload = useCallback(() => {
    load({ limit: 200 });
  }, [load]);

  // ── Tour integration ──────────────────────────────────────────────────────
  const handleTourFocus = useCallback(
    (accountId: string) => {
      handleSearch(accountId);
    },
    [handleSearch]
  );

  // ── Node interaction ──────────────────────────────────────────────────────
  const handleNodeClick = useCallback((node: EnrichedGraphNode) => {
    setSelectedNode(node);
    setFocusNodeId(node.id);
  }, []);

  const handleNodeHover = useCallback((node: EnrichedGraphNode | null) => {
    setHoveredNode(node);
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] -m-6 overflow-hidden">

      {/* ─ Top bar ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[rgba(186,215,247,0.12)] bg-[#05060f] shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#663af3] flex items-center justify-center shadow-[0_0_16px_rgba(102,58,243,0.5)] border border-[rgba(186,215,247,0.2)]">
            <Network className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-display font-medium text-skywash tracking-tight leading-none">
              Transaction Network
            </h1>
            <p className="text-[10px] text-[#9da7ba] font-mono mt-0.5">3D Graph Intelligence Layer</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Stats */}
          <NetworkStats stats={data?.stats ?? null} loading={loading} />

          {/* Detective Tour */}
          <DetectiveTour onFocusAccount={handleTourFocus} onClose={handleResetView} />
        </div>
      </div>

      {/* ─ Main workspace ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">

        {/* Sidebar */}
        <NetworkSidebar
          stats={data?.stats ?? null}
          filters={filters}
          quickFilter={quickFilter}
          onFilterChange={setFilters}
          onQuickFilter={setQuickFilter}
          onResetFilters={resetFilters}
          onSearch={handleSearch}
          onReload={handleReload}
          loading={loading}
        />

        {/* Graph area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#05060f] relative">

          {/* Search error banner */}
          {searchError && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 px-4 py-2 bg-red-950/90 border border-red-700 rounded-xl text-xs text-red-300 shadow-xl backdrop-blur-md">
              <AlertCircle className="w-3.5 h-3.5" />
              {searchError}
              <button onClick={() => setSearchError(null)} className="ml-2 text-red-400 hover:text-red-200">✕</button>
            </div>
          )}

          {/* Loading overlay */}
          {loading && (
            <div className="absolute inset-0 z-30 bg-[#05060f]/80 flex flex-col items-center justify-center gap-4 backdrop-blur-md">
              <div className="relative w-14 h-14">
                <div className="absolute inset-0 rounded-full border-4 border-[#663af3]/20" />
                <div className="absolute inset-0 rounded-full border-4 border-t-[#663af3] animate-spin" />
              </div>
              <p className="text-sm font-mono text-[#c7d3ea] animate-pulse">
                Loading transaction network…
              </p>
            </div>
          )}

          {/* Error overlay */}
          {error && !loading && (
            <div className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-4 text-[#9da7ba] bg-[#05060f]/90 backdrop-blur-md">
              <AlertCircle className="w-10 h-10 text-red-500" />
              <p className="text-sm font-semibold text-red-400">Unable to load transaction network.</p>
              <p className="text-xs text-[#9da7ba] max-w-xs text-center">{error}</p>
              <button
                onClick={handleReload}
                className="btn-void-violet text-xs px-4 py-2 flex items-center gap-1.5"
              >
                <RefreshCw className="w-4 h-4" /> Retry Connection
              </button>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && filteredNodes.length === 0 && data && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 text-[#9da7ba]">
              <Network className="w-10 h-10 opacity-30 text-[#b6d9fc]" />
              <p className="text-sm">No accounts match the selected filters.</p>
              <button
                onClick={resetFilters}
                className="text-xs text-[#663af3] hover:text-[#b6d9fc] underline"
              >
                Clear filters
              </button>
            </div>
          )}

          {/* 3D Graph Canvas */}
          <div ref={graphContainerRef} className="flex-1 w-full relative">
            {!error && (
              <TransactionGraph3D
                nodes={filteredNodes}
                edges={filteredEdges}
                selectedNode={selectedNode}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                focusNodeId={focusNodeId}
                width={width}
                height={height}
              />
            )}

            {/* Hover tooltip */}
            {hoveredNode && hoveredNode.id !== selectedNode?.id && (
              <div className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-none z-20">
                <div className="px-3 py-1.5 glass-panel text-xs text-white font-mono shadow-2xl flex items-center gap-2 border border-[rgba(186,215,247,0.2)]">
                  <span className="font-bold text-[#b6d9fc]">{hoveredNode.id}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded-md text-[10px] font-bold border ${
                      hoveredNode.risk_level === "CRITICAL" ? "bg-red-950/80 text-red-400 border-red-800" :
                      hoveredNode.risk_level === "HIGH"     ? "bg-amber-950/80 text-amber-400 border-amber-800" :
                      hoveredNode.risk_level === "MEDIUM"   ? "bg-yellow-950/80 text-yellow-400 border-yellow-800" :
                                                              "bg-emerald-950/80 text-emerald-400 border-emerald-800"
                    }`}
                  >
                    {hoveredNode.risk_level}
                  </span>
                  {hoveredNode.role !== "NORMAL" && (
                    <span className="text-[#9da7ba]">{hoveredNode.role}</span>
                  )}
                  {hoveredNode.ews_count > 0 && (
                    <span className="text-amber-300">⚠ {hoveredNode.ews_count}</span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Bottom toolbar */}
          <div className="shrink-0 px-6 py-2.5 border-t border-[rgba(186,215,247,0.12)] bg-[#05060f] flex items-center justify-between gap-4 z-20">
            <RiskLegend />
            <NetworkControls
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onReset={handleResetView}
              onFullscreen={handleFullscreen}
            />
          </div>
        </div>

        {/* Node Details Drawer */}
        {selectedNode && (
          <NodeDetailsDrawer
            node={selectedNode}
            onClose={() => { setSelectedNode(null); setFocusNodeId(null); }}
          />
        )}
      </div>
    </div>
  );
}
