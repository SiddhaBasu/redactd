// On-device mode (D7 + E1): cold load with a throttled connection, warm load from the Cache API, and a tampered
// model file must be refused.  node e2e/device.e2e.cjs [Standard|Thorough] [mbit=50]
const { chromium } = require("playwright");
const assert = require("assert/strict");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const mode = process.argv[2] || "Standard", mbit = Number(process.argv[3] || 50);
const MUST = ["Priya", "Raman", "priya.raman@northgate-mail.com", "0049821774471", "021000021", "GB82WEST12345698765432", "4111 1111 1111 1111", "123-45-6789", "Okafor"];

async function run(ctx, label, { throttle = false, tamper = false } = {}) {
  const p = await ctx.newPage();
  const errs = []; p.on("pageerror", (e) => errs.push(e.message));
  let modelBytes = 0, modelRequests = 0;
  p.on("response", async (r) => { if (r.url().includes("/models/")) { modelRequests++; modelBytes += Number((await r.allHeaders())["content-length"] || 0); } });
  if (tamper) await p.route("**/models/**/tokenizer.json", async (route) => { const r = await route.fetch(); const b = await r.body(); b[b.length - 5] ^= 1; await route.fulfill({ response: r, body: b }); });
  if (throttle) { const cdp = await ctx.newCDPSession(p); await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 20, downloadThroughput: (mbit * 1e6) / 8, uploadThroughput: (mbit * 1e6) / 8 }); }
  await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
  const scan = p.getByRole("button", { name: "Scan for sensitive data" });
  for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.getByRole("button", { name: "Try the sample document" }).click().catch(() => {}); await p.waitForTimeout(300); }
  await p.getByRole("radio", { name: /^On this device only/ }).click();
  await p.getByRole("radiogroup", { name: "Detection mode" }).getByRole("radio", { name: new RegExp(`^${mode}`) }).click();
  const t0 = Date.now(); await scan.click();
  if (tamper) {
    await p.getByRole("alert").filter({ hasText: /integrity check/ }).waitFor({ timeout: 120_000 });
    console.log(`  ✓ ${label}: tampered model file refused ("${(await p.getByRole("alert").filter({ hasText: /integrity check/ }).innerText()).slice(0, 90)}…")`); await p.close(); return 0;
  }
  await p.getByText(/Leak check passed|still present/).waitFor({ timeout: 15 * 60_000 });
  const s = (Date.now() - t0) / 1000, out = await p.getByTestId("output").innerText();
  assert.deepEqual(MUST.filter((v) => out.includes(v)), [], "identifiers left in on-device output");
  assert.deepEqual(errs, []);
  console.log(`  ✓ ${label}: ${s.toFixed(1)} s, ${modelRequests} model requests, ${(modelBytes / 1e6).toFixed(0)} MB downloaded, isolated=${await p.evaluate(() => self.crossOriginIsolated)}`);
  await p.close(); return s;
}
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const cold = await run(ctx, `cold load at ${mbit} Mbit/s (${mode})`, { throttle: true });
  const warm = await run(ctx, `warm load (${mode})`);
  const ctx2 = await browser.newContext();
  await run(ctx2, "integrity", { tamper: true });
  await browser.close();
  console.log(`RESULT ${mode}: cold ${cold.toFixed(1)} s (target < 15 s), warm ${warm.toFixed(1)} s (target < 2 s)`);
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
