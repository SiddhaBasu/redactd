// Browser rule engine. Executes the rule table generated from redactd/rules.py (rules.generated.json), so the
// Python and TypeScript pipelines cannot drift: tests/test_rule_parity.py runs both on the same documents.
//
// Portability contract (see redactd/rules.py): Python compiles with re.ASCII. JS \w \d \b are already ASCII; \s is
// not, so toJs() rewrites \s to the ASCII whitespace set. Both engines match against text + "\n" so patterns can
// use \n as "end of text" without `$`.
import spec from "./rules.generated.json" with { type: "json" };
import type { PiiType, Span } from "./types.ts";

export const SPEC = spec;
const NL = String.fromCharCode(10);
const WS = " \\t\\n\\r\\f\\v";

/** Rewrite \s / \S so they mean ASCII whitespace, as in Python's re.ASCII. */
export function toJs(pattern: string): string {
  let out = "", inClass = false;
  for (let i = 0; i < pattern.length; i++) {
    const c = pattern[i];
    if (c === "\\") {
      const n = pattern[++i];
      if (n === "s") out += inClass ? WS : `[${WS}]`;
      else if (n === "S") { if (inClass) throw new Error("\\S inside a character class is not portable"); out += `[^${WS}]`; }
      else out += c + n;
      continue;
    }
    if (c === "[" && !inClass) inClass = true;
    else if (c === "]" && inClass) inClass = false;
    out += c;
  }
  return out;
}

// ---------------------------------------------------------------- validators (mirror redactd/rules.py)
const digitsOf = (v: string) => Array.from(v).filter((c) => c >= "0" && c <= "9").map(Number);
export function luhn(v: string): boolean {
  const d = digitsOf(v);
  if (d.length < 13 || d.length > 19) return false;
  let s = 0;
  for (let i = 0; i < d.length; i++) {
    let x = d[d.length - 1 - i];
    if (i % 2) x = x > 4 ? x * 2 - 9 : x * 2;
    s += x;
  }
  return s % 10 === 0;
}
export function aba(v: string): boolean {
  if (!/^[0-9]{9}$/.test(v)) return false;
  const d = digitsOf(v);
  return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 === 0;
}
export function ibanOk(v: string): boolean {
  const s = v.replace(/[ \-]/g, "").toUpperCase();
  if (s.length < 15 || s.length > 34 || !/^[A-Z]{2}[0-9]{2}[A-Z0-9]+$/.test(s)) return false;
  let rem = 0;
  for (const c of s.slice(4) + s.slice(0, 4)) for (const ch of parseInt(c, 36).toString()) rem = (rem * 10 + Number(ch)) % 97;
  return rem === 1;
}
export const hasDigit = (v: string) => /[0-9]/.test(v);
export function orgShape(v: string): boolean {
  const words = v.split(/[ \t\n\r\f\v]+/).filter(Boolean);
  return words.length >= 2 || (v.toUpperCase() === v && v.toLowerCase() !== v);
}
const IBAN_COUNTRIES = new Set<string>(spec.iban_countries);
const GROUP_SEP = " -" + NL;
/** IBAN with odd spacing / hyphens / a line break / lower case: the pattern over-matches into the following
 *  words, so return the length of the longest prefix (cut where a group ends) that passes mod-97. */
