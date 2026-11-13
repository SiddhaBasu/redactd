export type PiiType =
  | "NAME" | "CONTACT" | "ADDRESS" | "GOV_ID" | "FIN_ID" | "SECRET"
  | "NETWORK" | "DATE" | "ORG" | "DEMOGRAPHIC";

export type Source = "rules" | "openmed" | "gliner" | "manual" | "propagated";

export interface Span {
  start: number;
  end: number;
  type: PiiType;
  source: Source;
  score?: number;
}

export interface ReviewSpan extends Span {
  id: number;
  accepted: boolean;
}

export type OutputStyle = "block" | "label" | "placeholder";
export type DetectMode = "rules" | "standard" | "thorough";

export type WorkerRequest = { kind: "detect"; text: string; mode: DetectMode; sensitivity: number };
export type WorkerResponse =
  | { kind: "progress"; stage: string; pct: number }
  | { kind: "result"; spans: Span[]; ms: number }
  | { kind: "error"; message: string };
