"use client";

import React, { Suspense } from "react";
import NetworkPage from "@/features/network/NetworkPage";

export default function GraphPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <div className="w-10 h-10 border-4 border-[#38bdf8] border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 font-mono text-sm animate-pulse">
            Loading 3D Investigation Network...
          </p>
        </div>
      }
    >
      <NetworkPage />
    </Suspense>
  );
}
