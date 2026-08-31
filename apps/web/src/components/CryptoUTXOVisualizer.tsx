"use client";

/**
 * Wallet cluster view.
 *
 * This component previously rendered a four-step "mixer hop" chain -- seed
 * wallet, co-spend cluster, ChipMixer pool, exchange deposit -- with amounts
 * in BTC and transaction hashes like "0x89f1a2b3...4c5d". None of it existed.
 * The hops were a hardcoded array, the hashes were typed by hand, and the
 * same four steps rendered for every actor. It also carried a "local fallback
 * mock" that fabricated an LLR of 3.85 whenever the API call failed, so a
 * broken backend looked like a successful attribution.
 *
 * We do not hold chain transaction data, so no hop chain can be drawn
 * honestly. What the ledger does hold is which addresses belong to which
 * persona and which co-spending cluster each sits in -- and therefore which
 * differently-named personas control addresses in the same cluster. That
 * co-ownership was what the fake diagram was gesturing at, and it is a
 * stronger finding than a decorative flow chart, because it is real.
 */

import React, { useEffect, useState } from "react";
import { Wallet, Link2, AlertTriangle, Layers, Users, Loader2 } from "lucide-react";
import { apiFetch } from "../lib/api";

interface CoOwner {
  actor_id: string;
  actor: string;
  address: string;
}

interface WalletRow {
  address: string;
  chain: string;
  cluster_id: string | null;
  co_owners: CoOwner[];
}

interface WalletResponse {
  actor_id: string;
  actor: string;
  wallets: WalletRow[];
  wallet_count: number;
  clustered_count: number;
  shared_cluster_count: number;
}

export const CryptoUTXOVisualizer: React.FC<{ actorId?: string }> = ({ actorId }) => {
  const [data, setData] = useState<WalletResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!actorId) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiFetch<WalletResponse>(`/api/v1/actors/${actorId}/wallets`)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: any) => {
        // Deliberately no mock fallback. A failed lookup must read as a failed
        // lookup, not as a finding.
        if (!cancelled) setError(err?.message || "Failed to load wallet data");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [actorId]);

  return (
    <div className="bg-netra-surface border border-netra-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-netra-border">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-netra-purple/20 text-netra-purple rounded-lg border border-netra-purple/40">
            <Wallet className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-netra-text tracking-wide">
              WALLET CLUSTERS
            </h3>
            <p className="text-[11px] text-netra-muted font-mono">
              co-spending clusters from the evidence ledger
            </p>
          </div>
        </div>
        {data && (
          <div className="flex items-center space-x-4 text-[11px] font-mono text-netra-muted">
            <span>{data.wallet_count} addresses</span>
            <span>{data.clustered_count} clustered</span>
            {data.shared_cluster_count > 0 && (
              <span className="text-netra-hazard font-semibold">
                {data.shared_cluster_count} shared
              </span>
            )}
          </div>
        )}
      </div>

      <div className="p-4">
        {loading && (
          <div className="flex items-center space-x-2 text-netra-muted text-xs font-mono py-6 justify-center">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Reading wallet ledger...</span>
          </div>
        )}

        {error && (
          <div className="flex items-start space-x-2 text-netra-red text-xs font-mono py-4">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && data && data.wallets.length === 0 && (
          <p className="text-xs text-netra-muted font-mono py-6 text-center">
            No wallet addresses are recorded against {data.actor}.
          </p>
        )}

        {!loading && !error && data && data.wallets.length > 0 && (
          <div className="space-y-3">
            {data.wallets.map((w) => {
              const shared = w.co_owners.length > 0;
              return (
                <div
                  key={w.address}
                  className={`border rounded-lg p-3 ${
                    shared
                      ? "border-netra-hazard/50 bg-netra-hazard/5"
                      : "border-netra-border bg-netra-bg/40"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0">
                      <p className="font-mono text-xs text-netra-text break-all">
                        {w.address}
                      </p>
                      <div className="flex items-center space-x-3 mt-1 text-[11px] font-mono text-netra-muted">
                        <span className="px-1.5 py-0.5 border border-netra-border rounded">
                          {w.chain}
                        </span>
                        {w.cluster_id ? (
                          <span className="flex items-center space-x-1">
                            <Layers className="w-3 h-3" />
                            <span>{w.cluster_id}</span>
                          </span>
                        ) : (
                          <span className="italic">unclustered</span>
                        )}
                      </div>
                    </div>
                    {shared && (
                      <span className="flex items-center space-x-1 text-[11px] font-mono text-netra-hazard shrink-0">
                        <Users className="w-3 h-3" />
                        <span>{w.co_owners.length} co-owner{w.co_owners.length > 1 ? "s" : ""}</span>
                      </span>
                    )}
                  </div>

                  {shared && (
                    <div className="mt-3 pt-3 border-t border-netra-hazard/20 space-y-1.5">
                      <p className="text-[11px] text-netra-muted font-mono">
                        Same cluster, different persona:
                      </p>
                      {w.co_owners.map((c) => (
                        <div
                          key={c.actor_id + c.address}
                          className="flex items-center space-x-2 text-[11px] font-mono"
                        >
                          <Link2 className="w-3 h-3 text-netra-hazard shrink-0" />
                          <span className="text-netra-text font-semibold">{c.actor}</span>
                          <span className="text-netra-muted break-all">{c.address}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!actorId && !loading && (
          <p className="text-xs text-netra-muted font-mono py-6 text-center">
            Select an actor to view their wallet clusters.
          </p>
        )}
      </div>
    </div>
  );
};
