"use client";
// Review aids (task D3): bulk actions per category, a "needs review" queue sorted by lowest confidence with a
// confidence filter, and bulk actions per exact value.
import { useMemo, useState } from "react";
import { TYPE_INFO, TYPES } from "../lib/labels";
import { countsByType, needsReview } from "../lib/review";
import type { PiiType, ReviewSpan } from "../lib/types";
import { typeClass } from "./ui";

type Tab = "types" | "queue" | "values";
interface Props {
  text: string; spans: ReviewSpan[]; focus: number; hidden: Set<PiiType>; below: number; filterOn: boolean;
  onBelow: (v: number) => void; onFilter: (v: boolean) => void; onFocus: (id: number) => void;
  onType: (t: PiiType, accepted: boolean) => void; onHide: (t: PiiType) => void; onValue: (value: string, accepted: boolean) => void; onAll: (accepted: boolean) => void;
}
const clip = (v: string, n = 34) => { const s = v.replace(/\s+/g, " "); return s.length > n ? s.slice(0, n - 1) + "…" : s; };

export function Sidebar(p: Props) {
  const [tab, setTab] = useState<Tab>("types");
  const [q, setQ] = useState("");
  const counts = useMemo(() => countsByType(p.spans), [p.spans]);
  const queue = useMemo(() => needsReview(p.spans, p.below), [p.spans, p.below]);
  const values = useMemo(() => {
    const m = new Map<string, { value: string; type: PiiType; n: number; on: number; first: number }>();
    for (const s of p.spans) {
      const v = p.text.slice(s.start, s.end);
      const x = m.get(v) ?? { value: v, type: s.type, n: 0, on: 0, first: s.id };
      x.n++; if (s.accepted) x.on++; m.set(v, x);
    }
    return [...m.values()].sort((a, b) => b.n - a.n || a.first - b.first);
  }, [p.spans, p.text]);
  const shown = useMemo(() => { const k = q.trim().toLowerCase(); return (k ? values.filter((v) => v.value.toLowerCase().includes(k)) : values).slice(0, 200); }, [values, q]);
  const tabs: { id: Tab; label: string }[] = [{ id: "types", label: "Categories" }, { id: "queue", label: `Needs review (${queue.length})` }, { id: "values", label: "Values" }];

  return (
    <aside className="card flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden text-sm" aria-label="Review tools">
      <div role="tablist" aria-label="Review tools" className="flex border-b" style={{ borderColor: "var(--border)" }}>
        {tabs.map((t) => (
          <button key={t.id} role="tab" type="button" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls={`panel-${t.id}`} onClick={() => setTab(t.id)}
            className="flex-1 px-2 py-2 text-xs font-semibold" style={tab === t.id ? { boxShadow: "inset 0 -2px 0 var(--accent)" } : { color: "var(--muted)" }}>{t.label}</button>
        ))}
      </div>

      {tab === "types" && (
        <div role="tabpanel" id="panel-types" aria-labelledby="tab-types" className="space-y-1 overflow-auto p-3">
          <div className="mb-2 flex gap-2">
            <button type="button" className="btn btn-sm flex-1" onClick={() => p.onAll(true)}>Redact all</button>
            <button type="button" className="btn btn-sm flex-1" onClick={() => p.onAll(false)}>Keep all</button>
          </div>
          {TYPES.filter((t) => counts[t]).map((t) => {
            const c = counts[t]!, all = c.on === c.n, none = c.on === 0;
            return (
              <div key={t} className="flex items-center gap-2 py-0.5">
                <input type="checkbox" id={`type-${t}`} checked={all} ref={(el) => { if (el) el.indeterminate = !all && !none; }} onChange={(e) => p.onType(t, e.target.checked)} className="h-4 w-4" />
                <span className={`swatch ${typeClass(t)}`} aria-hidden="true" />
                <label htmlFor={`type-${t}`} className="flex-1 cursor-pointer" title={TYPE_INFO[t].description}>{TYPE_INFO[t].label}</label>
                <span className="mono text-xs muted" aria-label={`${c.on} of ${c.n} redacted`}>{c.on}/{c.n}</span>
                <button type="button" className="btn btn-ghost btn-sm" aria-pressed={p.hidden.has(t)} onClick={() => p.onHide(t)} aria-label={`${p.hidden.has(t) ? "Show" : "Hide"} ${TYPE_INFO[t].label} highlights`}>{p.hidden.has(t) ? "show" : "hide"}</button>
              </div>
            );
          })}
          {!p.spans.length && <p className="muted">No findings. Select text in the document and press “Redact selection”, or press <span className="kbd">/</span> to search.</p>}
          <p className="pt-2 text-xs muted">Direct identifiers (names, contact details, IDs) point to a person or account on their own. Dates, organisations and demographics identify someone in combination.</p>
        </div>
      )}

      {tab === "queue" && (
        <div role="tabpanel" id="panel-queue" aria-labelledby="tab-queue" className="flex min-h-0 flex-col p-3">
          <label htmlFor="below" className="label">Show findings under {Math.round(p.below * 100)}% confidence</label>
          <input id="below" type="range" min={0.2} max={1} step={0.05} value={p.below} onChange={(e) => p.onBelow(+e.target.value)} className="w-full" />
          <label className="mt-2 flex items-center gap-2 text-xs"><input type="checkbox" checked={p.filterOn} onChange={(e) => p.onFilter(e.target.checked)} className="h-4 w-4" /> Dim everything else and step through these only (<span className="kbd">j</span>/<span className="kbd">k</span>)</label>
          <ul className="mt-2 min-h-0 flex-1 space-y-1 overflow-auto" aria-label="Findings that need review, lowest confidence first">
            {queue.slice(0, 300).map((s) => (
              <li key={s.id}>
                <button type="button" onClick={() => p.onFocus(s.id)} aria-current={p.focus === s.id ? "true" : undefined}
                  className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left" style={p.focus === s.id ? { background: "var(--accent-soft)", color: "var(--accent-soft-fg)" } : undefined}>
                  <span className="mono w-9 flex-none text-xs">{Math.round((s.score ?? 0) * 100)}%</span>
                  <span className={`chip ${typeClass(s.type)}`}>{TYPE_INFO[s.type].short}</span>
                  <span className={`mono min-w-0 flex-1 truncate text-xs ${s.accepted ? "" : "line-through"}`}>{clip(p.text.slice(s.start, s.end))}</span>
                </button>
              </li>
            ))}
            {!queue.length && <li className="muted">Nothing below this confidence. Pattern matches with a checksum or keyword are treated as certain.</li>}
            {queue.length > 300 && <li className="muted text-xs">Showing the 300 least confident of {queue.length}.</li>}
          </ul>
        </div>
      )}

      {tab === "values" && (
        <div role="tabpanel" id="panel-values" aria-labelledby="tab-values" className="flex min-h-0 flex-col p-3">
          <label htmlFor="vfilter" className="sr-only">Filter values</label>
          <input id="vfilter" className="input" placeholder="Filter values…" value={q} onChange={(e) => setQ(e.target.value)} />
          <ul className="mt-2 min-h-0 flex-1 space-y-1 overflow-auto" aria-label="Distinct values">
            {shown.map((v) => (
              <li key={v.value} className="flex items-center gap-2">
                <button type="button" className="flex min-w-0 flex-1 items-center gap-2 rounded px-1 py-0.5 text-left" onClick={() => p.onFocus(v.first)} title="Go to first occurrence">
                  <span className={`swatch ${typeClass(v.type)}`} aria-hidden="true" />
                  <span className={`mono min-w-0 flex-1 truncate text-xs ${v.on ? "" : "line-through"}`}>{clip(v.value, 28)}</span>
                  <span className="mono text-xs muted">×{v.n}</span>
                </button>
                <button type="button" className="btn btn-sm" onClick={() => p.onValue(v.value, v.on === 0)} aria-label={`${v.on === 0 ? "Redact" : "Keep"} all ${v.n} occurrences of ${clip(v.value, 40)}`}>{v.on === 0 ? "Redact" : "Keep"} all</button>
              </li>
            ))}
            {values.length > shown.length && <li className="muted text-xs">Showing {shown.length} of {values.length} distinct values. Filter to narrow.</li>}
          </ul>
        </div>
      )}
    </aside>
  );
}
