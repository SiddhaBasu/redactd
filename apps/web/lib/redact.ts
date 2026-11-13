// Span post-processing and rendering. A line-for-line port of redactd/post.py (finalize chain) and
// redactd/vault.py (render / restore / leak check). Keep them in step: tests/test_rule_parity.py runs both
// implementations on the same inputs and requires identical output.
// Only ASCII character classes are used for boundary logic so Python and JavaScript agree.
import { SPEC } from "./rules.ts";
import { DEFAULT_OPTIONS, type Options, type OutputStyle, type PiiType, type Span } from "./types.ts";

const LEX = SPEC.lexicon;
const isLetter = (c: string) => (c >= "a" && c <= "z") || (c >= "A" && c <= "Z");
const isDigit = (c: string) => c >= "0" && c <= "9";
const isUpper = (c: string) => c.toUpperCase() === c && c.toLowerCase() !== c;
const hasDigit = (v: string) => /[0-9]/.test(v);
const hasAlnum = (v: string) => /[A-Za-z0-9\u0080-￿]/.test(v);
const WS = " \t\n\r\f\v ";
const TRIM_CHARS = WS + ",;:";
const strip = (v: string) => { let a = 0, b = v.length; while (a < b && WS.includes(v[a])) a++; while (b > a && WS.includes(v[b - 1])) b--; return v.slice(a, b); };

/** Tokenizer offsets can include a leading space or trailing punctuation. Never strip brackets:
 *  that once turned "(415)" into "([CONTACT_2]". */
export function trimBounds(text: string, s: number, e: number): [number, number] {
  while (s < e && TRIM_CHARS.includes(text[s])) s++;
  while (e > s && TRIM_CHARS.includes(text[e - 1])) e--;
  return [s, e];
}

/** Every place `v` occurs as a value. Letters-only values must not be glued to other letters ("Art" does not match
 *  inside "Article"); short numeric values must not be glued to other digits. Longer values that contain digits
 *  match anywhere, so identifiers glued to text (SWIFT/FIX fields) are still caught. */
export function occurrences(text: string, v: string): [number, number][] {
  if (!v) return [];
  const digit = hasDigit(v), n = v.length, out: [number, number][] = [];
  let i = text.indexOf(v);
  while (i >= 0) {
    const j = i + n;
    let ok = true;
    if (!digit) {
      if (isLetter(v[0]) && i > 0 && isLetter(text[i - 1])) ok = false;
      if (isLetter(v[n - 1]) && j < text.length && isLetter(text[j])) ok = false;
    } else if (n < 6) {
      if (isDigit(v[0]) && i > 0 && isDigit(text[i - 1])) ok = false;
      if (isDigit(v[n - 1]) && j < text.length && isDigit(text[j])) ok = false;
    }
    if (ok) { out.push([i, j]); i = text.indexOf(v, j); } else i = text.indexOf(v, i + 1);
  }
  return out;
}

// ---------------------------------------------------------------- merge
const mk = (start: number, end: number, type: PiiType, source: string, score: number | null, label: string | null | undefined, why: string[], sources: string[]): Span =>
  ({ start, end, type, source, score, label: label ?? null, why, sources });

/** Union overlapping spans. Type: a rule covering at least half of the union wins; otherwise the longest member. */
export function mergeSpans(text: string, spans: Span[]): Span[] {
  const sorted = spans.filter((s) => s.end > s.start).map((s, i) => [s, i] as const)
    .sort((a, b) => a[0].start - b[0].start || a[0].end - b[0].end || a[1] - b[1]).map(([s]) => s);
  const groups: Span[][] = [];
  let end = -1;
  for (const s of sorted) {
    if (groups.length && s.start < end) { groups[groups.length - 1].push(s); end = Math.max(end, s.end); }
    else { groups.push([s]); end = s.end; }
  }
  return groups.map((g) => {
    const a = g[0].start, b = Math.max(...g.map((x) => x.end));
    let best: Span | null = null;
    for (const x of g) if (x.source === "rules" && 2 * (x.end - x.start) >= b - a && (!best || x.end - x.start > best.end - best.start)) best = x;
    if (!best) for (const x of g) if (!best || x.end - x.start > best.end - best.start) best = x;
    const scores = g.filter((x) => x.score !== null && x.score !== undefined).map((x) => x.score as number);
    const sources: string[] = [], why: string[] = [];
    for (const x of g) {
      for (const src of x.sources?.length ? x.sources : [x.source]) if (!sources.includes(src)) sources.push(src);
      for (const w of x.why ?? []) if (!why.includes(w)) why.push(w);
    }
    return mk(a, b, best!.type, best!.source, scores.length ? Math.max(...scores) : null, best!.label, why, sources);
  });
}

