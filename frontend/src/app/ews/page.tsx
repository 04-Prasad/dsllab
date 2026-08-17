"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Zap, ExternalLink, Filter } from "lucide-react";

export default function EWSPage() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [signalCode, setSignalCode] = useState<string>("");

  const loadSignals = async () => {
    try {
      setLoading(true);
      const data = await api.getEWSSignals({ signal_code: signalCode || undefined, limit: 60 });
      setSignals(data);
    } catch (err) {
      console.error("Failed to load EWS signals", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignals();
  }, [signalCode]);

  const ewsCodes = [
    { code: "", label: "ALL SIGNALS" },
    { code: "EWS-001", label: "EWS-001 (Velocity Spike)" },
    { code: "EWS-002", label: "EWS-002 (Fan-In Mule)" },
    { code: "EWS-003", label: "EWS-003 (Fan-Out)" },
    { code: "EWS-004", label: "EWS-004 (Dormancy Burst)" },
    { code: "EWS-005", label: "EWS-005 (Rapid Movement)" },
    { code: "EWS-006", label: "EWS-006 (Risky Neighbor)" },
    { code: "EWS-007", label: "EWS-007 (Circular Flow)" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Early Warning Signals (EWS)</h1>
          <p className="text-sm text-gray-400">Deterministic rule triggers based on transaction velocity, fan-in/fan-out, and graph topology.</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 bg-[#111827] border border-gray-800 rounded-xl flex flex-wrap items-center gap-2 text-xs">
        <Filter className="w-4 h-4 text-gray-400 mr-2" />
        {ewsCodes.map((item) => (
          <button
            key={item.code}
            onClick={() => setSignalCode(item.code)}
            className={`px-3 py-1 rounded-lg font-semibold transition-colors ${
              signalCode === item.code ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Signals Grid */}
      {loading ? (
        <div className="p-12 text-center text-gray-400 font-mono text-sm">Loading EWS Signals...</div>
      ) : signals.length === 0 ? (
        <div className="p-12 text-center text-gray-400 text-sm">No signals match current filter.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {signals.map((sig) => (
            <div key={sig.id} className="p-4 bg-[#111827] border border-gray-800 rounded-xl space-y-3 hover:border-gray-700 transition-colors">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-amber-400">{sig.signal_code}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  sig.severity === "CRITICAL" ? "bg-red-950 text-red-400" : "bg-amber-950 text-amber-400"
                }`}>
                  {sig.severity}
                </span>
              </div>

              <div>
                <div className="text-xs font-bold text-white flex items-center justify-between">
                  <span>{sig.signal_type}</span>
                  <Link href={`/accounts/${sig.account_id}`} className="font-mono text-indigo-400 hover:underline">
                    {sig.account_id}
                  </Link>
                </div>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">{sig.description}</p>
              </div>

              <div className="pt-2 border-t border-gray-800 flex items-center justify-between text-[11px] font-mono text-gray-400">
                <span>Observed: <strong className="text-white">{sig.observed_value}</strong></span>
                <span>Threshold: <strong className="text-gray-400">{sig.threshold_value}</strong></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
