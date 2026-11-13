// End-to-end: open /redact, paste a financial document, scan in a given mode, check output + leak check.
// Usage: node e2e/redact.e2e.cjs <mode: Fast|Standard|Thorough>   (needs `next start` on :3000)
const { chromium } = require("playwright");
const DOC = `From: Priya Raman <priya.raman@northgate-mail.com>
Subject: Wire recall request - acct ending 4471

Hi team, please recall the wire sent on March 3, 2026 from account 0049821774471 (routing 021000021)
to IBAN GB82WEST12345698765432 at Royal Bank of Canada. The beneficiary, Daniel Okafor, is a 52-year-old
retired teacher in Boise. Priya's card 4111 1111 1111 1111 was also flagged. Call me at (415) 555-0199.
SSN on file: 123-45-6789. Thanks, Priya Raman, Northgate Capital Partners`;
(async () => {
  const mode = process.argv[2] || "Fast";
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
  const errs = []; p.on("pageerror", (e) => errs.push(e.message)); p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
  await p.goto("http://127.0.0.1:3000/redact", { waitUntil: "networkidle" });
  console.log("crossOriginIsolated", await p.evaluate(() => self.crossOriginIsolated));
  // React may hydrate after load; re-fill until the controlled textarea enables the Scan button.
  const scanBtn = p.getByRole("button", { name: "Scan for sensitive data" });
  for (let i = 0; i < 20 && !(await scanBtn.isEnabled()); i++) { await p.fill("textarea", DOC); await p.waitForTimeout(500); }
  await p.getByRole("button", { name: new RegExp(`^${mode}`) }).click();
  const t0 = Date.now();
  await p.getByRole("button", { name: "Scan for sensitive data" }).click();
  await p.locator("text=/Leak check passed|still present/").first().waitFor({ timeout: 15 * 60_000 });
  const out = await p.locator("pre").first().innerText();
  console.log(`mode=${mode} seconds=${((Date.now() - t0) / 1000).toFixed(1)}`);
  console.log(out);
  const must = ["Priya", "Raman", "priya.raman@northgate-mail.com", "0049821774471", "021000021", "GB82WEST12345698765432",
    "Royal Bank of Canada", "4111 1111 1111 1111", "555-0199", "123-45-6789", "Okafor"];
  const leaked = must.filter((v) => out.includes(v));
  console.log("LEAKED:", leaked.length ? leaked : "none", "| badge:", await p.locator("text=/Leak check|still present/").first().innerText());
  await p.screenshot({ path: `e2e/screenshot-${mode}.png`, fullPage: true });
  if (errs.length) console.log("ERRORS:", errs.slice(0, 5));
  await b.close();
})();