// ---------------------------------------------------------------- precision filters
export function normTerm(v: string): string {
  v = strip(v.replace(/[ \t\n\r\f\v]+/g, " ")).toLowerCase();
  while (v && ".,;:".includes(v[v.length - 1])) v = v.slice(0, -1);
  if (v.startsWith("the ")) v = v.slice(4);
  return v;
}
const PUBLIC_RX = new RegExp(`^(?:${LEX.public_body_pattern})$`, "i");
const NONPERSONAL_DATE_RX = new RegExp(`^(?:${LEX.nonpersonal_date_pattern})$`, "i");
const ORG_ALLOW = new Set<string>(LEX.org_allowlist), GENERIC = new Set<string>(LEX.generic_terms);
export const isPublicBody = (v: string) => { const n = normTerm(v); return ORG_ALLOW.has(n) || PUBLIC_RX.test(n); };
export const isNonpersonalDate = (v: string) => NONPERSONAL_DATE_RX.test(strip(v));

function passesFilters(text: string, sp: Span, o: Options, allow: Set<string>): boolean {
  const v = text.slice(sp.start, sp.end);
  if (!hasAlnum(v)) return false;
  if (o.excludeTypes.includes(sp.type)) return false;
  if (allow.size && allow.has(normTerm(v))) return false;
  if (sp.source === "manual" || sp.source === "custom") return true;
  if (GENERIC.has(normTerm(v))) return false;
  if (o.orgAllowlist && sp.type === "ORG" && isPublicBody(v)) return false;
  if (o.dropNonpersonalDates && sp.type === "DATE" && isNonpersonalDate(v)) return false;
  return true;
}
function aboveThreshold(sp: Span, o: Options): boolean {
  if (sp.score === null || sp.score === undefined) return true;
  const table = (o.thresholds ?? LEX.thresholds) as Record<string, Record<string, number>>;
  return sp.score >= Math.max(table[sp.source]?.[sp.type] ?? 0, 0);
}

/** Drop model findings that no rule and no other model overlaps, when their score is under the per-label "solo" threshold. */
function dropUnsupported(spans: Span[], o: Options): Span[] {
  const table = (o.soloThresholds ?? LEX.solo_thresholds) as Record<string, Record<string, number>>;
  if (!Object.keys(table).length) return spans;
  const byOther = new Map<string, { starts: number[]; pmax: number[] }>();
  const others = (src: string) => {
    let v = byOther.get(src);
    if (!v) {
      const xs = spans.filter((x) => x.source !== src).map((x) => [x.start, x.end] as const).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      const pmax: number[] = [];
      let m = -1;
      for (const [, b] of xs) { m = Math.max(m, b); pmax.push(m); }
      v = { starts: xs.map((x) => x[0]), pmax }; byOther.set(src, v);
    }
    return v;
  };
  return spans.filter((sp) => {
    const th = sp.score === null || sp.score === undefined ? 0 : table[sp.source]?.[sp.label ?? ""] ?? 0;
    if (!(th > 0 && (sp.score as number) < th)) return true;
    const { starts, pmax } = others(sp.source);
    let lo = 0, hi = starts.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (starts[mid] < sp.end) lo = mid + 1; else hi = mid; }
    return lo > 0 && pmax[lo - 1] > sp.start;
  });
}

