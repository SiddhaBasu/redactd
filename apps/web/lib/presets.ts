// Redaction policies (task D4). A preset is plain data: an output style plus detection options. Unit-tested in
// presets.test.ts. Custom terms and the allow-list are per user, stored in this browser only (localStorage) and
// applied on the device; they are never sent to the server.
import { DEFAULT_OPTIONS, type Options, type OutputStyle, type PiiType } from "./types.ts";

export interface Preset { id: string; name: string; summary: string; style: OutputStyle; options: Partial<Options> }
export const PRESETS: Preset[] = [
  { id: "standard", name: "Standard", summary: "Reversible placeholders. Redacts every category; keeps public bodies and reporting periods.",
    style: "placeholder", options: { excludeTypes: [], orgAllowlist: true, dropNonpersonalDates: true } },
  { id: "llm", name: "Share with LLM", summary: "Reversible placeholders. Keeps organisations and dates so the text still makes sense to a model.",
    style: "placeholder", options: { excludeTypes: ["ORG", "DATE"], orgAllowlist: true, dropNonpersonalDates: true } },
  { id: "legal", name: "Legal production", summary: "Solid blocks, not reversible. Redacts everything, including public bodies and all dates.",
    style: "block", options: { excludeTypes: [], orgAllowlist: false, dropNonpersonalDates: false } },
  { id: "analytics", name: "Analytics", summary: "Category labels like [NAME], not reversible. Keeps dates for time-series work.",
    style: "label", options: { excludeTypes: ["DATE"], orgAllowlist: true, dropNonpersonalDates: true } },
];
export const presetById = (id: string) => PRESETS.find((p) => p.id === id) ?? PRESETS[0];

export interface UserPolicy { presetId: string; keepLast4: boolean; customTerms: string[]; allowTerms: string[]; sensitivity: number }
export const DEFAULT_POLICY: UserPolicy = { presetId: "standard", keepLast4: false, customTerms: [], allowTerms: [], sensitivity: DEFAULT_OPTIONS.sensitivity };

/** Detection options for a preset plus the user's own settings. */
export function optionsFor(policy: UserPolicy): Options {
  const p = presetById(policy.presetId);
  return { ...DEFAULT_OPTIONS, ...p.options, excludeTypes: [...(p.options.excludeTypes ?? [])] as PiiType[], sensitivity: policy.sensitivity,
    keepLast4: policy.keepLast4, customTerms: cleanTerms(policy.customTerms), allowTerms: cleanTerms(policy.allowTerms) };
}
export const styleFor = (policy: UserPolicy): OutputStyle => presetById(policy.presetId).style;

export function cleanTerms(terms: string[]): string[] {
  const seen = new Set<string>(), out: string[] = [];
  for (const t of terms) { const v = t.trim(); const k = v.toLowerCase(); if (v.length >= 2 && !seen.has(k)) { seen.add(k); out.push(v); } }
  return out.slice(0, 500);
}
export const parseTerms = (raw: string) => cleanTerms(raw.split(/[\n,;]+/));

const KEY = "redactd.policy.v1";
export function loadPolicy(): UserPolicy {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!raw || typeof raw !== "object") return DEFAULT_POLICY;
    return { presetId: presetById(String(raw.presetId)).id, keepLast4: !!raw.keepLast4, customTerms: cleanTerms(Array.isArray(raw.customTerms) ? raw.customTerms.map(String) : []),
      allowTerms: cleanTerms(Array.isArray(raw.allowTerms) ? raw.allowTerms.map(String) : []),
      sensitivity: typeof raw.sensitivity === "number" && raw.sensitivity >= 0.1 && raw.sensitivity <= 0.8 ? raw.sensitivity : DEFAULT_POLICY.sensitivity };
  } catch { return DEFAULT_POLICY; }
}
export function savePolicy(p: UserPolicy) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private mode: keep in memory only */ } }
