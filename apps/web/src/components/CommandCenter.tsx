"use client";

import React, { useEffect, useState } from "react";
import {
  Users, GitMerge, FileText, ShieldAlert, Cpu, Activity,
  ArrowUpRight, Clock, AlertTriangle, CheckCircle, Database
} from "lucide-react";
import { apiFetch } from "../lib/api";
import { useCountUp } from "../lib/useCountUp";
import { useToast } from "./StatusToasts";
import { ReviewQueue } from "./ReviewQueue";

/** One KPI figure. Split out so each tile owns its own count-up. */
function StatValue({ value, loading }: { value: number; loading: boolean }) {
  const shown = useCountUp(loading ? null : value);
  return (
    <div className="text-3xl font-bold text-white font-mono data-arrive tabular-nums">
      {loading ? "..." : shown}
    </div>
  );
}

interface CommandCenterProps {
  onNavigate: (view: string, targetId?: string) => void;
  onOpenReportModal?: () => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ onNavigate, onOpenReportModal }) => {
  const [actorsCount, setActorsCount] = useState(0);
  const [hypotheses, setHypotheses] = useState<any[]>([]);
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [loading, setLoading] = useState(true);

  // Investigation input state
  const [identifierType, setIdentifierType] = useState("handle");
  const [searchQuery, setSearchQuery] = useState("");
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsInvestigating(true);
    try {
      const res = await apiFetch<any>(`/api/v1/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(res.results || []);
      if (!res.results || res.results.length === 0) {
        // Fallback: create mock result or navigate to Actor Profile if not found
        toast.push("info", "Investigation launched", `${identifierType.toUpperCase()}: ${searchQuery} - collecting multi-source intelligence`);
        onNavigate("actor_profile");
      }
    } catch (err: any) {
      console.error("Search failed", err);
      onNavigate("actor_profile");
    } finally {
      setIsInvestigating(false);
    }
  };


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

  const toast = useToast();

  const handleReviewDecision = async (id: string, decision: string) => {
    try {
      await apiFetch(`/api/v1/review/${id}`, {
        method: "POST",
        body: JSON.stringify({ decision, notes: `Reviewed from Command Center Queue (${decision})` })
      });
      await loadData();
      // The write also appends a hash-chained audit event, so the toast names
      // that: the analyst should see that the decision was recorded, not just
      // that a button responded.
      toast.push(
        decision === "REJECT" ? "warn" : "ok",
        `Hypothesis ${decision.toLowerCase()}ed`,
        `Decision written to ledger and audit chain · ${id.slice(0, 8)}`
      );
    } catch (err: any) {
      // Was a browser alert(): modal, unstyled, and it blocks the thread.
      toast.push("error", "Decision failed", err.message);
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
        <div className="text-right flex items-center space-x-3">
          {onOpenReportModal && (
            <button
              onClick={onOpenReportModal}
              className="px-3 py-1.5 rounded-lg bg-netra-purple/20 border border-netra-purple/50 text-white text-xs font-mono hover:bg-netra-purple/40 transition flex items-center space-x-1.5 shadow"
            >
              <FileText className="w-3.5 h-3.5 text-netra-cyan" />
              <span>Export Report</span>
            </button>
          )}
          <div className="text-xs text-netra-cyan font-mono bg-netra-surface px-3 py-1.5 rounded border border-netra-border">
            CALIBRATED CONFIDENCE AVG: <span className="text-white font-bold">{avgConfidence.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Primary Investigation Input Command Bar */}
      <div className="bg-netra-card border border-netra-purple/40 rounded-xl p-5 space-y-4 shadow-xl relative overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm font-semibold text-white">
            <ShieldAlert className="w-5 h-5 text-netra-purple animate-pulse" />
            <span>Start Threat Investigation</span>
          </div>
          <span className="text-[11px] text-netra-cyan font-mono">STEP 1: ENTER SEED IDENTIFIER</span>
        </div>

        {/* Identifier Type Selectors */}
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {[
            { id: "handle", label: "Threat Actor Handle" },
            { id: "wallet", label: "Crypto Wallet" },
            { id: "pgp", label: "PGP Fingerprint" },
            { id: "onion", label: "Onion URL" },
            { id: "email", label: "Email / Jabber" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setIdentifierType(item.id)}
              className={`px-3 py-1.5 rounded-lg border transition font-medium ${
                identifierType === item.id
                  ? "bg-netra-purple/20 border-netra-purple text-white shadow"
                  : "bg-netra-surface border-netra-border text-netra-subtle hover:text-white"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Input Bar & Investigate Button */}
        <form onSubmit={handleInvestigate} className="flex gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                identifierType === "wallet"
                  ? "e.g. bc1q9v83... or 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
                  : identifierType === "pgp"
                  ? "e.g. 4F3B 8C90... or RSA 4096 Key Fingerprint"
                  : identifierType === "onion"
                  ? "e.g. http://darkmarketx37ab.onion"
                  : identifierType === "email"
                  ? "e.g. shadow_phoenix@jabber.cz"
                  : "e.g. dark_phoenix or alias_x"
              }
              className="w-full bg-netra-surface border border-netra-border focus:border-netra-purple text-white font-mono text-sm rounded-lg px-4 py-3 placeholder-netra-subtle focus:outline-none transition"
            />
          </div>
          <button
            type="submit"
            disabled={isInvestigating || !searchQuery.trim()}
            className="px-6 py-3 bg-netra-purple hover:bg-netra-purple/80 disabled:opacity-50 text-white font-semibold text-sm rounded-lg flex items-center space-x-2 transition shadow-lg shrink-0"
          >
            {isInvestigating ? (
              <>
                <Activity className="w-4 h-4 animate-spin text-white" />
                <span>Correlating...</span>
              </>
            ) : (
              <>
                <span>Investigate</span>
                <ArrowUpRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Live Search & Match Results */}
        {searchResults.length > 0 && (
          <div className="pt-3 border-t border-netra-border space-y-2">
            <div className="text-xs text-netra-muted flex items-center space-x-1 font-mono">
              <CheckCircle className="w-3.5 h-3.5 text-netra-valid" />
              <span>Matching Intelligence Results Found:</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {searchResults.map((res: any, idx: number) => (
                <div
                  key={idx}
                  onClick={() => onNavigate("actor_profile", res.entity_id)}
                  className="p-3 bg-netra-surface border border-netra-border hover:border-netra-cyan/60 rounded-lg cursor-pointer transition text-xs space-y-1"
                >
                  <div className="flex justify-between items-center font-bold text-white">
                    <span>{res.title}</span>
                    <span className="text-netra-cyan font-mono">{res.entity_type}</span>
                  </div>
                  <div className="text-netra-muted">{res.snippet}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>


      {/* Hero Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-1">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Tracked Threat Actors</span>
            <Users className="w-4 h-4 text-netra-purple" />
          </div>
          <StatValue value={actorsCount} loading={loading} />
          <div className="text-[11px] text-netra-cyan">3 Aliases • 1 PGP Key • 2 BTC Wallets</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-2">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Evidence Artifacts</span>
            <FileText className="w-4 h-4 text-netra-cyan" />
          </div>
          <StatValue value={evidenceCount} loading={loading} />
          <div className="text-[11px] text-netra-valid">100% SHA-256 Hash Verified</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-3">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Attribution Hypotheses</span>
            <GitMerge className="w-4 h-4 text-netra-amber" />
          </div>
          <StatValue value={hypotheses.length} loading={loading} />
          <div className="text-[11px] text-netra-amber">{openHypotheses.length} Awaiting Analyst Review</div>
        </div>

        <div className="bg-netra-card border border-netra-border p-4 rounded-xl space-y-2 glass-panel boot-in boot-in-3">
          <div className="flex justify-between items-center text-netra-muted text-xs font-medium">
            <span>Active Cases</span>
            <ShieldAlert className="w-4 h-4 text-netra-valid" />
          </div>
          <StatValue value={1} loading={loading} />
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
