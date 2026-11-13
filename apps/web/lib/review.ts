// Review state: the list of findings, which are accepted, the focused finding, and an undo/redo stack.
// Pure functions over immutable arrays so the reducer is easy to test and undo is just "previous array".
import type { PiiType, ReviewSpan, Span } from "./types.ts";

export interface ReviewState { text: string; spans: ReviewSpan[]; focus: number; past: ReviewSpan[][]; future: ReviewSpan[][] }
export type ReviewAction =
  | { type: "load"; text: string; spans: Span[]; rejected?: Set<string> }
  | { type: "focus"; id: number }
  | { type: "move"; dir: 1 | -1; among?: (s: ReviewSpan) => boolean }
  | { type: "toggle"; id: number }
  | { type: "toggleValue"; id: number }
  | { type: "setValue"; value: string; accepted: boolean }
  | { type: "setType"; piiType: PiiType; accepted: boolean }
  | { type: "setAll"; accepted: boolean; among?: (s: ReviewSpan) => boolean }
  | { type: "retype"; id: number; piiType: PiiType }
  | { type: "add"; spans: Span[] }
  | { type: "remove"; id: number }
  | { type: "undo" } | { type: "redo" };

const UNDO_LIMIT = 200;
export const emptyReview: ReviewState = { text: "", spans: [], focus: -1, past: [], future: [] };
export const valueOf = (st: { text: string }, s: { start: number; end: number }) => st.text.slice(s.start, s.end);
/** Key that identifies "the same finding" across a re-scan or a policy change: type + exact value. */
export const decisionKey = (type: string, value: string) => type + "\u0000" + value;

const index = (spans: (Span & { accepted: boolean })[]): ReviewSpan[] =>
  spans.slice().sort((a, b) => a.start - b.start || a.end - b.end).map((s, id) => ({ ...s, id }));

function commit(st: ReviewState, spans: ReviewSpan[], focus = st.focus): ReviewState {
  if (spans === st.spans) return focus === st.focus ? st : { ...st, focus };
  return { ...st, spans, focus: Math.min(focus, spans.length - 1), past: [...st.past.slice(-UNDO_LIMIT + 1), st.spans], future: [] };
}
const mapWhere = (spans: ReviewSpan[], pred: (s: ReviewSpan) => boolean, accepted: boolean): ReviewSpan[] => {
  let changed = false;
  const out = spans.map((s) => (pred(s) && s.accepted !== accepted ? ((changed = true), { ...s, accepted }) : s));
  return changed ? out : spans;
};

export function reviewReducer(st: ReviewState, a: ReviewAction): ReviewState {
  switch (a.type) {
    case "load": {
      const spans = index(a.spans.map((s) => ({ ...s, accepted: !a.rejected?.has(decisionKey(s.type, a.text.slice(s.start, s.end))) })));
      return { text: a.text, spans, focus: spans.length ? 0 : -1, past: [], future: [] };
    }
    case "focus": return a.id >= -1 && a.id < st.spans.length ? { ...st, focus: a.id } : st;
    case "move": {
      const n = st.spans.length;
      if (!n) return st;
      for (let k = 1; k <= n; k++) {
        const i = (((st.focus < 0 ? (a.dir > 0 ? -1 : 0) : st.focus) + a.dir * k) % n + n) % n;
        if (!a.among || a.among(st.spans[i])) return { ...st, focus: i };
      }
      return st;
    }
    case "toggle": {
      const t = st.spans[a.id];
      return t ? commit(st, st.spans.map((s) => (s.id === a.id ? { ...s, accepted: !s.accepted } : s)), a.id) : st;
    }
    case "toggleValue": {
      const t = st.spans[a.id];
      if (!t) return st;
      const v = valueOf(st, t);
      return commit(st, mapWhere(st.spans, (s) => valueOf(st, s) === v, !t.accepted), a.id);
    }
    case "setValue": return commit(st, mapWhere(st.spans, (s) => valueOf(st, s) === a.value, a.accepted));
    case "setType": return commit(st, mapWhere(st.spans, (s) => s.type === a.piiType, a.accepted));
    case "setAll": return commit(st, mapWhere(st.spans, a.among ?? (() => true), a.accepted));
    case "retype": return st.spans[a.id] ? commit(st, st.spans.map((s) => (s.id === a.id ? { ...s, type: a.piiType } : s)), a.id) : st;
    case "add": {
      const add = a.spans.filter((x) => x.end > x.start && x.start >= 0 && x.end <= st.text.length);
      if (!add.length) return st;
      // a manual finding replaces whatever it overlaps; everything else keeps its state
      const keep = st.spans.filter((s) => !add.some((x) => x.start < s.end && x.end > s.start));
      const spans = index([...keep, ...add.map((x) => ({ ...x, accepted: true }))]);
      const first = Math.min(...add.map((x) => x.start));
      return commit(st, spans, spans.findIndex((s) => s.start === first));
    }
    case "remove": return st.spans[a.id] ? commit(st, index(st.spans.filter((s) => s.id !== a.id)), Math.min(a.id, st.spans.length - 2)) : st;
    case "undo": {
      if (!st.past.length) return st;
      const prev = st.past[st.past.length - 1];
      return { ...st, spans: prev, focus: Math.min(st.focus, prev.length - 1), past: st.past.slice(0, -1), future: [st.spans, ...st.future] };
    }
    case "redo": {
      if (!st.future.length) return st;
      const next = st.future[0];
      return { ...st, spans: next, focus: Math.min(st.focus, next.length - 1), past: [...st.past, st.spans], future: st.future.slice(1) };
    }
  }
}

/** Decisions to carry across a re-scan or a policy change: every (type, value) the user chose to keep. */
export function rejectedKeys(st: ReviewState): Set<string> {
  return new Set(st.spans.filter((s) => !s.accepted).map((s) => decisionKey(s.type, valueOf(st, s))));
}

/** All case-insensitive occurrences of `query` as manual findings (the "/" search-and-redact command). */
export function searchSpans(text: string, query: string, type: PiiType): Span[] {
  const q = query.trim();
  if (q.length < 2) return [];
  let hay = text.toLowerCase();
  const needle = hay.length === text.length ? q.toLowerCase() : q;
  if (hay.length !== text.length) hay = text;
  const out: Span[] = [];
  for (let i = hay.indexOf(needle); i >= 0; i = hay.indexOf(needle, i + needle.length))
    out.push({ start: i, end: i + q.length, type, source: "manual", score: null, label: "search", why: [`matches your search “${q}”`], sources: ["manual"] });
  return out;
}

export function countsByType(spans: ReviewSpan[]): Partial<Record<PiiType, { n: number; on: number }>> {
  const c: Partial<Record<PiiType, { n: number; on: number }>> = {};
  for (const s of spans) { const x = (c[s.type] ??= { n: 0, on: 0 }); x.n++; if (s.accepted) x.on++; }
  return c;
}

/** Findings that deserve a human look first: lowest model confidence first; rule-only findings are confident. */
export function needsReview(spans: ReviewSpan[], below = 0.7): ReviewSpan[] {
  return spans.filter((s) => s.score !== null && s.score !== undefined && s.score < below && !(s.sources ?? []).includes("rules") && s.source !== "manual")
    .sort((a, b) => (a.score as number) - (b.score as number));
}
