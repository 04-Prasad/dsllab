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
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[rgba(186,215,247,0.12)]">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-eyebrow text-[#9da7ba] mb-1">
            <span>Rule Engine</span>
            <span>•</span>
            <span>Deterministic EWS Signals</span>
          </div>
          <h1 className="text-3xl font-display font-medium text-skywash tracking-tight">Early Warning Signals (EWS)</h1>
          <p className="text-sm text-[#9da7ba] mt-1">Deterministic rule triggers based on transaction velocity, fan-in/fan-out, and graph topology.</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 flex flex-wrap items-center gap-2 text-xs">
        <Filter className="w-4 h-4 text-[#9da7ba] mr-2" />
        {ewsCodes.map((item) => (
          <button
            key={item.code}
            onClick={() => setSignalCode(item.code)}
            className={`px-3.5 py-1 rounded-full font-semibold border transition-all ${
              signalCode === item.code
                ? "bg-[#663af3] text-white border-[#663af3] shadow-[0_0_12px_rgba(102,58,243,0.4)]"
                : "bg-[rgba(186,214,247,0.03)] text-[#c7d3ea] border-[rgba(186,215,247,0.12)] hover:bg-[rgba(186,214,247,0.08)]"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Signals Grid */}
      {loading ? (
        <div className="p-12 text-center text-[#9da7ba] font-mono text-sm animate-pulse">Loading EWS Signals...</div>
      ) : signals.length === 0 ? (
        <div className="p-12 text-center text-[#9da7ba] text-sm">No signals match current filter.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {signals.map((sig) => (
            <div key={sig.id} className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-amber-300">{sig.signal_code}</span>
                <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold border ${
                  sig.severity === "CRITICAL" ? "bg-red-950/60 text-red-400 border-red-800/60" : "bg-amber-950/60 text-amber-400 border-amber-800/60"
                }`}>
                  {sig.severity}
                </span>
              </div>

              <div>
                <div className="text-xs font-bold text-[#d8ecf8] flex items-center justify-between">
                  <span>{sig.signal_type}</span>
                  <Link href={`/accounts/${sig.account_id}`} className="font-mono text-[#663af3] hover:text-[#b6d9fc] hover:underline">
                    {sig.account_id}
                  </Link>
                </div>
                <p className="text-xs text-[#9da7ba] mt-1.5 leading-relaxed">{sig.description}</p>
              </div>

              <div className="pt-2.5 border-t border-[rgba(186,215,247,0.12)] flex items-center justify-between text-[11px] font-mono text-[#9da7ba]">
                <span>Observed: <strong className="text-white">{sig.observed_value}</strong></span>
                <span>Threshold: <strong className="text-[#c7d3ea]">{sig.threshold_value}</strong></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
