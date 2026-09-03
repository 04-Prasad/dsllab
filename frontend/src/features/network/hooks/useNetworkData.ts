"use client";

import { useState, useCallback, useRef } from "react";
import { fetchNetworkGraph, type NetworkQueryParams } from "../networkApi";
import type { EnrichedGraphNetworkOut } from "../types";

interface UseNetworkDataReturn {
  data: EnrichedGraphNetworkOut | null;
  loading: boolean;
  error: string | null;
  load: (params?: NetworkQueryParams) => Promise<void>;
  lastParams: NetworkQueryParams;
}

export function useNetworkData(initialParams: NetworkQueryParams = {}): UseNetworkDataReturn {
  const [data, setData] = useState<EnrichedGraphNetworkOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastParams, setLastParams] = useState<NetworkQueryParams>(initialParams);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async (params: NetworkQueryParams = lastParams) => {
    // Cancel previous in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);
    setLastParams(params);

    try {
      const result = await fetchNetworkGraph(params);
      setData(result);
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        setError(err?.message ?? "Failed to load network graph");
      }
    } finally {
      setLoading(false);
    }
  }, [lastParams]);

  return { data, loading, error, load, lastParams };
}
