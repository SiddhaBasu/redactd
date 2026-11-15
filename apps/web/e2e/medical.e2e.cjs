// Medical document type end to end: choose it in the options drawer, scan a clinical note, check health findings.
//   node e2e/medical.e2e.cjs     (needs the API on :8000 and `next start` on :3000)
const { chromium } = require("playwright");
const assert = require("assert/strict");
const { scanButton, openMore } = require("./ui.cjs");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const NOTE = `Discharge summary for Jane Roe (MRN 00123456), DOB 04/12/1961. Admitted with type 2 diabetes.
Started metformin 500 mg twice daily. Blood type O positive. NHS number 943 476 5919.
Follow-up with Dr. Amit Shah (NPI 1234567893).`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
  for (let i = 0; i < 20; i++) { await p.locator("#doc").fill(NOTE); if (await scanButton(p).isEnabled()) break; await p.waitForTimeout(300); }
  await p.getByRole("button", { name: /Options/ }).click();
  const d = p.getByRole("dialog", { name: "Options" });
  await d.getByRole("group", { name: "Document type" }).getByRole("button", { name: "Medical" }).click();
  await p.screenshot({ path: "../../docs/screenshots/11-medical-options-1280-light.png" });
  await p.keyboard.press("Escape");
  assert.match(await p.getByText(/^Medical · /).innerText(), /Medical · Standard/);
  await scanButton(p).click(); await p.getByText("Leak check passed").waitFor({ timeout: 120000 });
  await openMore(p); const out = await p.getByTestId("output").innerText();
  for (const v of ["Jane Roe", "00123456", "type 2 diabetes", "metformin", "O positive", "943 476 5919", "1234567893", "Amit Shah"]) assert.ok(!out.includes(v), `left in output: ${v}`);
  assert.match(out, /Admitted with \[HEALTH_1\]/, "the condition is labelled Health info");
  assert.match(out, /\[HEALTH_2\]/);
  console.log(out.split("\n")[0]); console.log("PASS medical e2e");
  await p.screenshot({ path: "../../docs/screenshots/12-medical-result-1280-light.png", fullPage: true });
  await b.close();
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
