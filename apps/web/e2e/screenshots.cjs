// Captures UI screenshots into docs/screenshots (needs web on :3000 and API on :8000).
const { chromium } = require("playwright");
const fs = require("fs");
const DOC = fs.readFileSync(__dirname + "/../../../tests/fixtures/wire_recall.txt", "utf8");
const OUT = __dirname + "/../../../docs/screenshots/";
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 2 });
  await p.goto("http://127.0.0.1:3000/", { waitUntil: "networkidle" });
  await p.screenshot({ path: OUT + "1-landing.png" });
  await p.goto("http://127.0.0.1:3000/redact", { waitUntil: "networkidle" });
  const scan = p.getByRole("button", { name: "Scan for sensitive data" });
  for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.fill("textarea", DOC); await p.waitForTimeout(400); }
  await p.screenshot({ path: OUT + "2-input.png" });
  await scan.click();
  await p.locator("text=/Leak check passed|still present/").first().waitFor({ timeout: 300000 });
  // reject one finding to show the review interaction
  await p.getByRole("button", { name: "Royal Bank of Canada" }).first().click();
  await p.locator("text=Review").first().scrollIntoViewIfNeeded();
  await p.evaluate(() => window.scrollTo(0, document.querySelector("section:nth-of-type(2)").offsetTop - 20));
  await p.screenshot({ path: OUT + "3-review.png" });
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await p.fill("input[type=password]", "correct horse battery");
  await p.screenshot({ path: OUT + "4-output.png" });
  await p.goto("http://127.0.0.1:3000/restore", { waitUntil: "networkidle" });
  await p.screenshot({ path: OUT + "5-restore.png" });
  await b.close();
})();
