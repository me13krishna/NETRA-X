"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Hash, ShieldCheck, AlertOctagon, ExternalLink } from "lucide-react";

interface EvidenceWaterfallProps {
  supporting: any[];
  contradictions: any[];
}

export const EvidenceWaterfall: React.FC<EvidenceWaterfallProps> = ({
  supporting,
  contradictions
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-4">
      {/* Supporting Evidence Items */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-netra-muted uppercase tracking-wider flex items-center justify-between">
          <span>Supporting Evidence ({supporting.length})</span>
          <span className="text-netra-purple font-mono">+LLR CORROBORATED</span>
        </h3>

        {supporting.map((item) => {
          const isExpanded = expandedId === item.evidence_id;
          return (
            <div
              key={item.evidence_id}
              className="bg-netra-surface border border-netra-border hover:border-netra-purple/50 rounded-lg overflow-hidden transition"
            >
              <div
                onClick={() => toggleExpand(item.evidence_id)}
                className="p-3.5 flex items-center justify-between cursor-pointer select-none"
              >
                <div className="flex items-center space-x-3">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-netra-purple" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-netra-subtle" />
                  )}
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-netra-purple">{item.family}</span>
                      <span className="text-xs text-netra-subtle">•</span>
                      <span className="text-xs font-mono text-netra-muted">{item.extraction_method}</span>
                    </div>
                    <div className="text-xs font-semibold text-white mt-0.5">{item.value}</div>
                  </div>
                </div>

                <div className="text-right flex items-center space-x-4">
                  <div className="text-xs">
                    <span className="text-netra-subtle">Reliability: </span>
                    <span className="font-mono text-netra-valid">{(item.reliability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-xs font-mono bg-netra-purple/20 text-netra-purple px-2.5 py-1 rounded border border-netra-purple/30 font-bold">
                    +{item.contribution.toFixed(2)} LLR
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="p-4 bg-netra-bg/80 border-t border-netra-border space-y-3 text-xs font-mono">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-netra-subtle">Evidence ID:</span>
                      <div className="text-white">{item.evidence_id}</div>
                    </div>
                    <div>
                      <span className="text-netra-subtle">Dependence Group:</span>
                      <div className="text-netra-cyan">{item.dependence_group}</div>
                    </div>
                    <div>
                      <span className="text-netra-subtle">Source URI:</span>
                      <div className="text-netra-muted break-all flex items-center space-x-1">
                        <span>{item.source_uri}</span>
                        <ExternalLink className="w-3 h-3 text-netra-subtle shrink-0" />
                      </div>
                    </div>
                    <div>
                      <span className="text-netra-subtle">Raw Artifact SHA-256:</span>
                      <div className="text-netra-valid break-all flex items-center space-x-1">
                        <Hash className="w-3 h-3 text-netra-valid shrink-0" />
                        <span>{item.sha256}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Contradiction Evidence Items */}
      {contradictions.length > 0 && (
        <div className="space-y-2 pt-3 border-t border-netra-border">
          <h3 className="text-xs font-semibold text-netra-red uppercase tracking-wider flex items-center justify-between">
            <span>Contradiction Penalties ({contradictions.length})</span>
            <span className="font-mono">-UNCAPPED SUBTRACTION</span>
          </h3>

          {contradictions.map((item) => {
            const isExpanded = expandedId === item.evidence_id;
            return (
              <div
                key={item.evidence_id}
                className="bg-netra-red/10 border border-netra-red/40 rounded-lg overflow-hidden transition"
              >
                <div
                  onClick={() => toggleExpand(item.evidence_id)}
                  className="p-3.5 flex items-center justify-between cursor-pointer select-none"
                >
                  <div className="flex items-center space-x-3">
                    <AlertOctagon className="w-4 h-4 text-netra-red shrink-0" />
                    <div>
                      <div className="text-xs font-bold text-netra-red">CONTRADICTION FLAG</div>
                      <div className="text-xs font-semibold text-white mt-0.5">{item.value}</div>
                    </div>
                  </div>

                  <div className="text-xs font-mono bg-netra-red/20 text-netra-red px-2.5 py-1 rounded border border-netra-red/40 font-bold">
                    {item.contribution.toFixed(2)} LLR
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 bg-netra-bg/90 border-t border-netra-red/30 space-y-2 text-xs font-mono">
                    <div className="text-netra-muted">Source URI: {item.source_uri}</div>
                    <div className="text-netra-subtle">Extraction Method: {item.extraction_method}</div>
                    <div className="text-netra-red font-semibold">
                      Notice: Contradiction penalties are never silently dropped or capped per architectural specification.
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
