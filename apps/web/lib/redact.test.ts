import { test } from "node:test";
import assert from "node:assert/strict";
import { detectRules, luhn, aba, ibanOk } from "./rules.ts";
import { propagate, render, restore, leakCheck, mergeSpans } from "./redact.ts";

const DOC = "Dear Mr. Okafor, loan 88-4410-2297 approved 2026-03-02. IBAN GB82WEST12345698765432, card 4111 1111 1111 1111, " +
  "routing 021000021. Call +1 (415) 555-0199 or chidi.okafor@example.com. Guarantor: Bank of the West. Okafor signed.";

test("validators", () => {
  assert.ok(luhn("4111 1111 1111 1111")); assert.ok(!luhn("4111 1111 1111 1112"));
  assert.ok(aba("021000021")); assert.ok(!aba("123456789"));
  assert.ok(ibanOk("GB82WEST12345698765432")); assert.ok(!ibanOk("GB00WEST12345698765432"));
});

test("rules find financial identifiers", () => {
  const vals = detectRules(DOC).map((s) => DOC.slice(s.start, s.end));
  for (const v of ["GB82WEST12345698765432", "4111 1111 1111 1111", "021000021", "chidi.okafor@example.com", "2026-03-02", "Okafor", "Bank of the West"])
    assert.ok(vals.some((x) => x.includes(v)), `missing ${v}: ${vals.join(" | ")}`);
});

test("propagation redacts every occurrence, render+restore round-trips, leak check passes", () => {
  const spans = propagate(DOC, mergeSpans(detectRules(DOC)));
  const { output, vault } = render(DOC, spans, "placeholder");
  assert.ok(!output.includes("Okafor"), output);
  assert.deepEqual(leakCheck(output, Object.values(vault)), []);
  assert.equal(restore(output, vault), DOC);
  const block = render(DOC, spans, "block").output;
  assert.ok(!block.includes("4111"));
});
