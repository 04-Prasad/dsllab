"use client";

import React, { useRef, useCallback, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import * as THREE from "three";
import type { EnrichedGraphNode, EnrichedGraphEdge } from "./types";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex flex-col items-center justify-center w-full h-full gap-4 text-[#94a3b8]">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-[#38bdf8]/20" />
        <div className="absolute inset-0 rounded-full border-4 border-t-[#38bdf8] animate-spin" />
      </div>
      <p className="text-sm font-mono animate-pulse">Initialising 3D Investigation Space…</p>
    </div>
  ),
});

// ── GraphGuard Spec Risk Colors ─────────────────────────────────────────────

function riskColourHex(level: string, role: string): number {
  if (role === "RING_MEMBER") return 0xa855f7; // Purple for ML Ring Member
  switch (level) {
    case "CRITICAL": return 0xef4444; // Red
    case "HIGH":     return 0xf97316; // Orange
    case "MEDIUM":   return 0xfacc15; // Yellow/Amber
    default:         return 0x22c55e; // Emerald Green
  }
}

function riskColourStr(level: string, role: string): string {
  if (role === "RING_MEMBER") return "#a855f7";
  switch (level) {
    case "CRITICAL": return "#ef4444";
    case "HIGH":     return "#f97316";
    case "MEDIUM":   return "#facc15";
    default:         return "#22c55e";
  }
}

// Preserve existing metric: degree + risk score boost
function nodeRadius(node: EnrichedGraphNode): number {
  const degreeCount = (node.in_degree || 0) + (node.out_degree || 0);
  const degreeBoost = Math.log1p(degreeCount) * 1.4;
  const riskBoost = node.risk_score > 80 ? 4 : node.risk_score > 60 ? 2.5 : 0;
  const roleBoost = node.role === "RING_MEMBER" ? 3 : node.role === "HUB" ? 4 : node.role === "MULE" ? 2.5 : 0;
  return Math.max(3.5, 3.5 + degreeBoost + riskBoost + roleBoost);
}

// Log-scaled edge width
function edgeWidth(edge: EnrichedGraphEdge): number {
  const amount = edge.amount ?? 0;
  return Math.max(0.6, Math.log1p(amount / 2000) * 0.9);
}

