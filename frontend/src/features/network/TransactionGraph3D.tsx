"use client";

import React, { useRef, useCallback, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import * as THREE from "three";
import type { EnrichedGraphNode, EnrichedGraphEdge } from "./types";
import { formatUsdAsInr } from "@/lib/currency";

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

// Direction communicates meaning in the investigation view; risk is conveyed
// by a restrained halo, rather than turning the whole graph orange.
const NODE_COLOURS = {
  selected: 0xef4444,
  incoming: 0x3b82f6,
  outgoing: 0xf97316,
  suspicious: 0xfacc15,
  normal: 0x94a3b8,
} as const;

function nodeRadius(node: EnrichedGraphNode): number {
  if (node.node_type === "selected") return 7;
  if (node.node_type === "suspicious") return 5.1;
  return Math.min(4.1, 2.7 + Math.max(0, node.risk_score - 50) / 100);
}

// Log-scaled edge width
function edgeWidth(edge: EnrichedGraphEdge): number {
  const amount = edge.amount ?? 0;
  return Math.min(2.4, Math.max(0.45, Math.log1p(amount / 2000) * 0.55));
}

function edgeColour(edge: EnrichedGraphEdge): string {
  if (edge.direction === "incoming") return "rgba(59, 130, 246, 0.52)";
  if (edge.direction === "outgoing") return "rgba(249, 115, 22, 0.52)";
  return "rgba(148, 163, 184, 0.25)";
}

function targetLabelSprite(label: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.font = "bold 28px monospace";
  context.textAlign = "center";
  context.fillStyle = "#fecaca";
  context.fillText(`TARGET · ${label}`, 256, 56);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(52, 9.75, 1);
  sprite.position.set(0, 13, 0);
  return sprite;
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

  // Keep the target central and arrange incoming/outgoing counterparties on
  // opposing arcs. Fixed semantic positions are intentionally used here: this
  // is an investigation view, not an unreadable global force-simulation dump.
  const graphData = useMemo(() => {
    const targetId = nodes.find((node) => node.node_type === "selected")?.id;
    const incomingIds = new Set(edges.filter((edge) => edge.direction === "incoming").map((edge) => typeof edge.source === "object" ? edge.source.id : edge.source));
    const outgoingIds = new Set(edges.filter((edge) => edge.direction === "outgoing").map((edge) => typeof edge.target === "object" ? edge.target.id : edge.target));
    const incoming = nodes.filter((node) => node.id !== targetId && incomingIds.has(node.id));
    const outgoing = nodes.filter((node) => node.id !== targetId && outgoingIds.has(node.id) && !incomingIds.has(node.id));
    const positions = new Map<string, { x: number; y: number; z: number }>();
    const placeSide = (side: EnrichedGraphNode[], x: number) => {
      side.forEach((node, index) => {
        const angle = side.length <= 1 ? 0 : -1.12 + (index / (side.length - 1)) * 2.24;
        const radius = 62 + (index % 3) * 13;
        positions.set(node.id, {
          x,
          y: Math.sin(angle) * radius,
          z: Math.cos(angle) * radius * 0.55,
        });
      });
    };
    placeSide(incoming, -105);
    placeSide(outgoing, 105);

    return {
      nodes: nodes.map((node) => {
        const pos = node.node_type === "selected" ? { x: 0, y: 0, z: 0 } : positions.get(node.id) ?? { x: 0, y: 0, z: 0 };
        return { ...node, ...pos, fx: pos.x, fy: pos.y, fz: pos.z };
      }),
      links: edges.map((edge) => ({ ...edge })),
    };
  }, [nodes, edges]);

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
      const isTarget = n.node_type === "selected";
      const isDetailSelected = selectedNode?.id === n.id;

      const r = nodeRadius(n);
      const hexColor = NODE_COLOURS[n.node_type ?? "normal"];

      const group = new THREE.Group();

      // Smooth 3D Sphere Geometry
      const geometry = new THREE.SphereGeometry(r, 24, 24);
      const material = new THREE.MeshPhongMaterial({
        color: hexColor,
        emissive: isTarget ? 0x5c0a0a : (isDetailSelected ? 0x0b2942 : 0x020617),
        shininess: 80,
        transparent: false,
        opacity: 0.96,
      });

      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      if (isTarget) {
        const label = targetLabelSprite(n.id);
        if (label) group.add(label);
      }

      // A restrained halo calls attention to the investigation target and
      // genuinely suspicious neighbours without flooding the scene with glow.
      if (isTarget || n.node_type === "suspicious" || isDetailSelected) {
        const haloRadius = r * (isTarget ? 1.55 : 1.28);
        const haloGeo = new THREE.SphereGeometry(haloRadius, 16, 16);
        const haloColor = isTarget ? NODE_COLOURS.selected : isDetailSelected ? 0x38bdf8 : NODE_COLOURS.suspicious;

        const haloMat = new THREE.MeshBasicMaterial({
          color: haloColor,
          transparent: true,
          opacity: isTarget ? 0.28 : 0.16,
          side: THREE.BackSide,
        });

        const halo = new THREE.Mesh(haloGeo, haloMat);
        group.add(halo);
      }

      return group;
    },
    [selectedNode]
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      onNodeClick(node as EnrichedGraphNode);
    },
    [onNodeClick]
  );

  const handleNodeHover = useCallback(
    (node: any) => {
      onNodeHover(node ? (node as EnrichedGraphNode) : null);
      document.body.style.cursor = node ? "pointer" : "default";
    },
    [onNodeHover]
  );

  const linkColor = useCallback((link: any) => edgeColour(link as EnrichedGraphEdge), []);

  const linkWidth = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      return edgeWidth(e);
    },
    []
  );

  // Directional flow particles representing money movement
  const linkDirectionalParticles = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      return e.amount > 100000 ? 2 : 1;
    },
    []
  );

  const linkDirectionalParticleSpeed = useCallback(() => 0.006, []);

  const linkDirectionalParticleColor = useCallback(
    (link: any) => {
      const e = link as EnrichedGraphEdge;
      return e.direction === "incoming" ? "#60a5fa" : "#fb923c";
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
        linkDirectionalParticleWidth={1.3}
        linkLabel={(link: any) => {
          const edge = link as EnrichedGraphEdge;
          const source = typeof edge.source === "object" ? (edge.source as EnrichedGraphNode).id : edge.source;
          const target = typeof edge.target === "object" ? (edge.target as EnrichedGraphNode).id : edge.target;
          return `${source} → ${target}\n${edge.count} transactions · ${formatUsdAsInr(edge.amount)}`;
        }}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        enableNodeDrag={false}
        enableNavigationControls={true}
        showNavInfo={false}
        d3AlphaDecay={0.08}
        d3VelocityDecay={0.8}
        warmupTicks={0}
        cooldownTicks={0}
      />
    </div>
  );
}
