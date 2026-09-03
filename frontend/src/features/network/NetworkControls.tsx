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
        className="w-8 h-8 flex items-center justify-center bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        onClick={onZoomOut}
        title="Zoom Out"
        className="w-8 h-8 flex items-center justify-center bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <button
        onClick={onReset}
        title="Reset View"
        className="w-8 h-8 flex items-center justify-center bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
      >
        <RotateCcw className="w-4 h-4" />
      </button>
      <button
        onClick={onFullscreen}
        title="Fullscreen"
        className="w-8 h-8 flex items-center justify-center bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors"
      >
        <Maximize2 className="w-4 h-4" />
      </button>
    </div>
  );
}