// ---------------------------------------------------------------- propagation (consistency + coreference)
const POSSESSIVE = /['’]s$/;
const STOP = new Set<string>(LEX.name_part_stop), COMMON = new Set<string>(LEX.common_word_names);
const stripEdge = (p: string) => { let a = 0, b = p.length; const ch = ".,;:()\"'"; while (a < b && ch.includes(p[a])) a++; while (b > a && ch.includes(p[b - 1])) b--; return p.slice(a, b); };

export function nameParts(v: string): string[] {
  const base = v.replace(POSSESSIVE, ""), parts: string[] = [];
  for (const raw of base.split(/[ \t\n\r\f\v,]+/)) {
    const p = stripEdge(raw).replace(POSSESSIVE, "");
    if (p) parts.push(p);
  }
  return parts;
}

/** Other ways a detected person name is written: its parts, ALL-CAPS forms, and initials. */
export function nameVariants(v: string): [string, string][] {
  const out: [string, string][] = [], seen = new Set([v]);
  const add = (s: string, why: string) => { if (!seen.has(s) && s.length >= 2) { seen.add(s); out.push([s, why]); } };
  const base = v.replace(POSSESSIVE, "");
  if (base.length >= 3) add(base, "possessive form of a detected name");
  const parts = nameParts(v).filter((p) => !STOP.has(p.toLowerCase()));
  for (const p of parts) if (p.length >= 3 && isUpper(p[0])) add(p, "part of a detected name");
  if (base.length >= 5 && base.toUpperCase() !== base) add(base.toUpperCase(), "detected name in capitals");
  for (const p of parts) if (p.length >= 4 && isUpper(p[0]) && p.toUpperCase() !== p && !COMMON.has(p.toLowerCase())) add(p.toUpperCase(), "part of a detected name in capitals");
  const alpha = parts.filter((p) => p.length >= 2 && p[0] >= "A" && p[0] <= "Z" && Array.from(p).every((c) => isLetter(c) || c === "-" || c === "'"));
  if (alpha.length >= 2) {
    const f = alpha[0], l = alpha[alpha.length - 1];
    for (const s of [`${f[0]}. ${l}`, `${f[0]}.${l}`, `${f[0]} ${l}`]) add(s, "initial + surname of a detected name");
    const ini = alpha.map((p) => p[0]).join("");
    if (ini.length >= 2 && ini.length <= 4) add(ini, "initials of a detected name");
  }
  return out;
}

const EMAIL = /(?<![\w.+-])[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}/g, HANDLE = /[A-Za-z0-9._-]+/g;

/** Redact every other occurrence of each detected value, plus the coreferent forms of person names. */
export function propagate(text: string, spans: Span[], minLen = 3): Span[] {
  const extra: Span[] = [], seen = new Set<string>(), handleParts: string[] = [];
  for (const sp of spans) {
    const v = text.slice(sp.start, sp.end), key = sp.type + "\u0000" + v;
    if (v.length < minLen || seen.has(key)) continue;
    seen.add(key);
    for (const [a, b] of occurrences(text, v)) extra.push(mk(a, b, sp.type, "propagated", null, sp.label, ["same value as another finding"], ["propagated"]));
    if (sp.type === "NAME") {
      for (const [s, why] of nameVariants(v)) for (const [a, b] of occurrences(text, s)) extra.push(mk(a, b, "NAME", "propagated", null, sp.label, [why], ["propagated"]));
      for (const p of nameParts(v)) {
        const low = p.toLowerCase();
        if (p.length >= 5 && !STOP.has(low) && !COMMON.has(low) && Array.from(p).every(isLetter) && !handleParts.includes(low)) handleParts.push(low);
      }
    }
  }
  if (handleParts.length) {
    for (const m of text.matchAll(EMAIL)) {
      const local = m[0].split("@")[0].toLowerCase();
      if (handleParts.some((p) => local.includes(p))) extra.push(mk(m.index!, m.index! + m[0].length, "CONTACT", "propagated", null, "email", ["email address contains a detected name"], ["propagated"]));
    }
    for (const m of text.matchAll(HANDLE)) {
      let a = m.index!, b = a + m[0].length;
      while (a < b && "._-".includes(text[a])) a++;
      while (b > a && "._-".includes(text[b - 1])) b--;
      const tok = text.slice(a, b), low = tok.toLowerCase();
      if (/[0-9._]/.test(tok) && /[A-Za-z]/.test(tok) && handleParts.some((p) => low.includes(p)))
        extra.push(mk(a, b, "NAME", "propagated", null, "user_name", ["login or handle contains a detected name"], ["propagated"]));
    }
  }
  // existing findings keep their identity; propagated spans only add coverage (spans are sorted, non-overlapping)
  const covered = (x: Span) => {
    let lo = 0, hi = spans.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (spans[mid].start <= x.start) lo = mid + 1; else hi = mid; }
    return lo > 0 && spans[lo - 1].end >= x.end;
  };
  const fresh = extra.filter((x) => !covered(x));
  return fresh.length ? mergeSpans(text, [...spans, ...fresh]) : spans;
}

