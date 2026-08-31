"use client";

import React, { useEffect, useState } from "react";
import { FileText, Hash, ExternalLink, Filter, Trash2, Globe, Plus } from "lucide-react";
import { apiFetch } from "../lib/api";

interface EvidenceVaultProps {
  onOpenIngestionModal?: () => void;
}

export const EvidenceVault: React.FC<EvidenceVaultProps> = ({ onOpenIngestionModal }) => {
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadEvidence = async () => {
    try {
      const data = await apiFetch<any[]>("/api/v1/evidence");
      setEvidenceList(data);
    } catch (err) {
      console.error("Failed loading evidence", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, []);

  const handleDeleteEvidence = async (id: string) => {
    if (!confirm("Are you sure you want to purge this evidence item from the vault?")) return;
    try {
      await apiFetch(`/api/v1/evidence/${id}`, { method: "DELETE" });
      setEvidenceList((prev) => prev.filter((e) => e.id !== id));
    } catch (err: any) {
      setEvidenceList((prev) => prev.filter((e) => e.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-netra-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide flex items-center space-x-2">
            <FileText className="w-6 h-6 text-netra-cyan" />
            <span>Immutable Evidence Vault</span>
          </h1>
          <p className="text-xs text-netra-muted mt-0.5">
            Authoritative Ledger of Extracted Artifacts, Source URIs & SHA-256 Hashes
          </p>
        </div>

        {onOpenIngestionModal && (
          <button
            onClick={onOpenIngestionModal}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-netra-cyan text-netra-bg hover:bg-netra-cyan/90 font-bold text-xs shadow-lg transition"
          >
            <Globe className="w-4 h-4" />
            <span>Ingest New Darknet Payload</span>
          </button>
        )}
      </div>

      <div className="bg-netra-card border border-netra-border rounded-xl p-5 space-y-4">
        {loading ? (
          <div className="p-8 text-netra-muted text-sm font-mono animate-pulse">Loading Evidence Ledger...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-netra-border text-netra-subtle bg-netra-surface">
                  <th className="p-3">Evidence ID</th>
                  <th className="p-3">Extraction Method</th>
                  <th className="p-3">Extracted Value</th>
                  <th className="p-3">Source URI</th>
                  <th className="p-3">Dependence Group</th>
                  <th className="p-3">SHA-256 Hash</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-netra-border">
                {evidenceList.map((e) => (
                  <tr key={e.id} className="hover:bg-netra-hover/50 transition">
                    <td className="p-3 text-netra-purple">{e.id.substring(0, 13)}...</td>
                    <td className="p-3 text-netra-muted">{e.extraction_method}</td>
                    <td className="p-3 text-white font-semibold">{e.value}</td>
                    <td className="p-3 text-netra-subtle flex items-center space-x-1">
                      <span>{e.source_uri}</span>
                      <ExternalLink className="w-3 h-3 text-netra-subtle" />
                    </td>
                    <td className="p-3 text-netra-cyan">{e.dependence_group}</td>
                    <td className="p-3 text-netra-valid flex items-center space-x-1">
                      <Hash className="w-3 h-3 text-netra-valid" />
                      <span>{e.sha256 ? e.sha256.substring(0, 16) + "..." : "Verified"}</span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleDeleteEvidence(e.id)}
                        title="Delete Evidence Record"
                        className="p-1 text-netra-muted hover:text-netra-hazard transition rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

