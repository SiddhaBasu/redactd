"use client";
// Virtualised document viewer (task D1). Only the rows in view are in the DOM, so a 1 MB document with ~10k
// findings scrolls smoothly. Rows are fixed height and soft-wrapped at a measured column count (lib/layout.ts),
// which keeps every finding at its exact character offsets.
//
// Accessibility: the viewer is one tab stop. j/k (or arrows) move a virtual focus between findings; the focused
// finding is announced through aria-activedescendant and described in the popover (role="status").
import { forwardRef, memo, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { firstSpanAfter, rowAt, wrapRows, type Rows } from "../lib/layout";
import { SOURCE_NAMES, TYPE_INFO, TYPES } from "../lib/labels";
import type { PiiType, ReviewSpan } from "../lib/types";
import { typeClass } from "./ui";

export const ROW_H = 24;
const PAD_X = 12, OVERSCAN = 12, POP_W = 340;

export interface ViewerHandle { scrollToSpan: (id: number) => void; focus: () => void; rows: () => Rows | null; selection: () => { start: number; end: number } | null }
interface Props {
  text: string; spans: ReviewSpan[]; focus: number; mode: "review" | "diff";
  /** replacement string per span id (diff mode / output preview) */
  replacements?: string[];
  hidden: Set<PiiType>; dim?: (s: ReviewSpan) => boolean;
  onFocus: (id: number) => void; onToggle: (id: number) => void; onToggleValue: (id: number) => void; onRetype: (id: number, t: PiiType) => void; onRemove: (id: number) => void;
  sameValueCount: (id: number) => number; height?: string;
}

function useCharWidth(): [React.RefObject<HTMLSpanElement | null>, number] {
  const ref = useRef<HTMLSpanElement>(null);
  const [w, setW] = useState(7.8);
  useLayoutEffect(() => {
    const measure = () => { const el = ref.current; if (el) { const cw = el.getBoundingClientRect().width / 40; if (cw > 2) setW(cw); } };
    measure();
    document.fonts?.ready.then(measure).catch(() => {});
  }, []);
  return [ref, w];
}

const Row = memo(function Row({ text, a, b, top, spans, i0, focus, hidden, dim, replacements, side }: {
  text: string; a: number; b: number; top: number; spans: ReviewSpan[]; i0: number; focus: number; hidden: Set<PiiType>; dim?: (s: ReviewSpan) => boolean;
  replacements?: string[]; side: "orig" | "out";
}) {
  const out: ReactNode[] = [];
  let pos = a;
  for (let i = i0; i < spans.length && spans[i].start < b; i++) {
    const s = spans[i];
    const from = Math.max(s.start, a), to = Math.min(s.end, b);
    if (to <= from) continue;
    if (from > pos) out.push(text.slice(pos, from));
    if (side === "out" && s.accepted) {
      // show the replacement once, where the finding starts
      if (s.start >= a) out.push(<span key={s.id} className="rep">{replacements?.[s.id] ?? "█"}</span>);
    } else {
      const first = s.start >= a;
      out.push(
        <mark key={s.id + (first ? "" : "c")} id={first && side === "orig" ? `f-${s.id}` : undefined} data-id={s.id} className={`f ${typeClass(s.type)}`}
          data-off={s.accepted ? undefined : "1"} data-focus={s.id === focus ? "1" : undefined} data-dim={dim?.(s) ? "1" : undefined} data-plain={hidden.has(s.type) ? "1" : undefined}>
          {text.slice(from, to)}
        </mark>,
      );
    }
    pos = to;
  }
  if (pos < b) out.push(text.slice(pos, b));
  return <div className="doc-row" style={{ top }} data-a={a}>{out.length ? out : "​"}</div>;
});

export const Viewer = forwardRef<ViewerHandle, Props>(function Viewer(p, ref) {
  const { text, spans, focus, mode } = p;
  const scroller = useRef<HTMLDivElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const [probe, charW] = useCharWidth();
  const [size, setSize] = useState({ w: 800, h: 480 });
  const [scrollTop, setScrollTop] = useState(0);
  const raf = useRef(0);

  useLayoutEffect(() => {
    const el = scroller.current!;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el); setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const paneW = mode === "diff" ? Math.floor(size.w / 2) : size.w;
  const cols = Math.max(20, Math.floor((paneW - PAD_X * 2 - 2) / charW));
  const rows = useMemo(() => wrapRows(text, cols), [text, cols]);
  const total = rows.count * ROW_H;

  const onScroll = useCallback(() => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => { if (scroller.current) setScrollTop(scroller.current.scrollTop); });
  }, []);

  const scrollToSpan = useCallback((id: number) => {
    const s = spans[id], el = scroller.current;
    if (!s || !el) return;
    const y = rowAt(rows, s.start) * ROW_H;
    if (y < el.scrollTop + ROW_H || y > el.scrollTop + el.clientHeight - ROW_H * 9) el.scrollTop = Math.max(0, y - Math.min(el.clientHeight / 3, 160));
  }, [spans, rows]);

  useImperativeHandle(ref, () => ({
    scrollToSpan, focus: () => scroller.current?.focus(), rows: () => rows,
    selection: () => {
      const sel = window.getSelection(), el = scroller.current;
      if (!sel || sel.isCollapsed || !el || !el.contains(sel.anchorNode) || !el.contains(sel.focusNode)) return null;
      const off = (node: Node, o: number): number | null => {
        const row = (node.nodeType === 1 ? (node as Element) : node.parentElement)?.closest<HTMLElement>(".doc-row[data-side='orig']");
        if (!row) return null;
        const r = document.createRange(); r.selectNodeContents(row); r.setEnd(node, o);
        return Number(row.dataset.a) + r.toString().replace(/​/g, "").length;
      };
      const x = off(sel.anchorNode!, sel.anchorOffset), y = off(sel.focusNode!, sel.focusOffset);
      if (x === null || y === null || x === y) return null;
      return { start: Math.min(x, y), end: Math.max(x, y) };
    },
  }), [scrollToSpan, rows]);

  useEffect(() => { if (focus >= 0) scrollToSpan(focus); }, [focus, scrollToSpan]);

  // ---- visible window
  const first = Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN);
  const last = Math.min(rows.count, Math.ceil((scrollTop + size.h) / ROW_H) + OVERSCAN);
  const rendered: ReactNode[] = [];
  for (let r = first; r < last; r++) {
    const a = rows.start[r], b = rows.end[r], i0 = firstSpanAfter(spans, a), top = r * ROW_H;
    if (mode === "diff") {
      rendered.push(
        <div key={r} className="absolute left-0 right-0" style={{ top, height: ROW_H }}>
          <div className="absolute inset-y-0 left-0 overflow-hidden" style={{ width: "50%" }}><RowWrap side="orig"><Row text={text} a={a} b={b} top={0} spans={spans} i0={i0} focus={focus} hidden={p.hidden} dim={p.dim} side="orig" /></RowWrap></div>
          <div className="absolute inset-y-0 right-0 overflow-hidden" style={{ width: "50%", borderLeft: "1px solid var(--border)" }}><RowWrap side="out"><Row text={text} a={a} b={b} top={0} spans={spans} i0={i0} focus={-1} hidden={p.hidden} replacements={p.replacements} side="out" /></RowWrap></div>
        </div>,
      );
    } else rendered.push(<RowWrap key={r} side="orig" top={top}><Row text={text} a={a} b={b} top={0} spans={spans} i0={i0} focus={focus} hidden={p.hidden} dim={p.dim} side="orig" /></RowWrap>);
  }

  // ---- popover for the focused finding
  const f = focus >= 0 ? spans[focus] : undefined;
  let pop: ReactNode = null;
  if (f && mode === "review") {
    const r = rowAt(rows, f.start);
    const col = f.start - rows.start[r];
    const left = Math.max(8, Math.min(size.w - POP_W - 24, PAD_X + col * charW - 12));
    const below = (r + 1) * ROW_H + 6;
    pop = <FindingPopover span={f} value={text.slice(f.start, f.end)} style={{ top: below, left, width: Math.min(POP_W, size.w - 16) }} same={p.sameValueCount(f.id)}
      onToggle={() => p.onToggle(f.id)} onToggleValue={() => p.onToggleValue(f.id)} onRetype={(t) => p.onRetype(f.id, t)} onRemove={() => p.onRemove(f.id)} />;
  }

  // ---- minimap (scrollbar markers)
  useEffect(() => {
    const cv = canvas.current;
    if (!cv) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1), H = size.h, W = 14;
    cv.width = W * dpr; cv.height = H * dpr;
    const g = cv.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    const css = getComputedStyle(cv), colour: Record<string, string> = {};
    for (const t of TYPES) colour[t] = css.getPropertyValue(`--t-${TYPE_INFO[t].token}-bd`).trim() || "#888";
    const off = css.getPropertyValue("--border-strong").trim() || "#999";
    const scale = rows.count * ROW_H <= H ? ROW_H : H / rows.count;
    let lastY = -1, lastType = "";
    for (const s of spans) {
      const y = Math.floor(rowAt(rows, s.start) * scale);
      const key = s.accepted ? s.type : "off";
      if (y === lastY && key === lastType) continue;      // at most one mark per pixel row and colour
      g.fillStyle = s.accepted ? colour[s.type] : off;
      g.fillRect(s.accepted ? 2 : 6, y, s.accepted ? 10 : 4, Math.max(2, Math.min(4, scale)));
      lastY = y; lastType = key;
    }
    if (total > H) {
      g.strokeStyle = css.getPropertyValue("--fg").trim() || "#000"; g.lineWidth = 1;
      g.strokeRect(0.5, Math.floor((scrollTop / total) * H) + 0.5, W - 1, Math.max(8, Math.floor((H / total) * H)));
    }
  }, [spans, rows, size.h, scrollTop, total]);

  const mapJump = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const el = scroller.current!, rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    el.scrollTop = Math.max(0, (rows.count * ROW_H <= size.h ? frac * size.h : frac * total) - size.h / 2);
  };

  const onClick = (e: React.MouseEvent) => {
    const m = (e.target as HTMLElement).closest<HTMLElement>("mark[data-id]");
    if (!m || (window.getSelection() && !window.getSelection()!.isCollapsed)) return;
    const id = Number(m.dataset.id);
    if (id === focus) p.onToggle(id); else p.onFocus(id);
  };

  return (
    <div className="relative flex" style={{ height: p.height ?? "min(62vh, 640px)" }}>
      <span ref={probe} aria-hidden="true" className="doc pointer-events-none invisible absolute">{"0".repeat(40)}</span>
      <div ref={scroller} onScroll={onScroll} onClick={onClick} tabIndex={0} role="group" data-testid="viewer"
        aria-label={`Document with ${spans.length} findings. Press j or k to move between findings, x to redact or keep, question mark for all shortcuts.`}
        aria-activedescendant={f ? `f-${f.id}` : undefined}
        className="doc relative min-w-0 flex-1 overflow-y-auto overflow-x-hidden rounded-l-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)", overscrollBehavior: "contain" }}>
        <div style={{ height: total + (mode === "review" ? 220 : 0), position: "relative" }}>
          {rendered}
          {pop}
        </div>
      </div>
      <canvas ref={canvas} onPointerDown={mapJump} onPointerMove={(e) => e.buttons === 1 && mapJump(e)} aria-hidden="true" data-testid="minimap"
        className="flex-none cursor-pointer rounded-r-lg" style={{ width: 14, height: "100%", background: "var(--surface-2)", border: "1px solid var(--border)", borderLeft: 0, touchAction: "none" }} />
    </div>
  );
});

