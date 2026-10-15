"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/AuthContext";
import { ShieldAlert, Eye, EyeOff, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@graphguard.ai");
  const [password, setPassword] = useState("admin1234");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push("/dashboard");
    }
  }, [user, router]);

  const setDemoCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const formData = new URLSearchParams();
      formData.append("username", email.trim());
      formData.append("password", password);

      const rawUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const baseUrl = rawUrl.replace(/\/api\/v1\/?$/, "");

      const res = await fetch(`${baseUrl}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || "Invalid email or password");
      }

      const data = await res.json();
      
      // Fetch user profile
      const userRes = await fetch(`${baseUrl}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.access_token}`
        }
      });
      
      if (!userRes.ok) {
         throw new Error("Failed to load user profile");
      }
      
      const userData = await userRes.json();
      login(data.access_token, userData);

    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#05060f] flex items-center justify-center p-4">
      <div className="w-full max-w-md p-8 rounded-3xl bg-[#0a0b16] border border-[rgba(186,215,247,0.12)] shadow-2xl relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute -top-32 -left-32 w-64 h-64 bg-[#663af3] rounded-full blur-[120px] opacity-20 pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-64 h-64 bg-[#027dea] rounded-full blur-[120px] opacity-20 pointer-events-none" />
        
        <div className="relative z-10 flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-full bg-[#663af3] flex items-center justify-center shadow-[0_0_24px_rgba(102,58,243,0.5)] border border-[rgba(186,215,247,0.2)] mb-4">
            <ShieldAlert className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-display font-medium text-white tracking-tight">GRAPHGUARD</h1>
          <p className="text-[#9da7ba] text-sm mt-1">Sign in to your account</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="relative z-10 space-y-5">
          <div>
            <label className="block text-xs font-eyebrow text-[#9da7ba] mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-[rgba(186,214,247,0.04)] border border-[rgba(186,215,247,0.12)] rounded-xl px-4 py-3 text-[#d1e4fa] focus:outline-none focus:border-[#663af3] focus:ring-1 focus:ring-[#663af3] transition-all"
              placeholder="admin@graphguard.ai"
            />
          </div>

          <div>
            <label className="block text-xs font-eyebrow text-[#9da7ba] mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-[rgba(186,214,247,0.04)] border border-[rgba(186,215,247,0.12)] rounded-xl px-4 py-3 text-[#d1e4fa] focus:outline-none focus:border-[#663af3] focus:ring-1 focus:ring-[#663af3] transition-all pr-12"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[#9da7ba] hover:text-[#d1e4fa] transition-colors"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 bg-gradient-to-tr from-[#663af3] to-[#027dea] hover:from-[#7c54f5] hover:to-[#178bef] text-white font-medium rounded-xl px-4 py-3 shadow-[0_0_20px_rgba(102,58,243,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* 1-Click Demo Accounts */}
        <div className="relative z-10 mt-6 pt-5 border-t border-[rgba(186,215,247,0.1)]">
          <p className="text-[11px] font-eyebrow text-[#9da7ba] uppercase tracking-wider text-center mb-3">
            Quick Fill Demo Roles
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setDemoCredentials("admin@graphguard.ai", "admin1234")}
              className="py-1.5 px-2 rounded-lg bg-[rgba(102,58,243,0.12)] border border-[rgba(102,58,243,0.3)] text-[11px] text-[#c7d3ea] hover:bg-[rgba(102,58,243,0.25)] hover:text-white transition-all text-center cursor-pointer"
            >
              👑 Admin
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials("investigator@graphguard.ai", "investigator123")}
              className="py-1.5 px-2 rounded-lg bg-[rgba(2,125,234,0.12)] border border-[rgba(2,125,234,0.3)] text-[11px] text-[#c7d3ea] hover:bg-[rgba(2,125,234,0.25)] hover:text-white transition-all text-center cursor-pointer"
            >
              🔍 Investigator
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials("analyst@graphguard.ai", "analyst123")}
              className="py-1.5 px-2 rounded-lg bg-[rgba(16,185,129,0.12)] border border-[rgba(16,185,129,0.3)] text-[11px] text-[#c7d3ea] hover:bg-[rgba(16,185,129,0.25)] hover:text-white transition-all text-center cursor-pointer"
            >
              📊 Analyst
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
