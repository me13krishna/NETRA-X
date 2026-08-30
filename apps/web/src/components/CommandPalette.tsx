"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  LayoutDashboard, FileSearch, Users, GitMerge, ListTree, FileText, Lock,
  Search, CornerDownLeft, Bot, LogOut,
} from "lucide-react";
import { apiFetch } from "../lib/api";

/*
  Command palette.

  The console had no keyboard path at all: every navigation was a mouse trip to
  the rail, and finding a specific actor among fourteen meant opening a view and
  scanning it. For an operator tool that is the wrong ergonomics -- the people
  this is built for keep their hands on the keys.

  Ctrl+K / Cmd+K opens it. Actions and actors are searched together, because an
  analyst thinks "get me ShadowByte", not "navigate, then filter".
*/

interface Action {
  id: string;
  label: string;
  hint?: string;
  group: string;
  Icon: typeof Search;
  run: () => void;
}

interface CommandPaletteProps {
  onNavigate: (view: string, targetId?: string) => void;
  onOpenCopilot: () => void;
  onLogout: () => void;
}

const VIEWS: { id: string; label: string; Icon: typeof Search }[] = [
  { id: "command_center", label: "Command Center", Icon: LayoutDashboard },
  { id: "cases", label: "Investigations", Icon: FileSearch },
  { id: "actors", label: "Actor Explorer", Icon: Users },
  { id: "attribution_lab", label: "Attribution Lab", Icon: GitMerge },
  { id: "graph_explorer", label: "Intelligence Graph", Icon: ListTree },
  { id: "evidence_vault", label: "Evidence Vault", Icon: FileText },
  { id: "audit_log", label: "Audit Chain", Icon: Lock },
];

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  onNavigate,
  onOpenCopilot,
  onLogout,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [actors, setActors] = useState<any[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Global hotkey. Bound on window so it works regardless of focus, except
  // while typing into a field -- intercepting Ctrl+K inside an input would
  // steal a shortcut the browser and the user both expect to keep.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        setOpen(false);
      } else if (e.key === "/" && !typing) {
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCursor(0);
      return;
    }
    inputRef.current?.focus();
    // Actors are fetched on open rather than on mount: the palette is usually
    // never opened, and this keeps it off the initial page load.
    apiFetch<any[]>("/api/v1/actors")
      .then(setActors)
      .catch(() => setActors([]));
  }, [open]);

  const actions = useMemo<Action[]>(() => {
    const nav: Action[] = VIEWS.map((v) => ({
      id: `nav:${v.id}`,
      label: v.label,
      group: "Navigate",
      Icon: v.Icon,
      run: () => onNavigate(v.id),
    }));

    const people: Action[] = actors.map((a) => ({
      id: `actor:${a.id}`,
      label: a.primary_alias,
      hint: a.category,
      group: "Threat actors",
      Icon: Users,
      run: () => onNavigate("actors", a.id),
    }));

    const system: Action[] = [
      { id: "sys:copilot", label: "Open AI Copilot", group: "System", Icon: Bot, run: onOpenCopilot },
      { id: "sys:logout", label: "Sign out", group: "System", Icon: LogOut, run: onLogout },
    ];

    return [...nav, ...people, ...system];
  }, [actors, onNavigate, onOpenCopilot, onLogout]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions.slice(0, 9);
    return actions
      .filter((a) => `${a.label} ${a.hint ?? ""} ${a.group}`.toLowerCase().includes(q))
      .slice(0, 12);
  }, [actions, query]);

  useEffect(() => setCursor(0), [query]);

  const commit = (a?: Action) => {
    const target = a ?? results[cursor];
    if (!target) return;
    target.run();
    setOpen(false);
  };

  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(results.length - 1, c + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(0, c - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      commit();
    }
  };

  // Keep the highlighted row in view when arrowing past the fold.
  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-idx="${cursor}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  let lastGroup = "";

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-start justify-center pt-[12vh] bg-netra-bg/80 palette-backdrop"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-[560px] bg-netra-card border border-netra-border shadow-hard palette-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-3.5 py-3 border-b border-netra-border">
          <Search className="w-4 h-4 text-netra-purple shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="Search actions and threat actors..."
            className="flex-1 bg-transparent outline-none font-mono text-[13px] text-netra-text placeholder:text-netra-subtle"
          />
          <kbd className="font-mono text-[10px] text-netra-subtle border border-netra-border px-1.5 py-0.5">
            ESC
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[46vh] overflow-y-auto py-1.5">
          {results.length === 0 && (
            <div className="px-4 py-6 text-center font-mono text-[11px] text-netra-subtle">
              No match for &apos;{query}&apos;
            </div>
          )}
          {results.map((a, i) => {
            const header = a.group !== lastGroup ? a.group : null;
            lastGroup = a.group;
            const active = i === cursor;
            return (
              <div key={a.id}>
                {header && (
                  <div className="px-3.5 pt-2.5 pb-1 font-mono text-[9px] uppercase tracking-telemetry text-netra-subtle">
                    {header}
                  </div>
                )}
                <button
                  data-idx={i}
                  onMouseEnter={() => setCursor(i)}
                  onClick={() => commit(a)}
                  className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-left transition-colors ${
                    active ? "bg-netra-purple/15 text-netra-text" : "text-netra-muted hover:bg-netra-hover"
                  }`}
                >
                  <a.Icon className={`w-3.5 h-3.5 shrink-0 ${active ? "text-netra-purple" : "text-netra-subtle"}`} />
                  <span className="font-mono text-[12px] truncate">{a.label}</span>
                  {a.hint && (
                    <span className="ml-auto font-mono text-[10px] text-netra-subtle truncate pl-3">{a.hint}</span>
                  )}
                  {active && <CornerDownLeft className="w-3 h-3 text-netra-purple shrink-0 ml-1" />}
                </button>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-3 px-3.5 py-2 border-t border-netra-border font-mono text-[9px] uppercase tracking-telemetry text-netra-subtle">
          <span>↑↓ navigate</span>
          <span>⏎ open</span>
          <span className="ml-auto">{results.length} result{results.length === 1 ? "" : "s"}</span>
        </div>
      </div>
    </div>
  );
};
