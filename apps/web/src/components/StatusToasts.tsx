"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";

/*
  Action feedback.

  Submitting an analyst decision -- ACCEPT, REJECT, INSUFFICIENT -- changed the
  ledger and appended an audit event, and told the analyst nothing. On a system
  whose whole claim is a defensible record, a write that lands silently is the
  wrong default: the operator cannot tell a success from a dropped request.

  Styled as a console readout rather than a product notification: monospace,
  square, hard 1px rule, a severity bar down the left edge. It reports what the
  system did, in the system's own voice.
*/

export type ToastKind = "ok" | "error" | "warn" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  detail?: string;
}

interface ToastApi {
  push: (kind: ToastKind, title: string, detail?: string) => void;
}

const ToastContext = createContext<ToastApi>({ push: () => {} });

export const useToast = () => useContext(ToastContext);

const STYLES: Record<ToastKind, { bar: string; text: string; Icon: typeof Info }> = {
  // Severity is carried by the same tokens the rest of the console uses, so a
  // red toast means what red means everywhere else.
  ok: { bar: "bg-netra-valid", text: "text-netra-valid", Icon: CheckCircle2 },
  error: { bar: "bg-netra-red", text: "text-netra-red", Icon: XCircle },
  warn: { bar: "bg-netra-amber", text: "text-netra-amber", Icon: AlertTriangle },
  info: { bar: "bg-netra-purple", text: "text-netra-purple", Icon: Info },
};

const LIFETIME_MS = 4200;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((kind: ToastKind, title: string, detail?: string) => {
    // Date.now() collides when two toasts fire in the same millisecond, which
    // duplicate React keys and drops one of them.
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, kind, title, detail }]);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div
        className="fixed bottom-5 right-5 z-[9997] flex flex-col gap-2 pointer-events-none"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <ToastRow key={t.id} toast={t} onDone={() => setToasts((x) => x.filter((i) => i.id !== t.id))} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

const ToastRow: React.FC<{ toast: Toast; onDone: () => void }> = ({ toast, onDone }) => {
  const [leaving, setLeaving] = useState(false);
  const { bar, text, Icon } = STYLES[toast.kind];

  useEffect(() => {
    const out = setTimeout(() => setLeaving(true), LIFETIME_MS);
    const gone = setTimeout(onDone, LIFETIME_MS + 220);
    return () => {
      clearTimeout(out);
      clearTimeout(gone);
    };
  }, [onDone]);

  return (
    <div
      className={`pointer-events-auto flex items-stretch bg-netra-card border border-netra-border min-w-[280px] max-w-[380px] shadow-hard ${
        leaving ? "toast-out" : "toast-in"
      }`}
    >
      <div className={`w-[3px] shrink-0 ${bar}`} />
      <div className="flex items-start gap-2.5 px-3 py-2.5">
        <Icon className={`w-4 h-4 mt-[1px] shrink-0 ${text}`} />
        <div className="min-w-0">
          <div className="font-mono text-[11px] uppercase tracking-telemetry text-netra-text">
            {toast.title}
          </div>
          {toast.detail && (
            <div className="font-mono text-[10px] text-netra-muted mt-0.5 break-words">{toast.detail}</div>
          )}
        </div>
      </div>
    </div>
  );
};
