// Exported redaction report (task D5): what was done, with counts only. It never contains a redacted value,
// a custom term or any document text, so it is safe to file next to the redacted copy.
import { TYPE_INFO, TYPES } from "./labels.ts";
import type { Options, OutputStyle, PiiType, ReviewSpan } from "./types.ts";

export interface RedactionReport {
  tool: "redactd"; generated: string; document: { characters: number; extension: string };
  processing: { where: "server" | "device"; mode: string; seconds: number | null; versions: Record<string, string> };
  policy: { preset: string; style: OutputStyle; reversible: boolean; keepLast4: boolean; excludedTypes: string[]; publicBodiesKept: boolean; reportingPeriodsKept: boolean; customTerms: number; allowTerms: number };
  findings: { total: number; redacted: number; kept: number; byType: Record<string, { found: number; redacted: number; kept: number }>; addedByYou: number };
  leakCheck: { passed: boolean; valuesStillPresent: number };
}

export function buildReport(a: { chars: number; fileName: string; where: "server" | "device"; mode: string; ms: number | null; versions: Record<string, string>;
  presetName: string; style: OutputStyle; options: Options; spans: ReviewSpan[]; leaks: number; now?: Date }): RedactionReport {
  const byType: RedactionReport["findings"]["byType"] = {};
  for (const s of a.spans) { const x = (byType[s.type] ??= { found: 0, redacted: 0, kept: 0 }); x.found++; if (s.accepted) x.redacted++; else x.kept++; }
  const ext = /\.[A-Za-z0-9]{1,8}$/.exec(a.fileName)?.[0] ?? "";
  return {
    tool: "redactd", generated: (a.now ?? new Date()).toISOString(), document: { characters: a.chars, extension: ext },
    processing: { where: a.where, mode: a.mode, seconds: a.ms === null ? null : Math.round(a.ms / 100) / 10, versions: a.versions },
    policy: { preset: a.presetName, style: a.style, reversible: a.style === "placeholder", keepLast4: a.options.keepLast4, excludedTypes: [...a.options.excludeTypes],
      publicBodiesKept: a.options.orgAllowlist, reportingPeriodsKept: a.options.dropNonpersonalDates, customTerms: a.options.customTerms.length, allowTerms: a.options.allowTerms.length },
    findings: { total: a.spans.length, redacted: a.spans.filter((s) => s.accepted).length, kept: a.spans.filter((s) => !s.accepted).length, byType,
      addedByYou: a.spans.filter((s) => s.source === "manual" || s.source === "custom").length },
    leakCheck: { passed: a.leaks === 0, valuesStillPresent: a.leaks },
  };
}

export function reportMarkdown(r: RedactionReport): string {
  const rows = TYPES.filter((t) => r.findings.byType[t]).map((t) => { const x = r.findings.byType[t]; return `| ${TYPE_INFO[t as PiiType].label} | ${x.found} | ${x.redacted} | ${x.kept} |`; });
  return [
    "# Redaction report", "",
    `Generated ${r.generated} by redactd. This report contains counts only: no redacted values and no document text.`, "",
    "## Document", "", `- Characters: ${r.document.characters.toLocaleString("en")}`, `- File type: ${r.document.extension || "(pasted text)"}`, "",
    "## Processing", "", `- Where: ${r.processing.where === "device" ? "on this device (nothing uploaded)" : "redactd server (in memory, not stored)"}`,
    `- Mode: ${r.processing.mode}`, `- Time: ${r.processing.seconds ?? "n/a"} s`, `- Versions: ${Object.entries(r.processing.versions).map(([k, v]) => `${k} ${v}`).join(", ") || "n/a"}`, "",
    "## Policy", "", `- Preset: ${r.policy.preset}`, `- Output: ${r.policy.style}${r.policy.reversible ? " (reversible with the restore key)" : " (not reversible)"}`,
    `- Keep last 4 digits: ${r.policy.keepLast4 ? "yes" : "no"}`, `- Categories not redacted: ${r.policy.excludedTypes.join(", ") || "none"}`,
    `- Public bodies kept: ${r.policy.publicBodiesKept ? "yes" : "no"}`, `- Reporting periods kept: ${r.policy.reportingPeriodsKept ? "yes" : "no"}`,
    `- Custom terms: ${r.policy.customTerms}, allow-list terms: ${r.policy.allowTerms}`, "",
    "## Findings", "", `${r.findings.redacted} of ${r.findings.total} findings redacted; ${r.findings.kept} kept by the reviewer; ${r.findings.addedByYou} added by the reviewer.`, "",
    "| Category | Found | Redacted | Kept |", "|---|---:|---:|---:|", ...rows, "",
    "## Leak check", "", r.leakCheck.passed ? "Passed: no redacted value appears anywhere in the output." : `FAILED: ${r.leakCheck.valuesStillPresent} redacted value(s) still appear in the output.`, "",
  ].join("\n");
}

/** "statement.md" -> "statement.redacted.md"; no extension -> ".txt". */
export function redactedName(fileName: string): string {
  const m = /^(.*?)(\.[A-Za-z0-9]{1,8})?$/.exec(fileName || "document.txt")!;
  const ext = (m[2] ?? ".txt").toLowerCase();
  const textual = [".txt", ".md", ".csv", ".tsv", ".json", ".jsonl", ".xml", ".log", ".eml", ".yaml", ".yml", ".html", ".htm"].includes(ext);
  return `${m[1] || "document"}.redacted${textual ? ext : ".txt"}`;
}
export const baseName = (fileName: string) => (fileName || "document").replace(/\.[A-Za-z0-9]{1,8}$/, "") || "document";
