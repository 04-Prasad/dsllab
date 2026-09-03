"use client";

import React, { useRef, useCallback, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import type { EnrichedGraphNode, EnrichedGraphEdge } from "./types";

// ── Dynamic import — Three.js requires browser APIs (no SSR) ─────────────────
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex flex-col items-center justify-center w-full h-full gap-4 text-gray-400">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-indigo-500/30" />
        <div className="absolute inset-0 rounded-full border-4 border-t-indigo-500 animate-spin" />
      </div>
      <p className="text-sm font-mono animate-pulse">Initialising 3D Engine…</p>
    </div>
  ),
});

// ── Colour helpers ───────────────────────────────────────────────────────────

function riskColour(level: string): string {
  switch (level) {
    case "CRITICAL": return "#ef4444";   // red-500
    case "HIGH":     return "#f97316";   // orange-500
    case "MEDIUM":   return "#eab308";   // yellow-500
    default:         return "#22c55e";   // green-500
  }
}

function roleColourMod(role: string, base: string): string {
  // Overlay a subtle tint based on role
  switch (role) {
    case "HUB":                 return base;           // keep risk colour, size handles it
    case "BRIDGE":              return "#60a5fa";       // blue-400 tint for bridges
    case "RING_MEMBER":         return "#c084fc";       // purple-400
    case "MULE":                return "#fb923c";       // orange-400
    case "SUSPICIOUS_NEIGHBOUR":return "#facc15";       // yellow-400
    default:                    return base;
  }
}

function nodeColour(node: EnrichedGraphNode): string {
  const base = riskColour(node.risk_level);
  return roleColourMod(node.role, base);
}

// Node radius: base size + degree contribution + risk boost
function nodeRadius(node: EnrichedGraphNode): number {
  const degreeBoost = Math.log1p(node.in_degree + node.out_degree) * 1.2;
  const riskBoost = node.risk_score > 80 ? 3 : node.risk_score > 60 ? 1.5 : 0;
  const roleBoost = node.role === "HUB" ? 4 : node.role === "BRIDGE" ? 2 : 0;
  return Math.max(3, 3 + degreeBoost + riskBoost + roleBoost);
}

// Log-scaled edge width
function edgeWidth(edge: EnrichedGraphEdge): number {
  const amount = edge.amount ?? 0;
  return Math.max(0.5, Math.log1p(amount / 1000) * 0.8);
}

function edgeColour(edge: EnrichedGraphEdge): string {
  // If either endpoint is known high-risk, colour the edge red
  const src = edge.source as EnrichedGraphNode;
  const tgt = edge.target as EnrichedGraphNode;
  if (typeof src === "object" && typeof tgt === "object") {
    const maxRisk = Math.max(src.risk_score ?? 0, tgt.risk_score ?? 0);
    if (maxRisk >= 80) return "rgba(239,68,68,0.55)";
    if (maxRisk >= 60) return "rgba(249,115,22,0.45)";
  }
  return "rgba(99,102,241,0.25)";   // indigo dim
}

// ── Props ────────────────────────────────────────────────────────────────────

