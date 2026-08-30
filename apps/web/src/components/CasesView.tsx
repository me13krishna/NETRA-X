"use client";

import React, { useEffect, useState } from "react";
import { FileSearch, Plus, ShieldCheck, Users, Calendar } from "lucide-react";
import { useToast } from "./StatusToasts";
import { apiFetch } from "../lib/api";

export const CasesView: React.FC = () => {
  const toast = useToast();
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    async function loadCases() {
      try {
        const res = await apiFetch<any[]>("/api/v1/investigations");
        setCases(res);
      } catch (err) {
        console.error("Failed loading cases", err);
      } finally {
        setLoading(false);
      }
    }
    loadCases();
  }, []);

  const handleCreateCase = async () => {
    if (!title.trim()) return;
    try {
      const created = await apiFetch<any>("/api/v1/investigations", {
        method: "POST",
        body: JSON.stringify({ title, description }),
      });
      setCases((prev) => [created, ...prev]);
      setShowModal(false);
      setTitle("");
      setDescription("");
    } catch (err: any) {
      toast.push("error", "Could not create investigation", err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-netra-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide flex items-center space-x-2">
            <FileSearch className="w-6 h-6 text-netra-purple" />
            <span>Investigation Cases</span>
          </h1>
          <p className="text-xs text-netra-muted mt-0.5">
            Object-Level ACL Case Management & Evidence Container Scope
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-netra-purple text-netra-bg hover:bg-netra-purple/80 font-medium text-xs shadow-lg transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Investigation Case</span>
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {loading ? (
          <div className="p-8 text-netra-muted text-sm font-mono animate-pulse col-span-2">Loading Investigation Cases...</div>
        ) : (
          cases.map((c) => (
            <div key={c.id} className="bg-netra-card border border-netra-border hover:border-netra-purple/50 rounded-xl p-5 space-y-3 transition glass-panel">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-base font-bold text-white">{c.title}</h2>
                  <div className="text-xs text-netra-subtle font-mono mt-0.5">Case ID: {c.id}</div>
                </div>
                <span className="px-2.5 py-1 rounded bg-netra-valid/20 text-netra-valid border border-netra-valid/30 text-xs font-mono">
                  {c.status}
                </span>
              </div>

              <p className="text-xs text-netra-muted">{c.description || "No description provided."}</p>

              <div className="pt-3 border-t border-netra-border flex justify-between items-center text-xs text-netra-subtle font-mono">
                <span className="flex items-center space-x-1">
                  <Users className="w-3.5 h-3.5 text-netra-purple" />
                  <span>{c.member_count} Investigators Assigned</span>
                </span>
                <span className="flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-netra-subtle" />
                  <span>{new Date(c.created_at).toLocaleDateString()}</span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* New Case Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-netra-card border border-netra-border rounded-xl p-6 w-full max-w-md space-y-4 shadow-2xl glass-panel">
            <h3 className="text-base font-bold text-white border-b border-netra-border pb-2">
              Create New Investigation Case
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-netra-subtle block mb-1">Case Title:</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Operation Darknet Syndicate"
                  className="w-full bg-netra-surface border border-netra-border rounded p-2.5 text-white placeholder-netra-subtle focus:outline-none focus:border-netra-purple"
                />
              </div>

              <div>
                <label className="text-netra-subtle block mb-1">Description:</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Summary of investigation scope..."
                  rows={3}
                  className="w-full bg-netra-surface border border-netra-border rounded p-2.5 text-white placeholder-netra-subtle focus:outline-none focus:border-netra-purple"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded bg-netra-surface border border-netra-border text-netra-muted hover:text-white text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCase}
                className="px-4 py-2 rounded bg-netra-purple text-netra-bg hover:bg-netra-purple/80 text-xs font-medium"
              >
                Create Case
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
