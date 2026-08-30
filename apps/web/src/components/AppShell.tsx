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
      <header className="h-[72px] border-b border-netra-border bg-netra-surface px-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          {/* The mark is served pre-trimmed and squared at 128px, so it fills
              this slot without a solid backing plate behind it -- the artwork
              carries its own silhouette against the dark ground. */}
          <img
            src="/netra-x-mark.png"
            // Decorative: the wordmark beside it already carries the name, so
            // announcing it twice is noise for a screen reader.
            alt=""
            aria-hidden="true"
            width={64}
            height={64}
            className="w-16 h-16 object-contain select-none"
            draggable={false}
          />
          <div>
            {/* Wordmark replaces the typeset name. Exported at 4x its display
                height so it stays crisp on retina; width is left to auto so the
                artwork's own aspect ratio drives it. */}
            <span
              className="glitch-img align-middle"
              style={{ ["--glitch-src" as string]: "url(/netra-x-wordmark.png)" } as React.CSSProperties}
            >
              <img
                src="/netra-x-wordmark.png"
                alt="NETRA-X"
                height={26}
                className="h-[26px] w-auto block select-none"
                draggable={false}
              />
            </span>
            <span className="ml-2 text-xs text-netra-cyan font-mono bg-netra-cyan/10 px-2 py-0.5 rounded border border-netra-cyan/30">
              v0.1 MVP
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs font-mono text-netra-valid bg-netra-valid/10 px-2.5 py-1 rounded border border-netra-valid/30">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span><span className="live-dot">&#9679;</span> LEDGER: ONLINE (PROVENANCE VERIFIED)</span>
          </div>

          <button
            onClick={onOpenCopilot}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-netra-purple/20 border border-netra-purple/50 text-netra-purple text-xs font-medium hover:bg-netra-purple/30 transition"
          >
            <Bot className="w-4 h-4" />
            <span>AI Copilot</span>
          </button>

          {/* A command palette nobody knows about is dead weight, so the
              shortcut is advertised. Clicking dispatches the same keystroke the
              palette listens for, rather than lifting its open state up here
              just to satisfy one button. */}
          <button
            onClick={() =>
              window.dispatchEvent(
                new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true })
              )
            }
            title="Command palette"
            aria-label="Open command palette"
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 border border-netra-border bg-netra-surface text-netra-subtle hover:text-netra-text hover:border-netra-purple/50 transition-colors font-mono text-[10px]"
          >
            <Search className="w-3 h-3" />
            <span className="tracking-telemetry">CTRL</span>
            <span className="opacity-60">+</span>
            <span className="tracking-telemetry">K</span>
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
