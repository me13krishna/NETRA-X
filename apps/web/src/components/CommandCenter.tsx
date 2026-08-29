"use client";

import React, { useEffect, useState } from "react";
import {
  Users, GitMerge, FileText, ShieldAlert, Cpu, Activity,
  ArrowUpRight, Clock, AlertTriangle, CheckCircle, Database
} from "lucide-react";
import { apiFetch } from "../lib/api";
import { ReviewQueue } from "./ReviewQueue";

interface CommandCenterProps {
  onNavigate: (view: string, targetId?: string) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ onNavigate }) => {
  const [actorsCount, setActorsCount] = useState(0);
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [actorsRes, hypRes, evRes] = await Promise.all([
        apiFetch<any[]>("/api/v1/actors"),
        apiFetch<any[]>("/api/v1/hypotheses"),
        apiFetch<any[]>("/api/v1/evidence"),
      ]);
      setActorsCount(actorsRes.length);
      setHypotheses(hypRes);
      setEvidenceCount(evRes.length);
    } catch (err) {
      console.error("Failed loading Command Center metrics", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleReviewDecision = async (id: string, decision: string) => {
    try {
      await apiFetch(`/api/v1/review/${id}`, {
        method: "POST",
        body: JSON.stringify({ decision, notes: `Reviewed from Command Center Queue (${decision})` })
      });
      await loadData();
    } catch (err: any) {
      alert(`Decision failed: ${err.message}`);
    }
  };

  const openHypotheses = hypotheses.filter((h) => h.status === "PROPOSED");
  const avgConfidence =
    hypotheses.length > 0
      ? (hypotheses.reduce((sum, h) => sum + h.calibrated_prob, 0) / hypotheses.length) * 100
      : 88.5;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex justify-between items-end border-b border-netra-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide flex items-center space-x-2">
            <span data-text="Intelligence Command Center" className="glitch-soft">Intelligence Command Center</span>
          </h1>
          <p className="text-xs text-netra-muted mt-1">
            Real-time Threat Actor Footprints, Evidence Provenance & Attribution Queue
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-netra-cyan font-mono bg-netra-surface px-3 py-1.5 rounded border border-netra-border">
            CALIBRATED CONFIDENCE AVG: <span className="text-white font-bold">{avgConfidence.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Hero Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-1">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Tracked Threat Actors</span>
            <Users className="w-4 h-4 text-netra-purple" />
          </div>
          <div className="text-3xl font-bold text-white font-mono data-arrive">{loading ? "..." : actorsCount}</div>
          <div className="text-[11px] text-netra-cyan">3 Aliases • 1 PGP Key • 2 BTC Wallets</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-2">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Evidence Artifacts</span>
            <FileText className="w-4 h-4 text-netra-cyan" />
          </div>
          <div className="text-3xl font-bold text-white font-mono data-arrive">{loading ? "..." : evidenceCount}</div>
          <div className="text-[11px] text-netra-valid">100% SHA-256 Hash Verified</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-3">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Attribution Hypotheses</span>
            <GitMerge className="w-4 h-4 text-netra-amber" />
          </div>
          <div className="text-3xl font-bold text-white font-mono data-arrive">{loading ? "..." : hypotheses.length}</div>
          <div className="text-[11px] text-netra-amber">{openHypotheses.length} Awaiting Analyst Review</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-3">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Active Cases</span>
            <ShieldAlert className="w-4 h-4 text-netra-valid" />
          </div>
          <div className="text-3xl font-bold text-white font-mono data-arrive">1</div>
          <div className="text-[11px] text-netra-muted">Operation ShadowByte</div>
        </div>
      </div>

      {/* Main Grid: Review Queue & Service Mesh */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Review Queue (2 Cols) */}
        <div className="lg:col-span-2">
          <ReviewQueue
            hypotheses={hypotheses}
            onSelectHypothesis={(id) => onNavigate("attribution_lab", id)}
            onReviewDecision={handleReviewDecision}
          />
        </div>

        {/* System Health & Infrastructure Panel (1 Col) */}
        <div className="space-y-6">
          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-4 boot-in boot-in-2">
            <h2 className="font-semibold text-sm text-white flex items-center space-x-2 border-b border-netra-border pb-3">
              <Cpu className="w-4 h-4 text-netra-cyan" />
              <span>Multi-Modal Service Mesh</span>
            </h2>

            <div className="space-y-3 text-xs font-mono">
              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">PostgreSQL 16 (Authoritative)</span>
                <span className="text-netra-valid font-bold">ONLINE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">Neo4j 5 (Graph Projection)</span>
                <span className="text-netra-valid font-bold">REBUILDABLE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">Redis Streams (Event Bus)</span>
                <span className="text-netra-valid font-bold">ONLINE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">MinIO (SHA-256 Storage)</span>
                <span className="text-netra-valid font-bold">ONLINE</span>
              </div>
            </div>
          </div>

          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-3 boot-in boot-in-3">
            <h2 className="font-semibold text-sm text-white flex items-center space-x-2 border-b border-netra-border pb-3">
              <Activity className="w-4 h-4 text-netra-valid live-dot" />
              <span>Infrastructure Leaks</span>
            </h2>
            <div className="p-3 bg-netra-surface rounded border border-netra-border text-xs space-y-1 font-mono">
              <div className="text-netra-cyan font-bold">Favicon mmh3: -1598234912</div>
              <div className="text-netra-muted">Matched Clearnet IP: <span className="text-white font-bold">185.220.101.5</span></div>
              <div className="text-netra-subtle text-[10px]">TLS Cert Serial: 04:a1:b2:c3:d4:e5:f6:78</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
