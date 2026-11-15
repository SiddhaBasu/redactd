// Screenshots for docs/screenshots (360 px and 1280 px, light and dark). node e2e/shots.cjs [Fast|Standard|Thorough]
const { chromium } = require("playwright");
const path = require("path");
const { loadSample, setOptions, openMore } = require("./ui.cjs");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3000", OUT = path.join(__dirname, "../../../docs/screenshots");
(async () => {
  const mode = process.argv[2] || "Standard";
  const b = await chromium.launch();
  for (const [w, h, scheme] of [[1280, 900, "light"], [1280, 900, "dark"], [360, 780, "light"], [360, 780, "dark"]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, colorScheme: scheme });
    const p = await ctx.newPage(); const tag = `${w}-${scheme}`;
    const shot = (n, full = true) => p.screenshot({ path: `${OUT}/${n}-${tag}.png`, fullPage: full });
    await p.goto(`${BASE}/`, { waitUntil: "networkidle" }); await shot("1-landing");
    await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
    const scan = await loadSample(p); await shot("2-input");
    await p.getByRole("button", { name: /Options/ }).click(); await p.getByRole("dialog", { name: "Options" }).waitFor(); await shot("3-options", false);
    await p.keyboard.press("Escape"); await setOptions(p, { mode });
    await scan.click(); await p.getByText("Leak check passed").waitFor({ timeout: 10 * 60_000 });
    await p.getByTestId("viewer").focus(); await p.keyboard.press("j"); await p.keyboard.press("j"); await p.waitForTimeout(300); await shot("4-review");
    await p.getByRole("button", { name: "Details" }).click(); await p.getByRole("dialog", { name: "Findings" }).waitFor(); await shot("5-findings", false); await p.keyboard.press("Escape");
    await p.getByTestId("viewer").focus(); await p.keyboard.press("d"); await p.waitForTimeout(300); await shot("6-compare", false); await p.keyboard.press("d");
    await p.keyboard.press("?"); await p.waitForTimeout(200); await shot("7-shortcuts", false); await p.keyboard.press("Escape");
    await openMore(p); await p.locator("#pw").fill("correct horse battery"); await p.waitForTimeout(200); await shot("8-export");
    await p.goto(`${BASE}/restore`, { waitUntil: "networkidle" }); await shot("9-restore");
    await p.goto(`${BASE}/privacy`, { waitUntil: "networkidle" }); await shot("10-data-policy");
    await ctx.close(); console.log("shots", tag);
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
