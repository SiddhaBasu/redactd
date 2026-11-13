import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { detectRules, luhn, aba, ibanOk, toJs } from "./rules.ts";
import { convertOffsets, finalize, keepLast4, leakCheck, mergeSpans, nameVariants, occurrences, propagate, render, restore, trimBounds } from "./redact.ts";
import { openVault, passwordStrength, sealVault } from "./vault.ts";
import type { Span } from "./types.ts";

const DOC = readFileSync(new URL("../../../tests/fixtures/wire_recall.txt", import.meta.url), "utf8");
const sp = (text: string, value: string, type: Span["type"], source = "openmed"): Span => {
  const start = text.indexOf(value);
  return { start, end: start + value.length, type, source, score: 0.9, label: null, why: [], sources: [source] };
};
const values = (text: string, spans: Span[]) => spans.map((s) => text.slice(s.start, s.end));

test("validators", () => {
  assert.ok(luhn("4111 1111 1111 1111")); assert.ok(!luhn("4111 1111 1111 1112"));
  assert.ok(aba("021000021")); assert.ok(!aba("021000022"));
  assert.ok(ibanOk("GB82 WEST 1234 5698 7654 32")); assert.ok(!ibanOk("GB82 WEST 1234 5698 7654 33"));
});

test("\\s is rewritten to ASCII whitespace", () => {
  assert.equal(toJs("a\\sb[^\\s<]"), "a[ \\t\\n\\r\\f\\v]b[^ \\t\\n\\r\\f\\v<]");
  assert.throws(() => toJs("[\\S]"));
});

test("rules find the structured identifiers in the fixture", () => {
  const found = values(DOC, detectRules(DOC));
  for (const v of ["priya.raman@northgate-mail.com", "021000021", "GB82WEST12345698765432", "4111 1111 1111 1111", "123-45-6789", "(415) 555-0199", "Royal Bank of Canada"])
    assert.ok(found.includes(v), `missing ${v}`);
});

test("trim never strips brackets", () => {
  const t = " (415) 555-0199, ";
  assert.deepEqual(trimBounds(t, 0, t.length), [1, 15]);
});

test("occurrences respect word boundaries for letters and short numbers", () => {
  assert.deepEqual(occurrences("Art wrote the Article about Art.", "Art"), [[0, 3], [28, 31]]);
  assert.equal(occurrences("ref 44711 and 4471", "4471").length, 1);
  assert.equal(occurrences("ACCT0049821774471USD", "0049821774471").length, 1);
});

test("merge: a validated rule wins the type, provenance is kept", () => {
  const t = "card 4111 1111 1111 1111 ok";
  const rule = detectRules(t).find((s) => s.label === "card")!;
  const m = mergeSpans(t, [{ ...sp(t, "4111 1111 1111 1111", "CONTACT", "gliner"), why: ["GLiNER: phone number 0.40"] }, rule]);
  assert.equal(m.length, 1); assert.equal(m[0].type, "FIN_ID");
  assert.deepEqual(m[0].sources!.sort(), ["gliner", "rules"]); assert.equal(m[0].why!.length, 2);
});

test("coreference: parts, initials, possessives, capitals, handles", () => {
  const t = "Priya Raman opened it. P. Raman replied; Raman's adviser and PR agreed. RAMAN, PRIYA. Login praman42, mail p.raman@x.io.";
  const out = values(t, propagate(t, mergeSpans(t, [sp(t, "Priya Raman", "NAME")])));
  for (const v of ["Priya Raman", "P. Raman", "Raman", "PR", "RAMAN", "PRIYA", "praman42", "p.raman@x.io"]) assert.ok(out.includes(v), `missing ${v} in ${JSON.stringify(out)}`);
  assert.ok(nameVariants("Bill Stone").every(([v]) => v !== "BILL"), "common-word names are not propagated in capitals");
});

test("precision filters: public bodies and reporting periods are kept, commercial banks are not", () => {
  const t = "The SEC and Royal Bank of Canada met in Q3 2025; signed March 3, 2026.";
  const raw = [sp(t, "SEC", "ORG"), sp(t, "Royal Bank of Canada", "ORG"), sp(t, "Q3 2025", "DATE"), sp(t, "March 3, 2026", "DATE")];
  assert.deepEqual(values(t, finalize(t, raw)), ["Royal Bank of Canada", "March 3, 2026"]);
  assert.equal(finalize(t, raw, { orgAllowlist: false, dropNonpersonalDates: false }).length, 4);
});