function RowWrap({ children, side, top }: { children: ReactNode; side: "orig" | "out"; top?: number }) {
  // data-side marks original-text rows so text selection can be mapped back to document offsets
  return <div data-side={side} style={top === undefined ? undefined : { position: "absolute", left: 0, right: 0, top, height: ROW_H }} className="doc-rowwrap">{children}</div>;
}

function FindingPopover({ span: s, value, style, same, onToggle, onToggleValue, onRetype, onRemove }: {
  span: ReviewSpan; value: string; style: CSSProperties; same: number; onToggle: () => void; onToggleValue: () => void; onRetype: (t: PiiType) => void; onRemove: () => void;
}) {
  const info = TYPE_INFO[s.type];
  const conf = s.score === null || s.score === undefined ? null : Math.round(s.score * 100);
  const sources = (s.sources?.length ? s.sources : [s.source]).filter((x, i, a) => a.indexOf(x) === i);
  return (
    <div role="status" aria-live="polite" data-testid="popover" className="card absolute z-10 p-3 text-[13px] leading-5" style={{ ...style, fontFamily: "var(--font-sans)", boxShadow: "var(--shadow)", whiteSpace: "normal" }}
      onClick={(e) => e.stopPropagation()}>
      <div className="flex items-center gap-2">
        <span className={`chip ${typeClass(s.type)}`}>{info.short}</span>
        <span className="font-semibold">{s.accepted ? "Will be redacted" : "Kept as is"}</span>
        <span className="ml-auto muted">{conf === null ? "pattern match" : `${conf}% confidence`}</span>
      </div>
      <div className="mono mt-2 max-h-10 overflow-hidden break-all rounded px-1.5 py-0.5 text-xs" style={{ background: "var(--surface-2)" }}>{value.length > 90 ? value.slice(0, 90) + "…" : value}</div>
      <dl className="mt-2 space-y-1">
        <div className="flex gap-2"><dt className="w-14 flex-none muted">Found by</dt><dd>{sources.map((x) => SOURCE_NAMES[x] ?? x).join(", ")}</dd></div>
        {!!s.why?.length && <div className="flex gap-2"><dt className="w-14 flex-none muted">Why</dt><dd><ul>{s.why.slice(0, 4).map((w) => <li key={w}>{w}</li>)}</ul></dd></div>}
      </dl>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" className="btn btn-sm btn-primary" onClick={onToggle}>{s.accepted ? "Keep" : "Redact"} <span className="kbd">x</span></button>
        {same > 1 && <button type="button" className="btn btn-sm" onClick={onToggleValue}>{s.accepted ? "Keep" : "Redact"} all {same}</button>}
        <label className="sr-only" htmlFor="pop-type">Category</label>
        <select id="pop-type" className="input ml-auto w-auto py-0 text-xs" style={{ minHeight: "1.75rem" }} value={s.type} onChange={(e) => onRetype(e.target.value as PiiType)}>
          {TYPES.map((t) => <option key={t} value={t}>{TYPE_INFO[t].short}</option>)}
        </select>
        {(s.source === "manual" || s.source === "custom") && <button type="button" className="btn btn-sm" onClick={onRemove}>Remove</button>}
      </div>
    </div>
  );
}
