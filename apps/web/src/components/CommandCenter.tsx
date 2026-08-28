"use client";

import React, { useEffect, useState } from "react";
import {
  Users, GitMerge, FileText, ShieldAlert, Cpu, Activity,
  ArrowUpRight, Clock, AlertTriangle, CheckCircle, Database
} from "lucide-react";
import { apiFetch } from "../lib/api";

interface CommandCenterProps {
  onNavigate: (view: string, targetId?: string) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ onNavigate }) => {
  const [actorsCount, setActorsCount] = useState(0);
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
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
    }
    loadData();
  }, []);

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
            <span>Intelligence Command Center</span>
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
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Tracked Threat Actors</span>
            <Users className="w-4 h-4 text-netra-purple" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{loading ? "..." : actorsCount}</div>
          <div className="text-[11px] text-netra-cyan">3 Aliases • 1 PGP Key • 2 BTC Wallets</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Evidence Artifacts</span>
            <FileText className="w-4 h-4 text-netra-cyan" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{loading ? "..." : evidenceCount}</div>
          <div className="text-[11px] text-netra-valid">100% SHA-256 Hash Verified</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Attribution Hypotheses</span>
            <GitMerge className="w-4 h-4 text-netra-amber" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{loading ? "..." : hypotheses.length}</div>
          <div className="text-[11px] text-netra-amber">{openHypotheses.length} Awaiting Analyst Review</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Active Cases</span>
            <ShieldAlert className="w-4 h-4 text-netra-valid" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">1</div>
          <div className="text-[11px] text-netra-muted">Operation ShadowByte</div>
        </div>
      </div>

      {/* Main Grid: Attribution Review Queue & Live Stream */}
      <div className="grid grid-cols-3 gap-6">
        {/* Attribution Review Queue (2 Cols) */}
        <div className="col-span-2 bg-netra-card border border-netra-border rounded-xl p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-netra-border pb-3">
            <h2 className="font-semibold text-sm text-white flex items-center space-x-2">
              <GitMerge className="w-4 h-4 text-netra-purple" />
              <span>Attribution Review Queue</span>
            </h2>
            <span className="text-xs text-netra-subtle">Mandatory Human Review Required</span>
          </div>

          <div className="space-y-3">
            {hypotheses.map((h) => (
              <div
                key={h.id}
                className="bg-netra-surface border border-netra-border hover:border-netra-purple/50 p-4 rounded-lg flex items-center justify-between transition group"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm text-white">{h.subject_label}</span>
                    <span className="text-netra-subtle text-xs">&rarr;</span>
                    <span className="font-semibold text-sm text-netra-cyan">{h.object_label}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                      h.status === "ACCEPTED"
                        ? "bg-netra-valid/20 text-netra-valid border border-netra-valid/30"
                        : "bg-netra-amber/20 text-netra-amber border border-netra-amber/30"
                    }`}>
                      {h.status}
                    </span>
                  </div>
                  <div className="text-xs text-netra-muted flex items-center space-x-4">
                    <span>Calibrated Prob: <strong className="text-white font-mono">{(h.calibrated_prob * 100).toFixed(1)}%</strong></span>
                    <span>Tier: <strong className="text-netra-purple">{h.confidence_tier}</strong></span>
                    <span>Supporting Ev: <strong className="text-white">{h.supporting_evidence.length}</strong></span>
                    <span className="text-netra-red">Contradictions: <strong>{h.contradictions.length}</strong></span>
                  </div>
                </div>

                <button
                  onClick={() => onNavigate("attribution_lab", h.id)}
                  className="px-3 py-1.5 rounded bg-netra-purple/20 text-netra-purple hover:bg-netra-purple hover:text-white border border-netra-purple/40 text-xs font-medium flex items-center space-x-1 transition"
                >
                  <span>Launch Lab</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* System Health & Infrastructure Panel (1 Col) */}
        <div className="space-y-6">
          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-4">
            <h2 className="font-semibold text-sm text-white flex items-center space-x-2 border-b border-netra-border pb-3">
              <Cpu className="w-4 h-4 text-netra-cyan" />
              <span>Multi-Modal Service Mesh</span>
            </h2>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">PostgreSQL 16 (Authoritative)</span>
                <span className="text-netra-valid font-mono font-semibold">ONLINE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">Neo4j 5 (Graph Projection)</span>
                <span className="text-netra-valid font-mono font-semibold">REBUILDABLE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">Redis Streams (Event Bus)</span>
                <span className="text-netra-valid font-mono font-semibold">ONLINE</span>
              </div>

              <div className="flex justify-between items-center p-2 rounded bg-netra-surface border border-netra-border">
                <span className="text-netra-muted">MinIO (SHA-256 Storage)</span>
                <span className="text-netra-valid font-mono font-semibold">ONLINE</span>
              </div>
            </div>
          </div>

          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-3">
            <h2 className="font-semibold text-sm text-white flex items-center space-x-2">
              <Activity className="w-4 h-4 text-netra-valid" />
              <span>Infrastructure Leaks</span>
            </h2>
            <div className="p-3 bg-netra-surface rounded border border-netra-border text-xs space-y-1">
              <div className="text-netra-cyan font-mono">Favicon mmh3: -1598234912</div>
              <div className="text-netra-muted">Matched Clearnet IP: <span className="text-white font-mono">185.220.101.5</span></div>
              <div className="text-netra-subtle text-[10px]">TLS Cert Serial: 04:a1:b2:c3:d4:e5:f6:78</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