interface TransactionGraph3DProps {
  nodes: EnrichedGraphNode[];
  edges: EnrichedGraphEdge[];
  selectedNode: EnrichedGraphNode | null;
  onNodeClick: (node: EnrichedGraphNode) => void;
  onNodeHover: (node: EnrichedGraphNode | null) => void;
  focusNodeId: string | null;
  width: number;
  height: number;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function TransactionGraph3D({
  nodes,
  edges,
  selectedNode,
  onNodeClick,
  onNodeHover,
  focusNodeId,
  width,
  height,
}: TransactionGraph3DProps) {
  const fgRef = useRef<any>(null);

  // Memoize graph data to avoid recreating on every render
  const graphData = useMemo(
    () => ({ nodes: nodes as any[], links: edges as any[] }),
    [nodes, edges]
  );

  // Focus camera on a specific node by id
  const focusNode = useCallback(
    (nodeId: string) => {
      if (!fgRef.current) return;
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;
      const distance = 120;
      const x = (node.x ?? 0);
      const y = (node.y ?? 0);
      const z = (node.z ?? 0);
      fgRef.current.cameraPosition(
        { x: x + distance, y: y + distance, z: z + distance },
        { x, y, z },
        1200 // ms transition
      );
    },
    [nodes]
  );

  // Watch focusNodeId — animate camera when it changes
  useEffect(() => {
    if (focusNodeId) {
      // Slight delay to let simulation settle a bit first
      const timer = setTimeout(() => focusNode(focusNodeId), 300);
      return () => clearTimeout(timer);
    }
  }, [focusNodeId, focusNode]);

  // Node label (Three.js canvas label)
  const nodeLabel = useCallback((node: any): string => {
    const n = node as EnrichedGraphNode;
    const ewsStr = n.ews_types.length > 0 ? `\n⚠ ${n.ews_types.join(", ")}` : "";
    return `${n.id} [${n.risk_level}] ${n.role !== "NORMAL" ? `• ${n.role}` : ""}${ewsStr}`;
  }, []);

  // Custom node canvas object — draws coloured sphere with optional glow
  const nodeThreeObject = useCallback(
    (node: any) => {
      // We let react-force-graph-3d render default spheres; we customise colour
      // and size via nodeColor + nodeRelSize. Custom Three.js objects would
      // require importing THREE directly here which causes SSR issues.
      return undefined; // fall back to default sphere
    },
    []
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      onNodeClick(node as EnrichedGraphNode);
      focusNode((node as EnrichedGraphNode).id);
    },
    [onNodeClick, focusNode]
  );

  const handleNodeHover = useCallback(
    (node: any) => {
      onNodeHover(node ? (node as EnrichedGraphNode) : null);
      // Change cursor style
      document.body.style.cursor = node ? "pointer" : "default";
    },
    [onNodeHover]
  );

  // Highlight selected node
  const nodeColor = useCallback(
    (node: any) => {
      const n = node as EnrichedGraphNode;
      if (selectedNode && n.id === selectedNode.id) return "#00f5ff"; // cyan highlight
      return nodeColour(n);
    },
    [selectedNode]
  );

  const nodeVal = useCallback((node: any) => {
    const n = node as EnrichedGraphNode;
    const r = nodeRadius(n);
    return r * r; // nodeVal is area, so square the radius
  }, []);

  const linkColor = useCallback((link: any) => edgeColour(link as EnrichedGraphEdge), []);
  const linkWidth = useCallback((link: any) => edgeWidth(link as EnrichedGraphEdge), []);

  // Directional particles represent money flow direction
  const linkDirectionalParticles = useCallback((link: any) => {
    const e = link as EnrichedGraphEdge;
    // More particles for bigger amounts
    const amount = e.amount ?? 0;
    if (amount > 100000) return 6;
    if (amount > 10000) return 4;
    return 2;
  }, []);

  const linkDirectionalParticleSpeed = useCallback(() => 0.005, []);

  const linkDirectionalParticleColor = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      const src = e.source as EnrichedGraphNode;
      if (typeof src === "object" && src.risk_level === "CRITICAL") return "#ef4444";
      return "#818cf8"; // indigo-400
    },
    []
  );

  return (
    <div className="w-full h-full rounded-xl overflow-hidden">
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="#050814"
        nodeLabel={nodeLabel}
        nodeColor={nodeColor}
        nodeVal={nodeVal}
        nodeRelSize={4}
        nodeOpacity={0.95}
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkDirectionalParticles={linkDirectionalParticles}
        linkDirectionalParticleSpeed={linkDirectionalParticleSpeed}
        linkDirectionalParticleColor={linkDirectionalParticleColor}
        linkDirectionalParticleWidth={2}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        enableNodeDrag={true}
        enableNavigationControls={true}
        showNavInfo={false}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        warmupTicks={50}
        cooldownTicks={200}
      />
    </div>
  );
}
