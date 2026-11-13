// Runs the browser rule engine and post-processing on a JSONL file of documents and prints results as JSONL.
// Used by tests/test_rule_parity.py. Offsets are converted to Unicode code points to compare with Python.
//   node --experimental-strip-types scripts/parity.ts in.jsonl out.jsonl
import { readFileSync, writeFileSync } from "node:fs";
import { detectRules } from "../lib/rules.ts";
import { convertOffsets, finalize, render, leakCheck } from "../lib/redact.ts";
import type { Span } from "../lib/types.ts";

const [inp, outp] = process.argv.slice(2);
const key = (s: Span) => [s.start, s.end, s.type, s.label ?? null];
const lines = readFileSync(inp, "utf8").split("\n").filter(Boolean).map((l) => {
  const d = JSON.parse(l) as { id: string; text: string; raw: Span[]; options?: object };
  const rules = detectRules(d.text);
  const raw = [...rules, ...convertOffsets(d.text, d.raw, "utf16")];
  const fin = finalize(d.text, raw, d.options ?? {});
  const r = render(d.text, fin);
  return JSON.stringify({
    id: d.id, rules: convertOffsets(d.text, rules, "codepoint").map(key), final: convertOffsets(d.text, fin, "codepoint").map(key),
    output: r.output, leaks: leakCheck(r.output, Object.values(r.vault)).length,
  });
});
writeFileSync(outp, lines.join("\n") + "\n");