function edgeColour(edge: EnrichedGraphEdge, isSelectedFlow: boolean): string {
  if (isSelectedFlow) return "rgba(0, 245, 255, 0.85)";
  const src = edge.source as EnrichedGraphNode;
  const tgt = edge.target as EnrichedGraphNode;
  if (typeof src === "object" && typeof tgt === "object") {
    const maxRisk = Math.max(src.risk_score ?? 0, tgt.risk_score ?? 0);
    if (maxRisk >= 80) return "rgba(239, 68, 68, 0.70)";
    if (maxRisk >= 60) return "rgba(249, 115, 22, 0.55)";
  }
  return "rgba(100, 116, 139, 0.30)"; // Cool gray-blue
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

  // Compute connected neighbor IDs when selectedNode is active for Focus Mode
  const connectedNodeIds = useMemo(() => {
    if (!selectedNode) return new Set<string>();
    const set = new Set<string>();
    edges.forEach((e) => {
      const sId = typeof e.source === "object" ? (e.source as any).id : e.source;
      const tId = typeof e.target === "object" ? (e.target as any).id : e.target;
      if (sId === selectedNode.id) set.add(tId);
      if (tId === selectedNode.id) set.add(sId);
    });
    return set;
  }, [selectedNode, edges]);

  // Memoize graph data
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
      const distance = 140;
      const x = (node.x ?? 0);
      const y = (node.y ?? 0);
      const z = (node.z ?? 0);
      fgRef.current.cameraPosition(
        { x: x + distance, y: y + distance, z: z + distance },
        { x, y, z },
        1200
      );
    },
    [nodes]
  );

  // Watch focusNodeId — animate camera when it changes
  useEffect(() => {
    if (focusNodeId) {
      const timer = setTimeout(() => focusNode(focusNodeId), 300);
      return () => clearTimeout(timer);
    }
  }, [focusNodeId, focusNode]);

  // Node label
  const nodeLabel = useCallback((node: any): string => {
    const n = node as EnrichedGraphNode;
    const ewsStr = n.ews_types.length > 0 ? `\n⚠ EWS: ${n.ews_types.join(", ")}` : "";
    return `${n.id} [${n.risk_level} Risk]\nRole: ${n.role}${ewsStr}`;
  }, []);

  // Custom 3D Node Mesh Generator: Spheres with Phong specular highlights & risk halos
  const nodeThreeObject = useCallback(
    (node: any) => {
      const n = node as EnrichedGraphNode;
      const isSelected = selectedNode && n.id === selectedNode.id;
      const isNeighbor = selectedNode && connectedNodeIds.has(n.id);
      const isDimmed = selectedNode && !isSelected && !isNeighbor;

      const r = nodeRadius(n);
      const hexColor = isSelected ? 0x00f5ff : riskColourHex(n.risk_level, n.role);

      const group = new THREE.Group();

      // Smooth 3D Sphere Geometry
      const geometry = new THREE.SphereGeometry(r, 24, 24);
      const material = new THREE.MeshPhongMaterial({
        color: hexColor,
        emissive: isSelected ? 0x00a8ff : (n.risk_score >= 80 ? 0x440000 : 0x020617),
        shininess: 80,
        transparent: true,
        opacity: isDimmed ? 0.15 : 0.95,
      });

      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      // Outer Risk Halo / Glow Ring for High, Critical, Ring Member, or Selected accounts
      if (!isDimmed && (n.risk_score >= 60 || n.role === "RING_MEMBER" || isSelected)) {
        const haloRadius = r * (isSelected ? 1.5 : n.risk_score >= 80 ? 1.4 : 1.25);
        const haloGeo = new THREE.SphereGeometry(haloRadius, 16, 16);
        const haloColor = isSelected
          ? 0x00f5ff
          : n.risk_score >= 80
          ? 0xef4444
          : n.risk_score >= 60
          ? 0xf97316
          : 0xa855f7;

        const haloMat = new THREE.MeshBasicMaterial({
          color: haloColor,
          transparent: true,
          opacity: isSelected ? 0.35 : n.risk_score >= 80 ? 0.28 : 0.18,
          side: THREE.BackSide,
        });

        const halo = new THREE.Mesh(haloGeo, haloMat);
        group.add(halo);
      }

      return group;
    },
    [selectedNode, connectedNodeIds]
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
      document.body.style.cursor = node ? "pointer" : "default";
    },
    [onNodeHover]
  );

  const linkColor = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      const sId = typeof e.source === "object" ? (e.source as any).id : e.source;
      const tId = typeof e.target === "object" ? (e.target as any).id : e.target;
      const isSelectedFlow = !!(selectedNode && (sId === selectedNode.id || tId === selectedNode.id));

      if (selectedNode && !isSelectedFlow) return "rgba(30, 41, 59, 0.10)";
      return edgeColour(e, isSelectedFlow);
    },
    [selectedNode]
  );

  const linkWidth = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      const sId = typeof e.source === "object" ? (e.source as any).id : e.source;
      const tId = typeof e.target === "object" ? (e.target as any).id : e.target;
      const isSelectedFlow = !!(selectedNode && (sId === selectedNode.id || tId === selectedNode.id));
      const baseW = edgeWidth(e);
      return isSelectedFlow ? baseW * 1.8 : baseW;
    },
    [selectedNode]
  );

  // Directional flow particles representing money movement
  const linkDirectionalParticles = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      const sId = typeof e.source === "object" ? (e.source as any).id : e.source;
      const tId = typeof e.target === "object" ? (e.target as any).id : e.target;
      const isSelectedFlow = !!(selectedNode && (sId === selectedNode.id || tId === selectedNode.id));

      if (selectedNode && !isSelectedFlow) return 0;
      const amount = e.amount ?? 0;
      if (amount > 100000) return 5;
      if (amount > 10000) return 3;
      return 2;
    },
    [selectedNode]
  );

  const linkDirectionalParticleSpeed = useCallback(() => 0.006, []);

  const linkDirectionalParticleColor = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      const src = e.source as EnrichedGraphNode;
      if (typeof src === "object" && src.risk_level === "CRITICAL") return "#ef4444";
      if (typeof src === "object" && src.risk_level === "HIGH") return "#f97316";
      return "#38bdf8"; // Cyan directional flow
    },
    []
  );

  return (
    <div className="w-full h-full overflow-hidden bg-[#020617] relative">
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="#020617"
        nodeLabel={nodeLabel}
        nodeThreeObject={nodeThreeObject}
        linkColor={linkColor}
        linkWidth={linkWidth}
        linkDirectionalParticles={linkDirectionalParticles}
        linkDirectionalParticleSpeed={linkDirectionalParticleSpeed}
        linkDirectionalParticleColor={linkDirectionalParticleColor}
        linkDirectionalParticleWidth={2.5}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        enableNodeDrag={true}
        enableNavigationControls={true}
        showNavInfo={false}
        d3AlphaDecay={0.015}
        d3VelocityDecay={0.25}
        warmupTicks={60}
        cooldownTicks={300}
      />
    </div>
  );
}
