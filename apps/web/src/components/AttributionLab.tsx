"use client";

import React, { useEffect, useState } from "react";
import {
  GitMerge, ShieldCheck, AlertOctagon, CheckCircle2, XCircle, HelpCircle,
  Download, Lock, FileText, ArrowRight
} from "lucide-react";
import { apiFetch, downloadReportPdf } from "../lib/api";
import { EvidenceWaterfall } from "./EvidenceWaterfall";

interface AttributionLabProps {
  hypothesisId?: string;
  onNavigate: (view: string) => void;
}

export const AttributionLab: React.FC<AttributionLabProps> = ({
  hypothesisId,
  onNavigate
}) => {
  const [hypothesis, setHypothesis] = useState<any>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadHypothesis() {
      try {
        const list = await apiFetch<any[]>("/api/v1/hypotheses");
        const target = hypothesisId ? list.find((h) => h.id === hypothesisId) : list[0];
        setHypothesis(target || list[0]);
      } catch (err) {
        console.error("Failed loading hypothesis", err);
      }
    }
    loadHypothesis();
  }, [hypothesisId]);

  if (!hypothesis) {
    return <div className="p-8 text-netra-muted text-sm font-mono animate-pulse">Loading Attribution Intelligence Lab...</div>;
  }

  const handleDecision = async (decision: "ACCEPT" | "REJECT" | "INSUFFICIENT") => {
    setSubmitting(true);
    setReviewMessage(null);
    try {
      const updated = await apiFetch<any>(`/api/v1/hypotheses/${hypothesis.id}/review`, {
        method: "POST",
        body: JSON.stringify({ decision, notes }),
      });
      setHypothesis(updated);
      setReviewMessage(`Analyst Decision '${decision}' recorded & SHA-256 hash-chained to audit log.`);
    } catch (err: any) {
      setReviewMessage(`Error submitting decision: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handlePdfExport = async () => {
    setExporting(true);
    try {
      await downloadReportPdf(hypothesis.id);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const familyCaps: Record<string, number> = {
    "Exact Identity": 10.0,
    "Financial": 7.5,
    "Infrastructure": 5.0,
    "Stylometry": 3.0,
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex justify-between items-center border-b border-netra-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide flex items-center space-x-2">
            <GitMerge className="w-6 h-6 text-netra-purple" />
            <span>Bayesian Attribution Intelligence Lab</span>
          </h1>
          <p className="text-xs text-netra-muted mt-0.5">
            Log-Likelihood Ratio Fusion, Dependence Discounting & Isotonic Calibration
          </p>
        </div>

        <button
          onClick={handlePdfExport}
          disabled={exporting}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-netra-purple text-white hover:bg-netra-purple/80 font-medium text-xs shadow-lg transition disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <span>{exporting ? "Generating PDF..." : "Export Signed PDF Report"}</span>
        </button>
      </div>

      {/* Candidate Pair Header */}
      <div className="bg-netra-card border border-netra-border rounded-xl p-6 glass-panel space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-netra-surface border border-netra-purple/50">
              <span className="text-xs text-netra-subtle block font-mono">SUBJECT ENTITY</span>
              <span className="text-lg font-bold text-white">{hypothesis.subject_label}</span>
            </div>

            <ArrowRight className="w-6 h-6 text-netra-purple" />

            <div className="p-3 rounded-xl bg-netra-surface border border-netra-cyan/50">
              <span className="text-xs text-netra-subtle block font-mono">CANDIDATE TARGET</span>
              <span className="text-lg font-bold text-netra-cyan">{hypothesis.object_label}</span>
            </div>
          </div>

          <div className="text-right space-y-1">
            <span className={`px-3 py-1 rounded text-xs font-mono font-bold ${
              hypothesis.status === "ACCEPTED" || hypothesis.status === "ACCEPT"
                ? "bg-netra-valid/20 text-netra-valid border border-netra-valid/40"
                : hypothesis.status === "REJECTED" || hypothesis.status === "REJECT"
                ? "bg-netra-red/20 text-netra-red border border-netra-red/40"
                : "bg-netra-amber/20 text-netra-amber border border-netra-amber/40"
            }`}>
              STATUS: {hypothesis.status}
            </span>
            <div className="text-xs text-netra-muted">
              Raw LLR Score: <span className="text-white font-mono font-bold">{hypothesis.raw_log_lr.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Calibrated Probability Gauge */}
        <div className="p-4 bg-netra-surface border border-netra-border rounded-xl space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-netra-muted font-medium">ISOTONIC CALIBRATED POSTERIOR PROBABILITY</span>
            <span className="font-bold text-netra-valid text-sm font-mono">
              {(hypothesis.calibrated_prob * 100).toFixed(1)}% ({hypothesis.confidence_tier})
            </span>
          </div>

          <div className="w-full h-3 bg-netra-bg rounded-full overflow-hidden border border-netra-border flex">
            <div
              className="h-full bg-gradient-to-r from-netra-cyan via-netra-purple to-netra-valid transition-all duration-500"
              style={{ width: `${hypothesis.calibrated_prob * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Grid: Family Breakdown + Evidence Waterfall & Analyst Decision Panel */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Evidence Waterfall & Family Caps */}
        <div className="col-span-2 space-y-6">
          {/* Family Caps Breakdown */}
          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-3">
            <h2 className="text-sm font-semibold text-white border-b border-netra-border pb-2">
              Evidence Family Contribution Caps
            </h2>

            <div className="grid grid-cols-2 gap-4">
              {Object.entries(familyCaps).map(([fam, cap]) => {
                const score = hypothesis.family_breakdown[fam] || 0;
                const pct = Math.min((score / cap) * 100, 100);
                return (
                  <div key={fam} className="p-3 bg-netra-surface border border-netra-border rounded-lg space-y-1.5">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="text-netra-muted">{fam}</span>
                      <span className="text-white font-mono">+{score.toFixed(1)} / {cap.toFixed(1)}</span>
                    </div>
                    <div className="w-full h-1.5 bg-netra-bg rounded-full overflow-hidden">
                      <div className="h-full bg-netra-purple rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Evidence Waterfall */}
          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-white border-b border-netra-border pb-2 flex items-center justify-between">
              <span>Evidence Waterfall Ledger</span>
              <span className="text-xs text-netra-subtle font-mono">DEPENDENCE DISCOUNT $\lambda=0.15$</span>
            </h2>

            <EvidenceWaterfall
              supporting={hypothesis.supporting_evidence}
              contradictions={hypothesis.contradictions}
            />
          </div>
        </div>

        {/* Right Column (1 Col): Mandatory Analyst Review Action Panel */}
        <div className="space-y-6">
          <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-4 sticky top-20 glass-panel">
            <h2 className="text-sm font-semibold text-white border-b border-netra-border pb-2 flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-netra-valid" />
              <span>Mandatory Analyst Review</span>
            </h2>

            <p className="text-xs text-netra-muted leading-relaxed">
              Per strict architecture constraints, AI generates hypotheses only. You must evaluate the evidence waterfall and issue an explicit decision.
            </p>

            <div className="space-y-2">
              <label className="text-xs text-netra-subtle font-medium block">Analyst Assessment Notes:</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter justification notes (e.g. Verified multi-family corroboration across PGP key & wallet cluster...)"
                rows={4}
                className="w-full bg-netra-surface border border-netra-border rounded-lg p-2.5 text-xs text-white placeholder-netra-subtle focus:outline-none focus:border-netra-purple transition"
              />
            </div>

            {reviewMessage && (
              <div className="p-3 rounded bg-netra-surface border border-netra-purple/40 text-xs text-netra-cyan font-mono leading-tight">
                {reviewMessage}
              </div>
            )}

            <div className="space-y-2 pt-2">
              <button
                onClick={() => handleDecision("ACCEPT")}
                disabled={submitting}
                className="w-full py-2.5 rounded-lg bg-netra-valid text-white hover:bg-netra-valid/80 font-bold text-xs flex items-center justify-center space-x-2 shadow transition disabled:opacity-50"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>ACCEPT LINKAGE</span>
              </button>

              <button
                onClick={() => handleDecision("REJECT")}
                disabled={submitting}
                className="w-full py-2.5 rounded-lg bg-netra-red text-white hover:bg-netra-red/80 font-bold text-xs flex items-center justify-center space-x-2 shadow transition disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" />
                <span>REJECT LINKAGE</span>
              </button>

              <button
                onClick={() => handleDecision("INSUFFICIENT")}
                disabled={submitting}
                className="w-full py-2.5 rounded-lg bg-netra-surface border border-netra-border text-netra-muted hover:text-white font-semibold text-xs flex items-center justify-center space-x-2 transition disabled:opacity-50"
              >
                <HelpCircle className="w-4 h-4" />
                <span>INSUFFICIENT EVIDENCE</span>
              </button>
            </div>

            <div className="pt-3 border-t border-netra-border text-[11px] text-netra-subtle flex items-center space-x-1.5">
              <Lock className="w-3.5 h-3.5 text-netra-valid" />
              <span>Decisions append to SHA-256 audit chain.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
