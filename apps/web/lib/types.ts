export type PiiType = "NAME" | "CONTACT" | "ADDRESS" | "GOV_ID" | "FIN_ID" | "SECRET" | "NETWORK" | "DATE" | "ORG" | "DEMOGRAPHIC" | "CUSTOM";
export type DetectMode = "rules" | "standard" | "thorough";
export type OutputStyle = "placeholder" | "label" | "block";

/** A finding. Offsets are UTF-16 code units in the browser (JS string indices). The API speaks Unicode code points;
 *  lib/api.ts converts at the boundary. */
export interface Span {
  start: number;
  end: number;
  type: PiiType;
  /** "rules" | "openmed" | "gliner" | "distilled" | "propagated" | "manual" | "custom" */
  source: string;
  score?: number | null;
  /** rule id or the model's fine label */
  label?: string | null;
  why?: string[];
  sources?: string[];
}
export interface ReviewSpan extends Span { id: number; accepted: boolean }

/** Mirrors redactd.post.Options */
export interface Options {
  sensitivity: number;
  thresholds?: Record<string, Record<string, number>> | null;
  soloThresholds?: Record<string, Record<string, number>> | null;
  orgAllowlist: boolean;
  dropNonpersonalDates: boolean;
  keepLast4: boolean;
  customTerms: string[];
  allowTerms: string[];
  excludeTypes: PiiType[];
}
export const DEFAULT_OPTIONS: Options = {
  sensitivity: 0.35, thresholds: null, orgAllowlist: true, dropNonpersonalDates: true, keepLast4: false,
  customTerms: [], allowTerms: [], excludeTypes: [],
};

export type WorkerRequest = { kind: "detect"; text: string; mode: DetectMode; sensitivity: number };
export type WorkerResponse =
  | { kind: "progress"; stage: string; pct: number }
  | { kind: "result"; spans: Span[]; ms: number }
  | { kind: "error"; message: string };
