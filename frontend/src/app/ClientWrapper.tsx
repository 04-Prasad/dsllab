"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/AuthContext";
import Link from "next/link";
import { 
  ShieldAlert, 
  LayoutDashboard, 
  Users, 
  AlertTriangle, 
  Network, 
  Zap,
  Activity,
  LogOut
} from "lucide-react";

function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05060f] flex items-center justify-center">
         <div className="w-8 h-8 border-2 border-[#663af3]/30 border-t-[#663af3] rounded-full animate-spin" />
      </div>
    );
  }

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!user) {
    return null;
  }

  return (
    <>
      {/* Top Header */}
      <header className="h-16 border-b border-[rgba(186,215,247,0.12)] bg-[#05060f]/80 backdrop-blur-xl px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-full bg-[#663af3] flex items-center justify-center shadow-[0_0_16px_rgba(102,58,243,0.5)] border border-[rgba(186,215,247,0.2)]">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xl font-display font-medium tracking-tight text-skywash">
              GRAPHGUARD
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-[rgba(199,211,234,0.12)] text-[#c7d3ea] border border-[rgba(186,215,247,0.12)]">
              PROTOTYPE v1.0
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-[rgba(186,214,247,0.06)] border border-[rgba(186,215,247,0.12)] text-xs font-mono text-[#d1e4fa]">
            <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="font-eyebrow text-[11px] text-[#c7d3ea] uppercase">{user.role}</span>
          </div>
          <div className="flex items-center space-x-3">
             <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#663af3] to-[#027dea] flex items-center justify-center font-bold text-xs text-white shadow-[0_0_12px_rgba(102,58,243,0.4)] border border-[rgba(186,215,247,0.2)]">
               {user.full_name.charAt(0).toUpperCase()}
             </div>
             <button onClick={logout} className="text-[#9da7ba] hover:text-white transition-colors" title="Sign out">
                <LogOut className="w-4 h-4" />
             </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 relative z-10">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-[rgba(186,215,247,0.12)] bg-[#05060f]/80 backdrop-blur-xl p-4 flex flex-col justify-between hidden md:flex">
          <nav className="space-y-1.5">
            <div className="px-3 py-2 text-[11px] font-eyebrow text-[#9da7ba]">
              Monitoring
            </div>
            
            <Link
              href="/dashboard"
              className="flex items-center space-x-3 px-3.5 py-2.5 rounded-full text-sm font-medium text-[#c7d3ea] hover:text-[#ffffff] hover:bg-[rgba(186,214,247,0.08)] border border-transparent hover:border-[rgba(186,215,247,0.12)] transition-all group"
            >
              <LayoutDashboard className="w-4 h-4 text-[#b6d9fc] group-hover:scale-110 transition-transform" />
              <span>Overview</span>
            </Link>

            <Link
              href="/accounts"
              className="flex items-center space-x-3 px-3.5 py-2.5 rounded-full text-sm font-medium text-[#c7d3ea] hover:text-[#ffffff] hover:bg-[rgba(186,214,247,0.08)] border border-transparent hover:border-[rgba(186,215,247,0.12)] transition-all group"
            >
              <Users className="w-4 h-4 text-[#b6d9fc] group-hover:scale-110 transition-transform" />
              <span>Accounts</span>
            </Link>

            <Link
              href="/alerts"
              className="flex items-center space-x-3 px-3.5 py-2.5 rounded-full text-sm font-medium text-[#c7d3ea] hover:text-[#ffffff] hover:bg-[rgba(186,214,247,0.08)] border border-transparent hover:border-[rgba(186,215,247,0.12)] transition-all group"
            >
              <AlertTriangle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
              <span>Alert Queue</span>
            </Link>

            <Link
              href="/ews"
              className="flex items-center space-x-3 px-3.5 py-2.5 rounded-full text-sm font-medium text-[#c7d3ea] hover:text-[#ffffff] hover:bg-[rgba(186,214,247,0.08)] border border-transparent hover:border-[rgba(186,215,247,0.12)] transition-all group"
            >
              <Zap className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
              <span>Early Warnings</span>
            </Link>

            <div className="pt-5 px-3 py-2 text-[11px] font-eyebrow text-[#9da7ba]">
              Analytics
            </div>

            <Link
              href="/graph"
              className="flex items-center space-x-3 px-3.5 py-2.5 rounded-full text-sm font-medium text-[#c7d3ea] hover:text-[#ffffff] hover:bg-[rgba(186,214,247,0.08)] border border-transparent hover:border-[rgba(186,215,247,0.12)] transition-all group"
            >
              <Network className="w-4 h-4 text-[#b6d9fc] group-hover:scale-110 transition-transform" />
              <span>Graph Explorer</span>
            </Link>
          </nav>

          <div className="p-4 glass-card rounded-2xl space-y-2 text-xs border border-[rgba(186,215,247,0.12)] bg-[rgba(102,58,243,0.04)]">
            <div className="font-semibold text-[#d8ecf8]">Demo Mule Target</div>
            <div className="text-[#9da7ba]">Account <span className="font-mono text-amber-300">A102</span> seeded with 35 fan-in senders & rapid movement.</div>
            <Link
              href="/accounts/A102"
              className="inline-flex items-center text-[#663af3] hover:text-[#b6d9fc] font-medium pt-1 transition-colors"
            >
              Investigate A102 →
            </Link>
          </div>
        </aside>

        {/* Main Content Viewport */}
        <main className="flex-1 p-6 overflow-y-auto max-w-[1400px]">
          {children}
        </main>
      </div>
    </>
  );
}

export default function ClientWrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <MainLayout>{children}</MainLayout>
    </AuthProvider>
  );
}
