"use client";

import React, { useEffect, useState } from "react";
import { apiFetch, getAuthToken, setAuthToken } from "../lib/api";
import { LoginScreen } from "../components/LoginScreen";
import { AppShell } from "../components/AppShell";
import { CommandCenter } from "../components/CommandCenter";
import { ActorProfile } from "../components/ActorProfile";
import { AttributionLab } from "../components/AttributionLab";
import { GraphExplorer } from "../components/GraphExplorer";
import { EvidenceVault } from "../components/EvidenceVault";
import { AuditLogViewer } from "../components/AuditLogViewer";
import { CasesView } from "../components/CasesView";
import { CopilotDrawer } from "../components/CopilotDrawer";
import { CommandPalette } from "../components/CommandPalette";
import { ToastProvider } from "../components/StatusToasts";

export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [currentView, setCurrentView] = useState("command_center");
  const [selectedTargetId, setSelectedTargetId] = useState<string | undefined>(undefined);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkSession() {
      const token = getAuthToken();
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const u = await apiFetch<any>("/api/v1/auth/me");
        setUser(u);
      } catch (err) {
        console.error("Session invalid", err);
        setAuthToken("");
      } finally {
        setLoading(false);
      }
    }
    checkSession();
  }, []);

  const handleNavigate = (view: string, targetId?: string) => {
    setCurrentView(view);
    if (targetId) {
      setSelectedTargetId(targetId);
    }
  };

  const handleLogout = () => {
    setAuthToken("");
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-netra-bg flex items-center justify-center font-mono text-xs text-netra-purple animate-pulse">
        Initializing NETRA-X Intelligence Interface...
      </div>
    );
  }

  if (!user) {
    return <LoginScreen onLoginSuccess={(u) => setUser(u)} />;
  }

  return (
    <ToastProvider>
      <CommandPalette
        onNavigate={handleNavigate}
        onOpenCopilot={() => setIsCopilotOpen(true)}
        onLogout={handleLogout}
      />
      <AppShell
        currentView={currentView}
        onNavigate={handleNavigate}
        userEmail={user.email}
        onLogout={handleLogout}
        onOpenCopilot={() => setIsCopilotOpen(true)}
      >
      {/* Keyed on the view id so the enter animation replays on every module
          change; without the key React reuses the node and nothing animates. */}
      <div key={currentView} className="view-enter">
      {currentView === "command_center" && <CommandCenter onNavigate={handleNavigate} />}
      {currentView === "cases" && <CasesView />}
      {currentView === "actors" && (
        <ActorProfile
          actorId={selectedTargetId}
          onBack={() => setCurrentView("command_center")}
          onNavigate={handleNavigate}
        />
      )}
      {currentView === "attribution_lab" && (
        <AttributionLab
          hypothesisId={selectedTargetId}
          onNavigate={handleNavigate}
        />
      )}
      {currentView === "graph_explorer" && <GraphExplorer actorId={selectedTargetId} />}
      {currentView === "evidence_vault" && <EvidenceVault />}
      {currentView === "audit_log" && <AuditLogViewer />}

      </div>

        <CopilotDrawer isOpen={isCopilotOpen} onClose={() => setIsCopilotOpen(false)} />
      </AppShell>
    </ToastProvider>
  );
}
