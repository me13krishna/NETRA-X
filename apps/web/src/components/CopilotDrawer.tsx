"use client";

import React, { useState } from "react";
import { Bot, X, Send, ShieldAlert, Sparkles, Hash } from "lucide-react";
import { apiFetch } from "../lib/api";

interface CopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CopilotDrawer: React.FC<CopilotDrawerProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Array<{ sender: "user" | "ai"; text: string; evidenceIds?: string[] }>>([
    {
      sender: "ai",
      text: "Greetings Analyst. I am the NETRA-X Constrained Intelligence Copilot. Ask me about threat actor linkages, evidence provenance, or contradictions. I generate hypothesis summaries only and never decide primary attribution.",
    },
  ]);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSend = async () => {
    if (!query.trim()) return;

    const userText = query;
    setQuery("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await apiFetch<any>(`/api/v1/copilot/query?query_text=${encodeURIComponent(userText)}`, {
        method: "POST",
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: res.response,
          evidenceIds: res.referenced_evidence_ids,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: `Copilot service error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-netra-card border-l border-netra-border z-50 flex flex-col shadow-2xl glass-panel font-sans">
      {/* Header */}
      <div className="p-4 border-b border-netra-border flex items-center justify-between bg-netra-surface">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5 text-netra-purple" />
          <div>
            <h2 className="text-sm font-bold text-white">AI Intelligence Copilot</h2>
            <span className="text-[10px] text-netra-cyan font-mono">CONSTRAINED TO LEDGER</span>
          </div>
        </div>
        <button onClick={onClose} className="text-netra-subtle hover:text-white transition">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-lg space-y-1.5 ${
              m.sender === "user"
                ? "bg-netra-purple/20 text-white border border-netra-purple/40 ml-6"
                : "bg-netra-surface text-netra-text border border-netra-border mr-4"
            }`}
          >
            <div className="font-bold text-[10px] text-netra-subtle font-mono uppercase">
              {m.sender === "user" ? "Investigator" : "NETRA-X Copilot"}
            </div>
            <p className="leading-relaxed">{m.text}</p>

            {m.evidenceIds && m.evidenceIds.length > 0 && (
              <div className="pt-2 border-t border-netra-border space-y-1 text-[10px] font-mono text-netra-cyan">
                <div>Referenced Evidence Provenance IDs:</div>
                <div className="space-y-0.5">
                  {m.evidenceIds.slice(0, 3).map((id) => (
                    <div key={id} className="flex items-center space-x-1">
                      <Hash className="w-3 h-3 text-netra-purple" />
                      <span>{id.substring(0, 16)}...</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-netra-purple text-xs font-mono animate-pulse">Analyzing evidence ledger...</div>}
      </div>

      {/* Footer Disclaimer & Input */}
      <div className="p-3 border-t border-netra-border bg-netra-surface space-y-2">
        <div className="flex items-center space-x-2 bg-netra-bg p-2 rounded border border-netra-border">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask Copilot about ShadowByte or evidence..."
            className="flex-1 bg-transparent text-xs text-white placeholder-netra-subtle focus:outline-none"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="p-1.5 rounded bg-netra-purple text-netra-bg hover:bg-netra-purple/80 transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="text-[9px] text-netra-subtle text-center">
          AI assists with explainability. Primary attribution requires analyst verification.
        </div>
      </div>
    </div>
  );
};
