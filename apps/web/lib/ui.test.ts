import { test } from "node:test";
import assert from "node:assert/strict";
import { firstSpanAfter, rowAt, wrapRows } from "./layout.ts";
import { countsByType, emptyReview, needsReview, rejectedKeys, reviewReducer, searchSpans, type ReviewState } from "./review.ts";
import { PRESETS, DEFAULT_POLICY, optionsFor, parseTerms, presetById, styleFor } from "./presets.ts";
import { buildReport, redactedName, reportMarkdown } from "./report.ts";
import { detectRules } from "./rules.ts";
import { finalize, render } from "./redact.ts";
import { SAMPLE_TEXT } from "./sample.ts";
import type { Span } from "./types.ts";

const span = (text: string, value: string, type: Span["type"], score: number | null = 0.9, from = 0): Span => {
  const start = text.indexOf(value, from);
  return { start, end: start + value.length, type, source: score === null ? "rules" : "gliner", score, label: null, why: [], sources: [score === null ? "rules" : "gliner"] };
};

// ---------------------------------------------------------------- layout
test("wrapRows covers every character exactly once and never exceeds the width", () => {
  const text = "short\n" + "word ".repeat(60) + "\n\n" + "x".repeat(205) + "\r\nwide 漢字漢字漢字漢字漢字 😀😀😀😀😀😀 end\nlast";
  for (const cols of [10, 37, 80]) {
    const rows = wrapRows(text, cols);
    let rebuilt = "";
    for (let i = 0; i < rows.count; i++) {
      assert.ok(rows.end[i] >= rows.start[i]);
      const seg = text.slice(rows.start[i], rows.end[i]);
      assert.ok(!seg.includes("\n"));
      assert.ok([...seg].length <= cols, `row ${i} too long at ${cols}`);
      const next = i + 1 < rows.count ? rows.start[i + 1] : text.length;
      rebuilt += seg + text.slice(rows.end[i], next);
      assert.ok(/^\r?\n?$/.test(text.slice(rows.end[i], next)), "only line breaks may sit between rows");
    }
    assert.equal(rebuilt, text);
  }
});
test("wrapRows handles a 1 MB document quickly; rowAt and firstSpanAfter are binary searches", () => {
  const big = (SAMPLE_TEXT + "\n").repeat(Math.ceil(1_000_000 / (SAMPLE_TEXT.length + 1)));
  const t0 = performance.now(); const rows = wrapRows(big, 100); const ms = performance.now() - t0;
  assert.ok(rows.count > 10_000 && ms < 500, `${rows.count} rows in ${ms.toFixed(0)} ms`);
  for (const off of [0, 1, 5000, big.length - 1]) { const r = rowAt(rows, off); assert.ok(rows.start[r] <= off && (r + 1 === rows.count || rows.start[r + 1] > off)); }
  const spans = [{ start: 5, end: 9 }, { start: 20, end: 30 }, { start: 30, end: 31 }];
  assert.deepEqual([0, 5, 9, 25, 30, 31].map((o) => firstSpanAfter(spans, o)), [0, 0, 1, 1, 2, 3]);
});

// ---------------------------------------------------------------- review reducer
const T = "Priya Raman paid Daniel Okafor. Priya Raman called Acme Bank twice.";
const load = (): ReviewState => reviewReducer(emptyReview, { type: "load", text: T, spans: [
  span(T, "Priya Raman", "NAME", 0.95), span(T, "Daniel Okafor", "NAME", 0.4), span(T, "Priya Raman", "NAME", 0.95, 20), span(T, "Acme Bank", "ORG", null)] });
const on = (s: ReviewState) => s.spans.map((x) => x.accepted);

