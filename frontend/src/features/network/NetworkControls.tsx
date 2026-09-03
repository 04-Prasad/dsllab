"use client";

import React from "react";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2 } from "lucide-react";

interface NetworkControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onFullscreen: () => void;
}

export default function NetworkControls({
  onZoomIn,
  onZoomOut,
  onReset,
  onFullscreen,
}: NetworkControlsProps) {
  return (
    <div className="flex items-center gap-1.5">
      <button
        onClick={onZoomIn}
        title="Zoom In"
        className="w-8 h-8 flex items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] border border-[#1e293b] rounded-lg text-[#94a3b8] hover:text-[#38bdf8] transition-colors cursor-pointer"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        onClick={onZoomOut}
        title="Zoom Out"
        className="w-8 h-8 flex items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] border border-[#1e293b] rounded-lg text-[#94a3b8] hover:text-[#38bdf8] transition-colors cursor-pointer"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <button
        onClick={onReset}
        title="Reset View"
        className="w-8 h-8 flex items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] border border-[#1e293b] rounded-lg text-[#94a3b8] hover:text-white transition-colors cursor-pointer"
      >
        <RotateCcw className="w-4 h-4" />
      </button>
      <button
        onClick={onFullscreen}
        title="Fullscreen"
        className="w-8 h-8 flex items-center justify-center bg-[#0f172a] hover:bg-[#1e293b] border border-[#1e293b] rounded-lg text-[#94a3b8] hover:text-white transition-colors cursor-pointer"
      >
        <Maximize2 className="w-4 h-4" />
      </button>
    </div>
  );
}
