"use client";

import React, { useState } from "react";
import { Lock, Mail, ShieldAlert, ArrowRight } from "lucide-react";
import { apiFetch, setAuthToken } from "../lib/api";

interface LoginScreenProps {
  onLoginSuccess: (user: any) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("analyst@netra-x.local");
  const [password, setPassword] = useState("AnalystPass2026!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch<any>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(res.access_token);
      onLoginSuccess(res.user);
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-netra-bg flex items-center justify-center p-4 font-sans relative overflow-hidden">
      {/* Dynamic Background Glow Elements */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-netra-purple/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-netra-cyan/10 rounded-full blur-3xl" />

      <div className="w-full max-w-md bg-netra-card border border-netra-border rounded-2xl p-8 shadow-2xl glass-panel relative z-10 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-netra-purple flex items-center justify-center font-bold text-xl text-white shadow-xl mx-auto">
            N
          </div>
          <h1 className="text-2xl font-bold text-white tracking-wider">NETRA-X</h1>
          <p className="text-xs text-netra-muted">
            Dark Web Threat Actor Intelligence & Attribution Operating System
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-netra-red/10 border border-netra-red/40 text-netra-red text-xs text-center font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1">
            <label className="text-netra-subtle font-medium block">Analyst Email Identifier:</label>
            <div className="flex items-center space-x-2 bg-netra-surface border border-netra-border rounded-lg p-2.5">
              <Mail className="w-4 h-4 text-netra-subtle" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-transparent text-white placeholder-netra-subtle focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-netra-subtle font-medium block">Passphrase:</label>
            <div className="flex items-center space-x-2 bg-netra-surface border border-netra-border rounded-lg p-2.5">
              <Lock className="w-4 h-4 text-netra-subtle" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-transparent text-white placeholder-netra-subtle focus:outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-netra-purple hover:bg-netra-deepViolet text-white font-bold text-xs flex items-center justify-center space-x-2 shadow-lg transition hover:opacity-90 disabled:opacity-50"
          >
            <span>{loading ? "Authenticating..." : "Authorize Access"}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="pt-4 border-t border-netra-border text-center space-y-1">
          <div className="text-[11px] text-netra-subtle font-mono">DEFAULT DEMO CREDENTIALS:</div>
          <div className="text-xs text-netra-cyan font-mono">analyst@netra-x.local / AnalystPass2026!</div>
        </div>
      </div>
    </div>
  );
};