// ---------------------------------------------------------------- user terms + keep-last-4
export function applyTerms(text: string, spans: Span[], customTerms: string[], allowTerms: string[]): Span[] {
  const allow = new Set(allowTerms.filter((t) => normTerm(t)).map(normTerm));
  if (allow.size) spans = spans.filter((s) => !allow.has(normTerm(text.slice(s.start, s.end))));
  const extra: Span[] = [];
  let low = text.toLowerCase();
  if (low.length !== text.length) low = text;
  for (const raw of customTerms) {
    const t = normEdges(raw);
    if (t.length < 2) continue;
    const tl = t.toLowerCase();
    for (let i = low.indexOf(tl); i >= 0; i = low.indexOf(tl, i + t.length))
      extra.push(mk(i, i + t.length, "CUSTOM", "custom", null, "custom_term", ["matches one of your custom terms"], ["custom"]));
  }
  return extra.length ? mergeSpans(text, [...spans, ...extra]) : spans;
}
const normEdges = strip;

/** Shrink long financial identifiers so their last four digits stay visible; drop already-masked partials. */
export function keepLast4(text: string, spans: Span[]): Span[] {
  const out: Span[] = [], masked = new Set<string>(LEX.masked_rule_ids);
  for (const sp of spans) {
    if (sp.type !== "FIN_ID") { out.push(sp); continue; }
    if (sp.label && masked.has(sp.label)) continue;
    const v = text.slice(sp.start, sp.end);
    if (Array.from(v).filter(isDigit).length < 8) { out.push(sp); continue; }
    let k = 0, e = sp.end;
    while (e > sp.start && k < 4) {
      e--;
      if (isDigit(text[e])) k++;
      else if (!(text[e] === " " || text[e] === "-")) break;
    }
    if (k === 4) {
      let [a, b] = trimBounds(text, sp.start, e);
      while (b > a && (text[b - 1] === " " || text[b - 1] === "-")) b--;
      if (b > a) out.push(mk(a, b, sp.type, sp.source, sp.score ?? null, sp.label, [...(sp.why ?? []), "last 4 digits kept visible"], sp.sources ?? []));
    } else out.push(sp);
  }
  return out;
}

// ---------------------------------------------------------------- the whole post-processing chain
export function finalize(text: string, raw: Span[], opts: Partial<Options> = {}): Span[] {
  const o: Options = { ...DEFAULT_OPTIONS, ...opts };
  const allow = new Set(o.allowTerms.filter((t) => normTerm(t)).map(normTerm));
  const kept: Span[] = [];
  for (const sp of raw) {
    const [s, e] = trimBounds(text, sp.start, sp.end);
    if (e <= s || !aboveThreshold(sp, o)) continue;
    kept.push(mk(s, e, sp.type, sp.source, sp.score ?? null, sp.label, [...(sp.why ?? [])], [...(sp.sources ?? [])]));
  }
  const merged = mergeSpans(text, dropUnsupported(kept, o)).filter((sp) => passesFilters(text, sp, o, allow));
  let out = propagate(text, merged).filter((sp) => passesFilters(text, sp, o, allow));
  out = applyTerms(text, out, o.customTerms, o.allowTerms);
  if (o.keepLast4) out = keepLast4(text, out);
  const res: Span[] = [];
  for (const sp of out) {
    const [s, e] = trimBounds(text, sp.start, sp.end);
    if (e > s) res.push({ ...sp, start: s, end: e });
  }
  return res;
}