export function ibanPrefix(v: string): number | false {
  if (!IBAN_COUNTRIES.has(v.slice(0, 2).toUpperCase())) return false;
  const n = v.length;
  for (let end = n; end > 14; end--) {
    if (end < n && (!GROUP_SEP.includes(v[end]) || GROUP_SEP.includes(v[end - 1]))) continue;
    const p = v.slice(0, end);
    if (p.toUpperCase() !== p && p.toLowerCase() !== p) continue;
    if (ibanOk(p.split(NL).join(""))) return end;
  }
  return false;
}
const digitCount = (lo: number, hi: number) => (v: string) => { const n = digitsOf(v).length; return n >= lo && n <= hi; };
const BULLET = String.fromCharCode(0x2022);
export const maskedIban = (v: string) => (v.includes("*") || v.includes(BULLET)) && hasDigit(v);
/** Two decimals in latitude/longitude range, with 6+ decimal places, a hemisphere letter or a sign (plain pairs are usually FX rates). */
export function coords(v: string): boolean {
  const nums = v.match(/[-+]?[0-9]{1,3}\.[0-9]+/g) ?? [];
  if (nums.length !== 2 || Math.abs(Number(nums[0])) > 90 || Math.abs(Number(nums[1])) > 180) return false;
  return nums.some((x) => x.split(".")[1].length >= 6) || /[NSEW]/.test(v) || v.includes("-");
}
const SCHEMA_URL = new RegExp("^(?:" + spec.schema_url_pattern + ")", "i");
/** XML namespace and schema URLs (w3.org, xbrl.org, fpml.org ...) are boilerplate, not contact details. */
export const personalUrl = (v: string) => !SCHEMA_URL.test(v + NL);
/** A long token is only key-like if it mixes letters and digits. */
export const mixedAlnum = (v: string) => hasDigit(v) && /[A-Za-z]/.test(v);
const VALIDATORS: Record<string, (v: string) => boolean | number> = {
  coords, personal_url: personalUrl, mixed_alnum: mixedAlnum, luhn, aba, iban: ibanOk, iban_prefix: ibanPrefix, has_digit: hasDigit, org_shape: orgShape, masked_iban: maskedIban,
  digits_8_15: digitCount(8, 15), digits_9_15: digitCount(9, 15), digits_9_11: digitCount(9, 11),
};
const REFINERS = new Set<string>(spec.refiners);

// ---------------------------------------------------------------- engine
type Rule = { id: string; type: PiiType; rx: RegExp; group: number; validate?: (v: string) => boolean | number; why: string };
const COMPILED: Rule[] = (spec.rules as { id: string; type: string; pattern: string; flags: string; validator: string | null; why: string }[]).map((r) => {
  const rx = new RegExp(toJs(r.pattern), "gd" + (r.flags.includes("i") ? "i" : ""));
  const groups = new RegExp(toJs(r.pattern) + "|").exec("")!.length - 1;
  if (groups > 1) throw new Error(`rule ${r.id}: more than one capture group`);
  if (r.validator && !VALIDATORS[r.validator]) throw new Error(`rule ${r.id}: unknown validator ${r.validator}`);
  return { id: r.id, type: r.type as PiiType, rx, group: groups, validate: r.validator ? VALIDATORS[r.validator] : undefined, why: r.why };
});
export const RULE_WHY: Record<string, string> = Object.fromEntries(COMPILED.map((r) => [r.id, r.why]));
export const RULES_VERSION: string = spec.version;

/** All rule matches in rule-table order (same order as redactd.rules.detect_detailed). */
export function detectRules(text: string): Span[] {
  const out: Span[] = [];
  const src = text + NL, n = text.length;
  for (const r of COMPILED) {
    const refiner = REFINERS.has(r.id);
    let pos = 0;
    while (pos <= n) {
      r.rx.lastIndex = pos;
      const m = r.rx.exec(src) as (RegExpExecArray & { indices: ([number, number] | undefined)[] }) | null;
      if (!m) break;
      pos = Math.max(m.indices[0]![1], m.index + 1);
      const idx = m.indices[r.group];
      if (!idx) continue;
      const s = idx[0];
      let e = Math.min(idx[1], n);
      if (e <= s) continue;
      if (r.validate) {
        const ok = r.validate(src.slice(s, e));   // false = reject, true = keep, number = keep only that many characters
        if (!ok) { if (refiner) pos = m.index + 1; continue; }   // the pattern over-matches; a real value may start inside it
        if (ok !== true) { e = s + ok; pos = Math.max(e, m.index + 1); }
      }
      out.push({ start: s, end: e, type: r.type, source: "rules", score: null, label: r.id, why: [r.why], sources: ["rules"] });
    }
  }
  return out;
}
