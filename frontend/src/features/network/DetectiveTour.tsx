"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Play, ChevronRight, ChevronLeft, X, Compass } from "lucide-react";
import { DETECTIVE_TOUR_STOPS, type TourStop } from "./types";

interface DetectiveTourProps {
  onFocusAccount: (id: string) => void;
  onClose: () => void;
}

export default function DetectiveTour({ onFocusAccount, onClose }: DetectiveTourProps) {
  const [active, setActive] = useState(false);
  const [stopIndex, setStopIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  const currentStop: TourStop | null = active ? DETECTIVE_TOUR_STOPS[stopIndex] : null;

  const startTour = useCallback(() => {
    setActive(true);
    setStopIndex(0);
    setProgress(0);
  }, []);

  // When stop changes, focus camera and start progress timer
  useEffect(() => {
    if (!active || !currentStop) return;
    onFocusAccount(currentStop.targetAccount);

    setProgress(0);
    const DURATION = 6000; // 6 s per stop
    const TICK = 100;
    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed += TICK;
      setProgress(Math.min(100, (elapsed / DURATION) * 100));
      if (elapsed >= DURATION) {
        clearInterval(interval);
        if (stopIndex < DETECTIVE_TOUR_STOPS.length - 1) {
          setStopIndex((i) => i + 1);
        }
      }
    }, TICK);

    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, stopIndex]);

  const goNext = () => {
    if (stopIndex < DETECTIVE_TOUR_STOPS.length - 1) setStopIndex((i) => i + 1);
    else { setActive(false); setStopIndex(0); }
  };
  const goPrev = () => {
    if (stopIndex > 0) setStopIndex((i) => i - 1);
  };
  const closeTour = () => {
    setActive(false);
    setStopIndex(0);
    onClose();
  };

  // Inactive trigger button
  if (!active) {
    return (
      <button
        onClick={startTour}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 border border-amber-700/50 text-amber-300 rounded-lg text-xs font-semibold transition-colors"
      >
        <Compass className="w-4 h-4" />
        Detective Tour
      </button>
    );
  }

  // Active tour overlay
  return (
    <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-50 w-[28rem] max-w-[90vw]">
      <div className="bg-[#0d111e] border border-amber-700/60 rounded-2xl shadow-2xl shadow-amber-900/20 overflow-hidden">
        {/* Progress bar */}
        <div className="h-0.5 bg-gray-800">
          <div
            className="h-full bg-amber-500 transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Play className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              <span className="text-[11px] text-amber-400 font-mono font-bold uppercase tracking-wider">
                Stop {stopIndex + 1} / {DETECTIVE_TOUR_STOPS.length}
              </span>
            </div>
            <button onClick={closeTour} className="text-gray-500 hover:text-white transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content */}
          <h3 className="text-white font-bold text-sm mb-1">{currentStop?.title}</h3>
          <p className="text-gray-400 text-xs leading-relaxed">{currentStop?.body}</p>

          {/* EWS highlight badges */}
          {currentStop?.highlightEws && currentStop.highlightEws.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {currentStop.highlightEws.map((code) => (
                <span
                  key={code}
                  className="px-2 py-0.5 bg-amber-950/60 border border-amber-700/60 rounded text-amber-300 text-[10px] font-mono font-bold"
                >
                  ⚠ {code}
                </span>
              ))}
            </div>
          )}

          {/* Stop dots + nav */}
          <div className="flex items-center justify-between mt-4">
            <div className="flex gap-1">
              {DETECTIVE_TOUR_STOPS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setStopIndex(i)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    i === stopIndex ? "bg-amber-400" : "bg-gray-700 hover:bg-gray-600"
                  }`}
                />
              ))}
            </div>
            <div className="flex gap-1.5">
              <button
                onClick={goPrev}
                disabled={stopIndex === 0}
                className="flex items-center gap-0.5 px-2.5 py-1 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-300 text-xs font-medium transition-colors disabled:opacity-40"
              >
                <ChevronLeft className="w-3 h-3" /> Prev
              </button>
              <button
                onClick={goNext}
                className="flex items-center gap-0.5 px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                {stopIndex < DETECTIVE_TOUR_STOPS.length - 1 ? (
                  <>Next <ChevronRight className="w-3 h-3" /></>
                ) : (
                  "Finish"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
