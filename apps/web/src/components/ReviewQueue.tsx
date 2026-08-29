"use client";

import React, { useState } from "react";
import { ShieldCheck, AlertOctagon, CheckCircle2, XCircle, Clock, Filter, ArrowUpRight } from "lucide-react";

interface HypothesisItem {
  id: string;
  subject_label: string;
  object_label: string;
  calibrated_prob: number;
  confidence_tier: string;
  status: string;
  raw_log_lr: number;
  supporting_evidence?: any[];
  contradictions?: any[];
  family_breakdown?: Record<string, number>;
}

interface ReviewQueueProps {
  hypotheses: HypothesisItem[];
  onSelectHypothesis: (id: string) => void;
  onReviewDecision: (id: string, decision: string) => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({
  hypotheses,
  onSelectHypothesis,
  onReviewDecision
}) => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const filteredHypotheses = hypotheses.filter((h) => {
    if (statusFilter === "ALL") return true;
    return h.status.toUpperCase() === statusFilter.toUpperCase();
  }).sort((a, b) => b.calibrated_prob - a.calibrated_prob);

  return (
    <div className="space-y-4">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-netra-surface border border-netra-border p-4 rounded-xl">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-netra-purple/20 text-netra-purple rounded-lg border border-netra-purple/40">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Hypothesis Review Queue</h2>
            <p className="text-xs text-netra-subtle">Prioritized by isotonic calibrated posterior probability</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
          {["ALL", "PROPOSED", "ACCEPTED", "REJECTED", "INSUFFICIENT"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg border font-bold transition ${
                statusFilter === st
                  ? "bg-netra-purple text-white border-netra-purple shadow-lg shadow-netra-purple/30"
                  : "bg-netra-bg text-netra-muted border-netra-border hover:border-netra-purple/40"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Hypothesis Cards */}
      <div className="space-y-3">
        {filteredHypotheses.length === 0 ? (
          <div className="p-8 text-center bg-netra-surface border border-netra-border rounded-xl text-netra-subtle font-mono text-xs">
            No hypotheses matching status filter '{statusFilter}'.
          </div>
        ) : (
          filteredHypotheses.map((h) => {
            const hasContradiction = (h.contradictions && h.contradictions.length > 0) || h.raw_log_lr < 0;
            const familyCount = h.family_breakdown ? Object.keys(h.family_breakdown).length : (h.supporting_evidence ? h.supporting_evidence.length : 1);
            const probPct = (h.calibrated_prob * 100).toFixed(1);

            return (
              <div
                key={h.id}
                className="bg-netra-surface border border-netra-border hover:border-netra-purple/60 rounded-xl p-5 transition shadow-lg space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-netra-border/50 pb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg font-black text-white">{h.subject_label}</span>
                    <span className="text-netra-purple font-mono font-bold">↔</span>
                    <span className="text-lg font-black text-netra-cyan">{h.object_label}</span>
                  </div>

                  <div className="flex items-center space-x-2 font-mono text-xs">
                    <span className="bg-netra-purple/20 text-netra-purple px-2.5 py-1 rounded-md border border-netra-purple/30 font-bold">
                      {familyCount} Independent Families
                    </span>
                    {hasContradiction && (
                      <span className="bg-netra-red/20 text-netra-red px-2.5 py-1 rounded-md border border-netra-red/40 font-bold flex items-center space-x-1">
                        <AlertOctagon className="w-3.5 h-3.5" />
                        <span>Contradiction Flagged</span>
                      </span>
                    )}
                    <span className={`px-2.5 py-1 rounded-md border font-bold ${
                      h.status === "ACCEPTED" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40" :
                      h.status === "REJECTED" ? "bg-red-500/20 text-red-400 border-red-500/40" :
                      "bg-amber-500/20 text-amber-400 border-amber-500/40"
                    }`}>
                      {h.status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                  <div className="bg-netra-bg p-3 rounded-lg border border-netra-border">
                    <span className="text-netra-subtle block">Calibrated Probability P(H1|E):</span>
                    <span className="text-xl font-bold text-netra-valid">{probPct}%</span>
                    <span className="text-netra-muted text-[11px] block mt-0.5">{h.confidence_tier}</span>
                  </div>
                  <div className="bg-netra-bg p-3 rounded-lg border border-netra-border">
                    <span className="text-netra-subtle block">Raw Log-Likelihood Ratio:</span>
                    <span className={`text-xl font-bold ${h.raw_log_lr >= 0 ? "text-netra-purple" : "text-netra-red"}`}>
                      {h.raw_log_lr >= 0 ? `+${h.raw_log_lr.toFixed(2)}` : h.raw_log_lr.toFixed(2)} LLR
                    </span>
                  </div>
                  <div className="bg-netra-bg p-3 rounded-lg border border-netra-border flex flex-col justify-between">
                    <span className="text-netra-subtle block">Actions:</span>
                    <div className="flex items-center space-x-2 pt-1">
                      <button
                        onClick={() => onSelectHypothesis(h.id)}
                        className="flex-1 py-1.5 bg-netra-purple hover:bg-netra-purple/80 text-white font-bold rounded text-xs transition flex items-center justify-center space-x-1"
                      >
                        <span>Waterfall Detail</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Inline Review Decision Buttons */}
                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-netra-border/50 text-xs font-mono">
                  <span className="text-netra-subtle mr-2">Submit Analyst Review:</span>
                  <button
                    onClick={() => onReviewDecision(h.id, "ACCEPT")}
                    className="px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40 rounded font-bold transition flex items-center space-x-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>ACCEPT</span>
                  </button>
                  <button
                    onClick={() => onReviewDecision(h.id, "REJECT")}
                    className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 rounded font-bold transition flex items-center space-x-1"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>REJECT</span>
                  </button>
                  <button
                    onClick={() => onReviewDecision(h.id, "INSUFFICIENT")}
                    className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40 rounded font-bold transition flex items-center space-x-1"
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>INSUFFICIENT</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