test("custom terms, allow-list and excluded types", () => {
  const t = "Project Falcon pays Acme Bank on March 3, 2026. project falcon again.";
  const raw = [sp(t, "Acme Bank", "ORG"), sp(t, "March 3, 2026", "DATE")];
  const out = finalize(t, raw, { customTerms: ["Project Falcon"], allowTerms: ["acme bank"], excludeTypes: ["DATE"] });
  assert.deepEqual(out.map((s) => [t.slice(s.start, s.end), s.type]), [["Project Falcon", "CUSTOM"], ["project falcon", "CUSTOM"]]);
});

test("keep last 4 digits", () => {
  const t = "acct 0049821774471 card 4111 1111 1111 1111 pin 9921";
  const out = keepLast4(t, [sp(t, "0049821774471", "FIN_ID"), sp(t, "4111 1111 1111 1111", "FIN_ID"), sp(t, "9921", "FIN_ID")]);
  assert.deepEqual(values(t, out), ["004982177", "4111 1111 1111", "9921"]);
});

test("render styles, restore round trip, leak check", () => {
  const spans = finalize(DOC, detectRules(DOC));
  const r = render(DOC, spans, "placeholder");
  assert.ok(!r.output.includes("4111 1111")); assert.match(r.output, /\[FIN_ID_1\]/);
  assert.equal(restore(r.output, r.vault), DOC, "restore is byte-exact");
  assert.deepEqual(leakCheck(r.output, Object.values(r.vault)), []);
  assert.equal(r.marks.length, mergeSpans(DOC, spans).length);
  for (const [a, b] of r.marks) assert.match(r.output.slice(a, b), /^\[[A-Z_]+_\d+\]$/);
  assert.ok(render(DOC, spans, "label").output.includes("[FIN_ID]"));
  assert.ok(render(DOC, spans, "block").output.includes("█".repeat(6)));
  // a value left un-redacted somewhere is a leak, unless the user chose to keep that region
  const partial = render(DOC, spans.filter((s) => DOC.slice(s.start, s.end) !== "021000021"));
  const at = partial.output.indexOf("021000021");
  assert.deepEqual(leakCheck(partial.output, ["021000021"]), ["021000021"]);
  assert.deepEqual(leakCheck(partial.output, ["021000021"], [[at, at + 9]]), []);
});

test("offset conversion across astral characters", () => {
  const t = "😀 John 😀 Smith";
  const cp = [{ start: 2, end: 6 }, { start: 9, end: 14 }];
  const u16 = convertOffsets(t, cp, "utf16");
  assert.deepEqual(u16.map((s) => t.slice(s.start, s.end)), ["John", "Smith"]);
  assert.deepEqual(convertOffsets(t, u16, "codepoint"), cp);
});

test("vault: seal, open, wrong password, tampering", async () => {
  const vault = { "[NAME_1]": "Priya Raman", "[FIN_ID_1]": "0049821774471" };
  const sealed = await sealVault(vault, "correct horse battery", 1000);
  assert.ok(!JSON.stringify(sealed).includes("Priya"));
  assert.deepEqual(await openVault(sealed, "correct horse battery"), vault);
  await assert.rejects(openVault(sealed, "wrong password"));
  await assert.rejects(openVault({ ...sealed, ct: sealed.ct.slice(0, -4) + "AAAA" }, "correct horse battery"));
  assert.equal(passwordStrength("short").score, 0);
  assert.ok(passwordStrength("password123").score <= 1);
  assert.ok(passwordStrength("correct horse battery staple").score >= 3);
});

test("leak check ignores our own placeholders; partial digit findings are widened", () => {
  const t = "Header ORG: Northgate.";
  const r = render(t, finalize(t, [sp(t, "ORG", "ORG")]));
  assert.ok(r.output.includes("[ORG_1]")); assert.deepEqual(leakCheck(r.output, Object.values(r.vault)), []);
  const u = "ref 55664471 and ref 77884471 end";
  const fin = finalize(u, [sp(u, "4471", "ADDRESS"), { ...sp(u, "7788", "ADDRESS") }]);
  const out = render(u, fin).output;
  assert.ok(!/4471|7788|5566/.test(out), out); assert.deepEqual(leakCheck(out, fin.map((s) => u.slice(s.start, s.end))), []);
});