// ---------------------------------------------------------------- render / restore / leak check (redactd/vault.py)
export interface RenderResult { output: string; vault: Record<string, string>; /** [start, end) of each replacement in `output` */ marks: [number, number][] }

/** Replace each span. placeholder: reversible "[NAME_1]" (same value -> same placeholder); label: "[NAME]"; block: six full-block characters. */
export function render(text: string, spans: Span[], style: OutputStyle = "placeholder"): RenderResult {
  const merged = mergeSpans(text, spans);
  const out: string[] = [], vault: Record<string, string> = {}, counters: Record<string, number> = {}, seen = new Map<string, string>();
  const marks: [number, number][] = [];
  let last = 0, len = 0;
  for (const sp of merged) {
    const val = text.slice(sp.start, sp.end), key = sp.type + "\u0000" + val;
    let ph = seen.get(key);
    if (!ph) { counters[sp.type] = (counters[sp.type] ?? 0) + 1; ph = `[${sp.type}_${counters[sp.type]}]`; seen.set(key, ph); vault[ph] = val; }
    const rep = style === "placeholder" ? ph : style === "label" ? `[${sp.type}]` : "█".repeat(6);
    const before = text.slice(last, sp.start);
    out.push(before, rep); len += before.length; marks.push([len, len + rep.length]); len += rep.length; last = sp.end;
  }
  out.push(text.slice(last));
  return { output: out.join(""), vault, marks };
}

export function restore(text: string, vault: Record<string, string>): string {
  return text.replace(/\[[A-Z_]+_[0-9a-f]+\]/g, (m) => (Object.prototype.hasOwnProperty.call(vault, m) ? vault[m] : m));
}

/** Values that were redacted but still occur in the output. `kept` lists output regions the user chose to keep
 *  (rejected findings); a value inside one of those is intentional, not a leak. */
export function leakCheck(output: string, values: string[], kept: [number, number][] = []): string[] {
  const leaks: string[] = [];
  for (const v of new Set(values)) {
    if (v.length < 3) continue;
    if (occurrences(output, v).some(([a, b]) => !kept.some(([ks, ke]) => a >= ks && b <= ke))) leaks.push(v);
  }
  return leaks;
}

// ---------------------------------------------------------------- offsets: API (code points) <-> JS (UTF-16)
/** Convert spans between Unicode code-point offsets (Python) and UTF-16 offsets (JS). No-op for BMP-only text. */
export function convertOffsets<T extends { start: number; end: number }>(text: string, spans: T[], to: "utf16" | "codepoint"): T[] {
  if (!/[\ud800-\udbff]/.test(text)) return spans;
  const cpToU16: number[] = [], u16ToCp = new Array<number>(text.length + 1);
  let cp = 0;
  for (let i = 0; i < text.length; cp++) {
    cpToU16.push(i); u16ToCp[i] = cp;
    const pair = text.charCodeAt(i) >= 0xd800 && text.charCodeAt(i) <= 0xdbff && i + 1 < text.length && text.charCodeAt(i + 1) >= 0xdc00 && text.charCodeAt(i + 1) <= 0xdfff;
    if (pair) u16ToCp[i + 1] = cp;
    i += pair ? 2 : 1;
  }
  cpToU16.push(text.length); u16ToCp[text.length] = cp;
  const f = to === "utf16" ? (x: number) => cpToU16[Math.min(x, cpToU16.length - 1)] : (x: number) => u16ToCp[Math.min(x, text.length)];
  return spans.map((s) => ({ ...s, start: f(s.start), end: f(s.end) }));
}
