"use client";

import React from "react";
import {
  ShieldAlert, LayoutDashboard, Users, GitMerge, FileText, Search,
  Lock, Cpu, Activity, LogOut, FileSearch, Bot, CheckCircle2, ListTree, Globe
} from "lucide-react";

interface AppShellProps {
  currentView: string;
  onNavigate: (view: string) => void;
  userEmail: string;
  onLogout: () => void;
  onOpenCopilot: () => void;
  onOpenReportModal?: () => void;
  onOpenIngestionModal?: () => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentView,
  onNavigate,
  userEmail,
  onLogout,
  onOpenCopilot,
  onOpenReportModal,
  onOpenIngestionModal,
  children
}) => {
  const navSections = [
    {
      category: "Threat Operations",
      items: [
        { id: "command_center", label: "Command Center", icon: LayoutDashboard },
        { id: "cases", label: "Investigations", icon: FileSearch },
        { id: "actors", label: "Actor Explorer", icon: Users },
      ],
    },
    {
      category: "Analytics & Intelligence",
      items: [
        { id: "attribution_lab", label: "Attribution Lab", icon: GitMerge },
        { id: "graph_explorer", label: "Intelligence Graph", icon: ListTree },
      ],
    },
    {
      category: "Forensic Ledger",
      items: [
        { id: "evidence_vault", label: "Evidence Vault", icon: FileText },
        { id: "audit_log", label: "Audit Chain", icon: Lock },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-netra-bg text-netra-text flex flex-col font-sans">
      {/* Top Header Bar */}
      <header className="h-[68px] border-b border-netra-border bg-netra-surface/90 backdrop-blur-md px-5 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <img
            src="/netra-x-mark.png"
            alt=""
            aria-hidden="true"
            width={52}
            height={52}
            className="w-12 h-12 object-contain select-none"
            draggable={false}
          />
          <div className="flex items-center space-x-2">
            <span
              className="glitch-img align-middle"
              style={{ ["--glitch-src" as string]: "url(/netra-x-wordmark.png)" } as React.CSSProperties}
            >
              <img
                src="/netra-x-wordmark.png"
                alt="NETRA-X"
                height={24}
                className="h-[24px] w-auto block select-none"
                draggable={false}
              />
            </span>
            <span className="text-[10px] text-netra-cyan font-mono bg-netra-cyan/10 px-2 py-0.5 rounded border border-netra-cyan/30">
              v0.1 MVP
            </span>
          </div>
        </div>

        {/* Top Header Action Buttons */}
        <div className="flex items-center space-x-3">
          {/* Status Indicator */}
          <div className="hidden sm:flex items-center space-x-2 text-[11px] font-mono text-netra-valid bg-netra-valid/10 px-2.5 py-1 rounded-full border border-netra-valid/30">
            <Activity className="w-3.5 h-3.5 animate-pulse text-netra-valid" />
            <span>LEDGER: ONLINE</span>
          </div>

          {/* Quick Action: Ingest Payload */}
          {onOpenIngestionModal && (
            <button
              onClick={onOpenIngestionModal}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-netra-cyan text-netra-bg font-bold text-xs hover:bg-netra-cyan/90 transition shadow-lg"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>+ Crawl .onion</span>
            </button>
          )}

          {/* Quick Action: Export Report */}
          {onOpenReportModal && (
            <button
              onClick={onOpenReportModal}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-netra-purple/20 border border-netra-purple/40 text-netra-purple hover:text-white text-xs font-semibold hover:bg-netra-purple/30 transition"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Export Report</span>
            </button>
          )}

          {/* AI Copilot Drawer Trigger */}
          <button
            onClick={onOpenCopilot}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-netra-surface border border-netra-border text-white text-xs font-medium hover:border-netra-cyan/60 hover:text-netra-cyan transition"
          >
            <Bot className="w-3.5 h-3.5 text-netra-cyan" />
            <span>AI Copilot</span>
          </button>

          {/* Command Palette Trigger */}
          <button
            onClick={() =>
              window.dispatchEvent(
                new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true })
              )
            }
            title="Command palette"
            aria-label="Open command palette"
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 border border-netra-border bg-netra-surface text-netra-subtle hover:text-netra-text hover:border-netra-cyan/40 transition-colors font-mono text-[10px] rounded-lg"
          >
            <Search className="w-3 h-3" />
            <span>CTRL+K</span>
          </button>

          {/* User Profile & Logout */}
          <div className="text-xs text-netra-muted border-l border-netra-border pl-3 flex items-center space-x-2">
            <span className="font-mono text-white text-[11px]">{userEmail}</span>
            <button
              onClick={onLogout}
              className="p-1 text-netra-subtle hover:text-netra-hazard transition rounded"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Body Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Organized Sidebar Navigation */}
        <aside className="w-56 border-r border-netra-border bg-netra-surface/80 p-3 flex flex-col justify-between shrink-0 font-sans">
          <nav className="space-y-4">
            {navSections.map((sec, idx) => (
              <div key={idx} className="space-y-1">
                <div className="px-3 py-1 text-[10px] font-mono text-netra-subtle tracking-widest uppercase font-bold">
                  {sec.category}
                </div>
                {sec.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentView === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onNavigate(item.id)}
                      className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                        isActive
                          ? "bg-netra-cyan/15 text-white border border-netra-cyan/40 font-semibold shadow-sm"
                          : "text-netra-muted hover:bg-netra-surface hover:text-white"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? "text-netra-cyan" : "text-netra-subtle"}`} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>

          {/* Footer Ledger Notice */}
          <div className="bg-netra-card border border-netra-border p-3 rounded-xl text-[11px] space-y-1">
            <div className="text-netra-valid font-semibold flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-netra-valid" />
              <span>Evidence Ledger</span>
            </div>
            <p className="text-netra-muted text-[10px] leading-relaxed">
              Append-only SHA-256 audit log. AI assists; analyst decides.
            </p>
          </div>
        </aside>

        {/* Main View Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-netra-bg">
          {children}
        </main>
      </div>
    </div>
  );
};