test("review: toggle one, toggle every occurrence of a value, bulk by type, undo and redo", () => {
  let s = load();
  assert.deepEqual(on(s), [true, true, true, true]); assert.equal(s.focus, 0);
  s = reviewReducer(s, { type: "toggle", id: 1 }); assert.deepEqual(on(s), [true, false, true, true]);
  s = reviewReducer(s, { type: "toggleValue", id: 0 }); assert.deepEqual(on(s), [false, false, false, true]);
  s = reviewReducer(s, { type: "setType", piiType: "NAME", accepted: true }); assert.deepEqual(on(s), [true, true, true, true]);
  s = reviewReducer(s, { type: "setValue", value: "Acme Bank", accepted: false }); assert.deepEqual(on(s), [true, true, true, false]);
  s = reviewReducer(s, { type: "undo" }); assert.deepEqual(on(s), [true, true, true, true]);
  s = reviewReducer(s, { type: "undo" }); assert.deepEqual(on(s), [false, false, false, true]);
  s = reviewReducer(s, { type: "redo" }); assert.deepEqual(on(s), [true, true, true, true]);
  for (let i = 0; i < 10; i++) s = reviewReducer(s, { type: "undo" });
  assert.deepEqual(on(s), [true, true, true, true]); assert.equal(s.past.length, 0);
  const same = reviewReducer(s, { type: "setType", piiType: "NAME", accepted: true });
  assert.equal(same, s, "a no-op does not create an undo step");
});
test("review: keyboard navigation wraps and can be restricted to a filter", () => {
  let s = load();
  s = reviewReducer(s, { type: "move", dir: 1 }); assert.equal(s.focus, 1);
  s = reviewReducer(s, { type: "move", dir: -1 }); s = reviewReducer(s, { type: "move", dir: -1 }); assert.equal(s.focus, 3);
  s = reviewReducer(s, { type: "move", dir: 1, among: (x) => (x.score ?? 1) < 0.7 }); assert.equal(s.focus, 1);
});
test("review: manual additions replace what they overlap, search-and-redact finds every match", () => {
  let s = load();
  const found = searchSpans(T, "priya", "CUSTOM"); assert.equal(found.length, 2);
  s = reviewReducer(s, { type: "add", spans: [{ start: 17, end: 30, type: "NAME", source: "manual" }] });
  assert.equal(s.spans.length, 4); assert.equal(T.slice(s.spans[s.focus].start, s.spans[s.focus].end), "Daniel Okafor"); assert.equal(s.spans[s.focus].source, "manual");
  s = reviewReducer(s, { type: "add", spans: searchSpans(T, "twice", "CUSTOM") }); assert.equal(s.spans.length, 5);
  s = reviewReducer(s, { type: "remove", id: 4 }); assert.equal(s.spans.length, 4);
  s = reviewReducer(s, { type: "undo" }); s = reviewReducer(s, { type: "undo" }); s = reviewReducer(s, { type: "undo" });
  assert.equal(s.spans[1].source, "gliner");
});
test("review: decisions survive a re-scan; needs-review queue is lowest confidence first; counts", () => {
  let s = reviewReducer(load(), { type: "toggleValue", id: 0 });
  const re = reviewReducer(emptyReview, { type: "load", text: T, spans: s.spans, rejected: rejectedKeys(s) });
  assert.deepEqual(on(re), [false, true, false, true]);
  assert.deepEqual(needsReview(load().spans).map((x) => T.slice(x.start, x.end)), ["Daniel Okafor"]);
  assert.deepEqual(countsByType(s.spans), { NAME: { n: 3, on: 1 }, ORG: { n: 1, on: 1 } });
});

// ---------------------------------------------------------------- presets (D4)
const raw = (): Span[] => { const t = SAMPLE_TEXT; return [...detectRules(t), span(t, "Priya Raman", "NAME"), span(t, "Daniel Okafor", "NAME"), span(t, "Boise", "ADDRESS"), span(t, "52-year-old", "DEMOGRAPHIC")]; };
const run = (presetId: string, extra = {}) => { const policy = { ...DEFAULT_POLICY, presetId, ...extra }; const spans = finalize(SAMPLE_TEXT, raw(), optionsFor(policy)); return { spans, out: render(SAMPLE_TEXT, spans, styleFor(policy)).output }; };

