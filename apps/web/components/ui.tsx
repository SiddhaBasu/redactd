"use client";
// Small design-system primitives. Styling lives in app/globals.css (tokens + component classes).
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { TYPE_INFO } from "../lib/labels";
import type { PiiType } from "../lib/types";

export const typeClass = (t: PiiType) => `t-${TYPE_INFO[t].token}`;
export function TypeChip({ type, children }: { type: PiiType; children?: ReactNode }) {
  return <span className={`chip ${typeClass(type)}`}>{children ?? TYPE_INFO[type].short}</span>;
}
export function Kbd({ children }: { children: ReactNode }) { return <kbd className="kbd">{children}</kbd>; }

export function Segmented<T extends string>({ value, onChange, options, label }: { value: T; onChange: (v: T) => void; options: { id: T; label: string }[]; label: string }) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}>{o.label}</button>)}
    </div>
  );
}

export function Switch({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  const id = useId();
  return (
    <div className="flex items-start gap-3">
      <button type="button" role="switch" aria-checked={checked} aria-labelledby={`${id}-l`} aria-describedby={hint ? `${id}-h` : undefined} onClick={() => onChange(!checked)}
        className="relative mt-0.5 h-6 w-11 flex-none rounded-full border" style={{ background: checked ? "var(--accent)" : "var(--surface-2)", borderColor: checked ? "var(--accent)" : "var(--border-strong)" }}>
        <span className="absolute top-0.5 h-[18px] w-[18px] rounded-full transition-all" style={{ left: checked ? 22 : 2, background: checked ? "var(--accent-fg)" : "var(--border-strong)" }} />
      </button>
      <div className="text-sm"><div id={`${id}-l`} className="font-medium">{label}</div>{hint && <div id={`${id}-h`} className="muted text-xs">{hint}</div>}</div>
    </div>
  );
}

/** Modal dialog with focus trap, Escape to close and focus restore. */
export function Dialog({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null), id = useId();
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("button, [href], input, select, textarea")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); }
      if (e.key === "Tab" && ref.current) {
        const f = [...ref.current.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])")].filter((x) => !x.hasAttribute("disabled"));
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => { document.removeEventListener("keydown", onKey, true); prev?.focus?.(); };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4" style={{ background: "rgb(0 0 0 / 0.5)" }} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={id} className={`card max-h-[90vh] w-full overflow-auto p-5 ${wide ? "sm:max-w-2xl" : "sm:max-w-md"}`} style={{ boxShadow: "var(--shadow)" }}>
        <div className="mb-3 flex items-center gap-3">
          <h2 id={id} className="text-lg font-semibold">{title}</h2>
          <button type="button" className="btn btn-ghost btn-sm ml-auto" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

type Theme = "system" | "light" | "dark";
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => { try { const t = localStorage.getItem("redactd.theme") as Theme | null; if (t === "light" || t === "dark") setTheme(t); } catch { /* ignore */ } }, []);
  useEffect(() => {
    const el = document.documentElement;
    if (theme === "system") el.removeAttribute("data-theme"); else el.setAttribute("data-theme", theme);
    try { if (theme === "system") localStorage.removeItem("redactd.theme"); else localStorage.setItem("redactd.theme", theme); } catch { /* ignore */ }
  }, [theme]);
  const next: Theme = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
  return (
    <button type="button" className="btn btn-ghost btn-sm" onClick={() => setTheme(next)} aria-label={`Theme: ${theme}. Switch to ${next}.`} title={`Theme: ${theme}`}>
      <span aria-hidden="true">{theme === "system" ? "◐" : theme === "light" ? "☀" : "☾"}</span><span className="hidden sm:inline">{theme[0].toUpperCase() + theme.slice(1)}</span>
    </button>
  );
}

export function Progress({ pct, stage, onCancel }: { pct: number; stage: string; onCancel?: () => void }) {
  return (
    <div role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: "var(--surface-2)" }} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)} aria-label="Scan progress">
          <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(2, Math.min(100, pct))}%`, background: "var(--accent)" }} />
        </div>
        <span className="mono w-10 text-right text-xs">{Math.round(pct)}%</span>
        {onCancel && <button type="button" className="btn btn-sm" onClick={onCancel}>Cancel</button>}
      </div>
      <p className="mt-1 text-xs muted">{stage}</p>
    </div>
  );
}

export function Steps({ current }: { current: 1 | 2 | 3 }) {
  const steps = ["Add document", "Review findings", "Export"];
  return (
    <ol className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm" aria-label="Progress">
      {steps.map((s, i) => (
        <li key={s} className="flex items-center gap-2" aria-current={current === i + 1 ? "step" : undefined}>
          <span className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold"
            style={i + 1 <= current ? { background: "var(--accent)", color: "var(--accent-fg)" } : { background: "var(--surface-2)", color: "var(--muted)", boxShadow: "inset 0 0 0 1px var(--border-strong)" }}>{i + 1}</span>
          <span className={current === i + 1 ? "font-semibold" : "muted"}>{s}</span>
        </li>
      ))}
    </ol>
  );
}
