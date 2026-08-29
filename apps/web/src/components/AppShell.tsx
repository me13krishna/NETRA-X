"use client";

import React, { useState } from "react";
import {
  ShieldAlert, LayoutDashboard, Users, GitMerge, FileText, Search,
  Lock, Cpu, Activity, LogOut, FileSearch, Bot, CheckCircle2, ListTree
} from "lucide-react";

interface AppShellProps {
  currentView: string;
  onNavigate: (view: string) => void;
  userEmail: string;
  onLogout: () => void;
  onOpenCopilot: () => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentView,
  onNavigate,
  userEmail,
  onLogout,
  onOpenCopilot,
  children
}) => {
  const navItems = [
    { id: "command_center", label: "Command Center", icon: LayoutDashboard },
    { id: "cases", label: "Investigations", icon: FileSearch },
    { id: "actors", label: "Actor Explorer", icon: Users },
    { id: "attribution_lab", label: "Attribution Lab", icon: GitMerge },
    { id: "graph_explorer", label: "Intelligence Graph", icon: ListTree },
    { id: "evidence_vault", label: "Evidence Vault", icon: FileText },
    { id: "audit_log", label: "Audit Chain", icon: Lock },
  ];

  return (
    <div className="min-h-screen bg-netra-bg text-netra-text flex flex-col font-sans">
      {/* Top Bar */}
      <header className="h-14 border-b border-netra-border bg-netra-surface px-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-netra-purple flex items-center justify-center font-bold text-white shadow-lg">
            N
          </div>
          <div>
            <span className="font-bold tracking-wider text-base text-white">NETRA-X</span>
            <span className="ml-2 text-xs text-netra-cyan font-mono bg-netra-cyan/10 px-2 py-0.5 rounded border border-netra-cyan/30">
              v0.1 MVP
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs font-mono text-netra-valid bg-netra-valid/10 px-2.5 py-1 rounded border border-netra-valid/30">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span>LEDGER: ONLINE (PROVENANCE VERIFIED)</span>
          </div>

          <button
            onClick={onOpenCopilot}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-netra-purple/20 border border-netra-purple/50 text-netra-purple text-xs font-medium hover:bg-netra-purple/30 transition"
          >
            <Bot className="w-4 h-4" />
            <span>AI Copilot</span>
          </button>

          <div className="text-xs text-netra-muted border-l border-netra-border pl-3 flex items-center space-x-2">
            <span className="font-mono">{userEmail}</span>
            <button
              onClick={onLogout}
              className="text-netra-subtle hover:text-netra-red transition ml-2"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-60 border-r border-netra-border bg-netra-card p-3 flex flex-col justify-between shrink-0">
          <nav className="space-y-1">
            <div className="px-3 py-2 text-[10px] font-mono text-netra-subtle tracking-widest uppercase">
              Core Modules
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                    isActive
                      ? "bg-netra-purple/20 text-white border border-netra-purple/50 purple-glow"
                      : "text-netra-muted hover:bg-netra-hover hover:text-white"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-netra-purple" : "text-netra-subtle"}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="bg-netra-surface border border-netra-border p-3 rounded-lg text-[11px] space-y-1">
            <div className="text-netra-cyan font-semibold flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Evidence Ledger</span>
            </div>
            <p className="text-netra-subtle text-[10px] leading-tight">
              Append-only SHA-256 audit log. AI assists; analyst decides.
            </p>
          </div>
        </aside>

        {/* Main Workspace Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-netra-bg">
          {children}
        </main>
      </div>
    </div>
  );
};
