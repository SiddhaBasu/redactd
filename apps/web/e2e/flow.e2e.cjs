// End-to-end: keyboard-first review, export, restore round trip (byte-exact), presets, shortcuts overlay.
// Usage: node e2e/flow.e2e.cjs [Fast|Standard|Thorough]     (needs the API on :8000 and `next start` on :3000)
// BASE_URL / mode can be overridden for preview deployments: BASE_URL=https://preview.example node e2e/flow.e2e.cjs
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), os = require("os"), assert = require("assert/strict");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const DOC = fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/wire_recall.txt"), "utf8").replace(/\n$/, "");   // the sample has no trailing newline
const MUST = ["priya.raman@northgate-mail.com", "0049821774471", "021000021", "GB82WEST12345698765432", "Royal Bank of Canada", "4111 1111 1111 1111", "555-0199", "123-45-6789"];
const MODEL_ONLY = ["Priya", "Raman", "Okafor", "Boise"];   // names and places need a model (Standard / Thorough)

(async () => {
  const mode = process.argv[2] || "Fast";
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const p = await ctx.newPage();
  const errs = []; p.on("pageerror", (e) => errs.push(e.message)); p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
  const step = (s) => console.log("  ✓", s);

  await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
  const scan = p.getByRole("button", { name: "Scan for sensitive data" });
  // 1. onboarding sample -> scan
  for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.getByRole("button", { name: "Try the sample document" }).click().catch(() => {}); await p.waitForTimeout(300); }
  assert.equal(await p.locator("#doc").inputValue(), DOC, "sample equals the fixture");
  await p.getByRole("radio", { name: new RegExp(`^${mode}`) }).click();
  const t0 = Date.now();
  await scan.click();
  await p.getByTestId("viewer").waitFor({ timeout: 10 * 60_000 });
  await p.getByText("Leak check passed").waitFor({ timeout: 60_000 });
  step(`scan in ${mode} mode: ${((Date.now() - t0) / 1000).toFixed(1)} s, ${await p.getByTestId("summary").innerText()}`);
  const output = () => p.getByTestId("output").innerText();
  let out = await output();
  const must = mode === "Fast" ? MUST : [...MUST, ...MODEL_ONLY];
  assert.deepEqual(must.filter((v) => out.includes(v)), [], "identifiers left in the output");

  // 2. keyboard-only review: focus the viewer with Tab-reachable focus(), then drive everything from the keyboard
  await p.getByTestId("viewer").focus();
  const focusedText = () => p.locator("mark[data-focus='1']").first().innerText();
  const first = await focusedText();
  await p.keyboard.press("j"); const second = await focusedText();
  assert.notEqual(first, second, "j moves to the next finding");
  await p.keyboard.press("k"); assert.equal(await focusedText(), first, "k moves back");
  await p.getByTestId("popover").waitFor();
  assert.match(await p.getByTestId("popover").innerText(), /Found by/);
  await p.keyboard.press("x");
  assert.ok((await output()).includes(first), "x keeps the focused finding");
  await p.keyboard.press("u");
  assert.ok(!(await output()).includes(first), "u undoes");
  await p.keyboard.press("Shift+U"); assert.ok((await output()).includes(first), "Shift+U redoes"); await p.keyboard.press("u");
  await p.keyboard.press("Shift+A"); const kept = await output(); await p.keyboard.press("a");
  assert.notEqual(kept, await output(), "a re-accepts every finding of the focused type");
  await p.keyboard.press("/"); await p.keyboard.type("recall"); await p.keyboard.press("Enter");
  await p.waitForFunction(() => !document.querySelector("#search"));
  assert.ok(!/recall/i.test(await output()), "/ search-and-redact removed every match");
  await p.keyboard.press("u"); assert.ok(/recall/i.test(await output()), "search-and-redact is one undo step");
  await p.keyboard.press("?"); await p.getByRole("dialog", { name: "Keyboard shortcuts" }).waitFor();
  await p.keyboard.press("Escape"); await p.getByRole("dialog").waitFor({ state: "detached" });
  await p.keyboard.press("d"); await p.getByText("Redacted output", { exact: true }).waitFor(); await p.keyboard.press("d");
  step("keyboard review: j/k, x, u/U, a/A, / search, ? overlay, d diff");

  // 3. presets change the output without rescanning
  await p.getByRole("radio", { name: /^Share with LLM/ }).click();
  await p.waitForFunction(() => document.querySelector("[data-testid=output]").innerText.includes("Royal Bank of Canada"));
  out = await output(); assert.ok(out.includes("March 3, 2026") && /\[[A-Z_]+_1\]/.test(out) && !out.includes("4111 1111"));
  await p.getByRole("radio", { name: /^Legal production/ }).click();
  await p.waitForFunction(() => document.querySelector("[data-testid=output]").innerText.includes("██████"));
  out = await output(); assert.ok(!out.includes("Royal Bank of Canada") && !out.includes("March 3, 2026") && !/\[[A-Z_]+\]/.test(out));
  await p.getByRole("radio", { name: /^Analytics/ }).click();
  await p.waitForFunction(() => document.querySelector("[data-testid=output]").innerText.includes("[FIN_ID]"));
  assert.ok((await output()).includes("March 3, 2026"));
  await p.getByRole("radio", { name: /^Standard Reversible/ }).click();
  await p.waitForFunction(() => /\[FIN_ID_1\]/.test(document.querySelector("[data-testid=output]").innerText));
  await p.getByRole("switch", { name: "Keep last 4 digits" }).click();
  await p.waitForFunction(() => document.querySelector("[data-testid=output]").innerText.includes("1111 was also"));
  await p.getByRole("switch", { name: "Keep last 4 digits" }).click();
  await p.waitForFunction(() => !document.querySelector("[data-testid=output]").innerText.includes("1111 was also"));
  step("presets: Share with LLM, Legal production, Analytics, Standard, keep last 4");

  // 4. export: redacted file (original extension kept), report without values, restore key
  await p.getByText("Leak check passed").waitFor();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "redactd-e2e-"));
  const save = async (click) => { const [d] = await Promise.all([p.waitForEvent("download"), click()]); const f = path.join(dir, d.suggestedFilename()); await d.saveAs(f); return f; };
  const redFile = await save(() => p.getByRole("button", { name: "Download redacted file" }).click());
  assert.equal(path.basename(redFile), "sample-wire-recall.redacted.txt");
  const redacted = fs.readFileSync(redFile, "utf8");
  assert.deepEqual(must.filter((v) => redacted.includes(v)), []);
  const repFile = await save(() => p.getByRole("button", { name: "Download report", exact: true }).click());
  const report = fs.readFileSync(repFile, "utf8");
  assert.ok(/Leak check\s+Passed/.test(report) && /\| Financial IDs \|/.test(report) && /rules/.test(report));
  assert.deepEqual([...MUST, ...MODEL_ONLY].filter((v) => report.includes(v)), [], "report must not contain values");
  await p.locator("#pw").fill("correct horse battery staple");
  const keyFile = await save(() => p.getByRole("button", { name: "Download restore key" }).click());
  const key = fs.readFileSync(keyFile, "utf8");
  assert.deepEqual(MUST.filter((v) => key.includes(v)), [], "the key file is encrypted");
  step(`export: ${path.basename(redFile)}, report (no values), encrypted key`);

  // 5. restore round trip, byte-exact
  await p.goto(`${BASE}/restore`, { waitUntil: "networkidle" });
  for (let i = 0; i < 20; i++) { await p.locator("#rtext").fill(redacted); if ((await p.locator("#rtext").inputValue()) === redacted) break; await p.waitForTimeout(300); }
  await p.locator("input[type=file][accept^='.json']").setInputFiles(keyFile);
  await p.getByText("Key loaded").waitFor();
  await p.locator("#rpw").fill("wrong password");
  await p.getByRole("button", { name: "Restore", exact: true }).click();
  await p.getByRole("alert").filter({ hasText: "Could not unlock" }).waitFor();
  await p.locator("#rpw").fill("correct horse battery staple");
  await p.getByRole("button", { name: "Restore", exact: true }).click();
  await p.getByTestId("restored").waitFor();
  const restoredFile = await save(() => p.getByRole("button", { name: "Download" }).click());
  assert.ok(Buffer.from(DOC, "utf8").equals(fs.readFileSync(restoredFile)), "restored file is byte-identical to the original");
  step("restore: wrong password rejected; round trip is byte-exact");

  assert.deepEqual(errs.filter((e) => !/favicon/.test(e)), [], "console errors");
  await browser.close();
  console.log(`PASS flow e2e (${mode})`);
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
