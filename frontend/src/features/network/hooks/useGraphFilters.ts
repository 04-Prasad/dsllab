"use client";

import { useState, useMemo, useCallback } from "react";
import type { EnrichedGraphNode, EnrichedGraphEdge, NetworkFilters, QuickFilter } from "../types";
import { DEFAULT_FILTERS } from "../types";

interface UseGraphFiltersReturn {
  filters: NetworkFilters;
  quickFilter: QuickFilter;
  setFilters: (f: Partial<NetworkFilters>) => void;
  setQuickFilter: (qf: QuickFilter) => void;
  resetFilters: () => void;
  applyFilters: (
    nodes: EnrichedGraphNode[],
    edges: EnrichedGraphEdge[]
  ) => { nodes: EnrichedGraphNode[]; edges: EnrichedGraphEdge[] };
}

export function useGraphFilters(): UseGraphFiltersReturn {
  const [filters, setFiltersState] = useState<NetworkFilters>(DEFAULT_FILTERS);
  const [quickFilter, setQuickFilterState] = useState<QuickFilter>("ALL");

  const setFilters = useCallback((partial: Partial<NetworkFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...partial }));
  }, []);

  const setQuickFilter = useCallback((qf: QuickFilter) => {
    setQuickFilterState(qf);
    // Quick filter presets
    if (qf === "ALL") {
      setFiltersState(DEFAULT_FILTERS);
    } else if (qf === "FRAUD_ONLY") {
      setFiltersState({ ...DEFAULT_FILTERS, fraudOnly: true });
    } else if (qf === "RING_MEMBERS") {
      setFiltersState({ ...DEFAULT_FILTERS, ringMembersOnly: true });
    } else if (qf === "HIGH_RISK") {
      setFiltersState({ ...DEFAULT_FILTERS, riskThreshold: 60 });
    }
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
    setQuickFilterState("ALL");
  }, []);

  const applyFilters = useCallback(
    (
      allNodes: EnrichedGraphNode[],
      allEdges: EnrichedGraphEdge[]
    ): { nodes: EnrichedGraphNode[]; edges: EnrichedGraphEdge[] } => {
      let filteredNodes = allNodes;

      // Risk threshold filter
      if (filters.riskThreshold > 0) {
        filteredNodes = filteredNodes.filter((n) => n.risk_score >= filters.riskThreshold);
      }

      // Fraud / high-risk only
      if (filters.fraudOnly) {
        filteredNodes = filteredNodes.filter(
          (n) => n.is_fraud || n.risk_level === "HIGH" || n.risk_level === "CRITICAL"
        );
      }

      // Ring members only
      if (filters.ringMembersOnly) {
        filteredNodes = filteredNodes.filter((n) => n.role === "RING_MEMBER");
      }

      // Has EWS signals
      if (filters.hasEws) {
        filteredNodes = filteredNodes.filter((n) => n.ews_count > 0);
      }

      // Hubs only
      if (filters.hubsOnly) {
        filteredNodes = filteredNodes.filter((n) => n.role === "HUB");
      }

      const visibleIds = new Set(filteredNodes.map((n) => n.id));

      // Keep only edges where both endpoints are visible
      const filteredEdges = allEdges.filter((e) => {
        const src = typeof e.source === "string" ? e.source : e.source.id;
        const tgt = typeof e.target === "string" ? e.target : e.target.id;
        return visibleIds.has(src) && visibleIds.has(tgt);
      });

      return { nodes: filteredNodes, edges: filteredEdges };
    },
    [filters]
  );

  return { filters, quickFilter, setFilters, setQuickFilter, resetFilters, applyFilters };
}