test("preset: Share with LLM keeps organisations and dates, uses reversible placeholders", () => {
  const { out } = run("llm");
  assert.ok(out.includes("Royal Bank of Canada") && out.includes("March 3, 2026") && out.includes("Northgate Capital Partners"));
  assert.match(out, /\[NAME_1\]/); assert.ok(!out.includes("Priya") && !out.includes("0049821774471") && !out.includes("123-45-6789"));
});
test("preset: Legal production blocks everything", () => {
  const { out, spans } = run("legal");
  assert.ok(!/\[[A-Z_]+(_\d+)?\]/.test(out) && out.includes("█".repeat(6)));
  for (const v of ["Royal Bank of Canada", "March 3, 2026", "Priya", "4111", "Boise"]) assert.ok(!out.includes(v), v);
  assert.ok(spans.some((s) => s.type === "ORG") && spans.some((s) => s.type === "DATE"));
  assert.equal(optionsFor({ ...DEFAULT_POLICY, presetId: "legal" }).orgAllowlist, false);
});
test("preset: Analytics uses labels and keeps dates", () => {
  const { out } = run("analytics");
  assert.ok(out.includes("[NAME]") && out.includes("[FIN_ID]") && out.includes("March 3, 2026") && !out.includes("Royal Bank of Canada") && !/\[NAME_\d+\]/.test(out));
});
test("preset: Standard redacts every category; keep-last-4, custom terms and allow-list apply on top", () => {
  const std = run("standard").out;
  assert.ok(!std.includes("Royal Bank of Canada") && !std.includes("March 3, 2026"));
  const { out } = run("standard", { keepLast4: true, customTerms: ["wire"], allowTerms: ["boise"] });
  assert.ok(out.includes("4471 (routing") && out.includes("1111 was also") && !out.includes("0049821774471") && !out.includes("4111 1111 1111"));
  assert.ok(out.includes("Boise") && !/\bwire\b/i.test(out) && out.includes("[CUSTOM_1]"));
  assert.equal(presetById("nope").id, "standard"); assert.equal(PRESETS.length, 4);
  assert.deepEqual(parseTerms(" Falcon , falcon\nx\nProject Kestrel;"), ["Falcon", "Project Kestrel"]);
});

// ---------------------------------------------------------------- report (D5)
test("exported report has counts and versions but no values", () => {
  const policy = { ...DEFAULT_POLICY, customTerms: ["Northgate"] };
  const spans = finalize(SAMPLE_TEXT, raw(), optionsFor(policy)).map((s, id) => ({ ...s, id, accepted: id !== 0 }));
  const r = buildReport({ chars: SAMPLE_TEXT.length, fileName: "statement.MD", where: "server", mode: "thorough", ms: 1234, versions: { rules: "abc" }, presetName: "Standard",
    style: "placeholder", options: optionsFor(policy), spans, leaks: 0, now: new Date("2026-11-13T00:00:00Z") });
  const dump = JSON.stringify(r) + reportMarkdown(r);
  for (const v of ["Priya", "Raman", "Okafor", "4111", "0049821774471", "Northgate", "Boise", "123-45-6789"]) assert.ok(!dump.includes(v), v);
  assert.equal(r.findings.total, spans.length); assert.equal(r.findings.kept, 1); assert.equal(r.policy.customTerms, 1); assert.equal(r.leakCheck.passed, true);
  assert.match(reportMarkdown(r), /\| Financial IDs \| \d+ \| \d+ \| \d+ \|/); assert.equal(r.processing.seconds, 1.2); assert.equal(r.generated, "2026-11-13T00:00:00.000Z");
});
test("download name keeps the original extension", () => {
  assert.equal(redactedName("statement.md"), "statement.redacted.md"); assert.equal(redactedName("notes.txt"), "notes.redacted.txt");
  assert.equal(redactedName("data.CSV"), "data.redacted.csv"); assert.equal(redactedName("letter.docx"), "letter.redacted.txt"); assert.equal(redactedName(""), "document.redacted.txt");
});
