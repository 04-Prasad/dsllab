import "./globals.css";
import React from "react";
import Link from "next/link";
import { 
  ShieldAlert, 
  LayoutDashboard, 
  Users, 
  AlertTriangle, 
  Network, 
  Zap, 
  Search,
  Activity
} from "lucide-react";

export const metadata = {
  title: "GraphGuard — Graph Fraud Detection System",
  description: "Intelligent Transaction Monitoring & Graph-based Fraud Analytics Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0B0F19] text-gray-100 min-h-screen flex flex-col">
        {/* Top Header */}
        <header className="h-16 border-b border-gray-800 bg-[#111827]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
                GRAPHGUARD
              </span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800 font-mono">
                PROTOTYPE v1.0
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono text-emerald-400">
              <Activity className="w-4 h-4 animate-pulse" />
              <span>SYSTEM ONLINE</span>
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold text-xs text-white shadow-md">
              INV
            </div>
          </div>
        </header>

        <div className="flex flex-1">
          {/* Left Sidebar */}
          <aside className="w-64 border-r border-gray-800 bg-[#0F1423] p-4 flex flex-col justify-between hidden md:flex">
            <nav className="space-y-1">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Monitoring
              </div>
              
              <Link
                href="/dashboard"
                className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors group"
              >
                <LayoutDashboard className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
                <span>Overview</span>
              </Link>

              <Link
                href="/accounts"
                className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors group"
              >
                <Users className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
                <span>Accounts</span>
              </Link>

              <Link
                href="/alerts"
                className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors group"
              >
                <AlertTriangle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
                <span>Alert Queue</span>
              </Link>

              <Link
                href="/ews"
                className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors group"
              >
                <Zap className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
                <span>Early Warnings</span>
              </Link>

              <div className="pt-4 px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Analytics
              </div>

              <Link
                href="/graph"
                className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors group"
              >
                <Network className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                <span>Graph Explorer</span>
              </Link>
            </nav>

            <div className="p-3 bg-indigo-950/40 border border-indigo-900/60 rounded-xl space-y-2 text-xs">
              <div className="font-semibold text-indigo-300">Demo Mule Target</div>
              <div className="text-gray-400">Account <span className="font-mono text-amber-400">A102</span> seeded with 35 fan-in senders & rapid movement.</div>
              <Link
                href="/accounts/A102"
                className="inline-block mt-1 text-indigo-400 hover:text-indigo-300 font-medium underline"
              >
                Investigate A102 →
              </Link>
            </div>
          </aside>

          {/* Main Content Viewport */}
          <main className="flex-1 p-6 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
