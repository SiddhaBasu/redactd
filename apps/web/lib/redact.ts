// Merge, propagate, render and leak-check. TypeScript port of redactd/vault.py.
import type { OutputStyle, PiiType, Span } from "./types";

export function mergeSpans<T extends Span>(spans: T[]): T[] {
  const s = [...spans].filter((x) => x.end > x.start).sort((a, b) => a.start - b.start || b.end - a.end);
  const out: T[] = [];
  for (const x of s) {
    const last = out[out.length - 1];
    if (last && x.start < last.end) {
      if (x.end > last.end) {
        // keep the type of the longer span
        const keep = last.end - last.start >= x.end - x.start ? last : x;
        out[out.length - 1] = { ...keep, start: last.start, end: x.end };
      }
    } else out.push({ ...x });
  }
  return out;
}

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Redact every occurrence of each detected value; for names also each capitalised part (e.g. surname alone). */
export function propagate(text: string, spans: Span[], minLen = 3): Span[] {
  const extra: Span[] = [];
  const seen = new Set<string>();
  for (const s of spans) {
    const v = text.slice(s.start, s.end);
    const key = `${s.type}\u0000${v}`;
    if (v.length < minLen || seen.has(key)) continue;
    seen.add(key);
    for (const m of text.matchAll(new RegExp(esc(v), "g")))
      extra.push({ start: m.index!, end: m.index! + v.length, type: s.type, source: "propagated" });
    if (s.type === "NAME")
      for (const part of v.split(/\s+/))
        if (part.length >= 3 && /^[A-Z]/.test(part))
          for (const m of text.matchAll(new RegExp(`\\b${esc(part)}\\b`, "g")))
            extra.push({ start: m.index!, end: m.index! + part.length, type: "NAME", source: "propagated" });
  }
  return mergeSpans([...spans, ...extra]);
}

export type Vault = Record<string, string>;

export function render(text: string, spans: Span[], style: OutputStyle): { output: string; vault: Vault } {
  const merged = mergeSpans(spans);
  const vault: Vault = {};
  const seen = new Map<string, string>();
  const counters: Partial<Record<PiiType, number>> = {};
  let out = "", last = 0;
  for (const s of merged) {
    const val = text.slice(s.start, s.end);
    let rep: string;
    if (style === "block") rep = "█".repeat(Math.min(Math.max(val.length, 3), 12));
    else if (style === "label") rep = `[${s.type}]`;
    else {
      const key = `${s.type}\u0000${val}`;
      if (!seen.has(key)) {
        counters[s.type] = (counters[s.type] ?? 0) + 1;
        const ph = `[${s.type}_${counters[s.type]}]`;
        seen.set(key, ph);
        vault[ph] = val;
      }
      rep = seen.get(key)!;
    }
    out += text.slice(last, s.start) + rep;
    last = s.end;
  }
  return { output: out + text.slice(last), vault };
}

export function restore(text: string, vault: Vault): string {
  return text.replace(/\[[A-Z_]+_\d+\]/g, (m) => vault[m] ?? m);
}

/** Return every redacted value (>=3 chars) that still appears in the output. Must be empty before download. */
export function leakCheck(output: string, values: string[]): string[] {
  return [...new Set(values)].filter((v) => v.length >= 3 && output.includes(v));
}
