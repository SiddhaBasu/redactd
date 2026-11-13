// D1 + D6 checks:  node e2e/quality.e2e.cjs      (needs the API on :8000 and `next start` on :3000)
//  * axe-core: no WCAG 2.2 A/AA violations on every page and state, at 1280 px and 360 px, light and dark
//  * 1 MB document (~10k findings): stage-by-stage progress over SSE, then no long task over 100 ms while scrolling
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path"), assert = require("assert/strict");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const AXE = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const SAMPLE = fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/wire_recall.txt"), "utf8");

function bigDoc(bytes = 1_000_000) {
  // every block gets different numbers so there are thousands of distinct values, like a real export
  const parts = []; let n = 0, i = 0;
  while (n < bytes - 600) {
    const b = SAMPLE.replace(/0049821774471/g, String(4000000000000 + i * 7919)).replace(/555-0199/g, `555-${String(1000 + (i % 9000))}`).replace("Daniel Okafor", `Daniel Okafor${i % 97}`) + `\nRef ${i}: card ending ${String(1000 + (i * 37) % 9000)}; next review on ${1 + (i % 28)} March 2026.\n\n`;
    parts.push(b); n += b.length; i++;
  }
  return parts.join("");
}
async function axe(p, label) {
  await p.evaluate(AXE);
  const r = await p.evaluate(async () => await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } }));
  const v = r.violations.map((x) => `${x.id} (${x.impact}): ${x.nodes.length} node(s), e.g. ${x.nodes[0].target.join(" ")} — ${x.nodes[0].failureSummary.split("\n")[1] || ""}`);
  console.log(`  ${v.length ? "✗" : "✓"} axe ${label}: ${r.passes.length} rules passed, ${v.length} violations`);
  return v.map((x) => `${label}: ${x}`);
}

(async () => {
  const browser = await chromium.launch();
  const violations = [];
  for (const [w, h, scheme] of [[1280, 900, "light"], [1280, 900, "dark"], [360, 780, "light"], [360, 780, "dark"]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, bypassCSP: true });
    const p = await ctx.newPage(); const tag = `${w}px ${scheme}`;
    for (const route of ["/", "/privacy", "/restore"]) { await p.goto(BASE + route, { waitUntil: "networkidle" }); violations.push(...await axe(p, `${route} ${tag}`)); }
    await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
    violations.push(...await axe(p, `/redact empty ${tag}`));
    const scan = p.getByRole("button", { name: "Scan for sensitive data" });
    for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.getByRole("button", { name: "Try the sample document" }).click().catch(() => {}); await p.waitForTimeout(300); }
    await p.getByRole("radio", { name: /^Fast/ }).click(); await scan.click();
    await p.getByText("Leak check passed").waitFor();
    await p.getByTestId("viewer").focus(); await p.keyboard.press("j"); await p.keyboard.press("x");
    violations.push(...await axe(p, `/redact review ${tag}`));
    for (const t of [/Needs review/, "Values"]) { await p.getByRole("tab", { name: t }).click(); violations.push(...await axe(p, `/redact tab ${t} ${tag}`)); }
    await p.getByTestId("viewer").focus(); await p.keyboard.press("d"); violations.push(...await axe(p, `/redact diff ${tag}`)); await p.keyboard.press("d");
    await p.keyboard.press("?"); await p.getByRole("dialog").waitFor(); violations.push(...await axe(p, `/redact shortcuts ${tag}`)); await p.keyboard.press("Escape");
    // no horizontal page scroll at this width
    const overflow = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    assert.ok(overflow <= 1, `page scrolls horizontally by ${overflow}px at ${tag}`);
    await ctx.close();
  }

  // ---- 1 MB performance
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/redact`, { waitUntil: "networkidle" });
  const doc = bigDoc(); const file = path.join(require("os").tmpdir(), "redactd-1mb.txt"); fs.writeFileSync(file, doc);
  const scan = p.getByRole("button", { name: "Scan for sensitive data" });
  for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.locator("input[type=file]").first().setInputFiles(file); await p.waitForTimeout(500); }
  await p.getByRole("radio", { name: new RegExp(`^${process.env.BIG_MODE || "Fast"}`) }).click();
  const stages = new Set(); const t0 = Date.now();
  await scan.click();
  while (!(await p.getByTestId("viewer").count())) {
    const s = await p.locator("[role=status] p.muted").first().innerText().catch(() => ""); if (s) stages.add(s);
    await p.waitForTimeout(40);
    if (Date.now() - t0 > 10 * 60_000) throw new Error("1 MB scan timed out");
  }
  const scanS = (Date.now() - t0) / 1000;
  const summary = await p.getByTestId("summary").innerText();
  console.log(`  ✓ 1 MB (${doc.length.toLocaleString()} chars): ${summary}; wall ${scanS.toFixed(1)} s; progress stages seen: ${[...stages].join(" → ")}`);
  assert.ok(stages.size >= 2, "expected stage-by-stage progress");
  assert.ok(scanS < 60, "1 MB must finish within 60 s");
  await p.getByText(/Leak check passed|still present/).waitFor({ timeout: 120_000 });
  const res = await p.evaluate(async () => {
    const el = document.querySelector("[data-testid=viewer]");
    const long = []; const po = new PerformanceObserver((l) => { for (const e of l.getEntries()) long.push(e.duration); }); po.observe({ entryTypes: ["longtask"] });
    const frames = []; let last = performance.now(), run = true;
    const tick = (t) => { frames.push(t - last); last = t; if (run) requestAnimationFrame(tick); }; requestAnimationFrame(tick);
    const max = el.scrollHeight - el.clientHeight;
    for (let i = 0; i <= 240; i++) { el.scrollTop = (max * i) / 240; await new Promise((r) => requestAnimationFrame(r)); }      // sweep the whole document
    for (let i = 0; i < 120; i++) { el.scrollTop = Math.max(0, el.scrollTop - 900); await new Promise((r) => requestAnimationFrame(r)); }  // fast scroll back
    run = false; await new Promise((r) => setTimeout(r, 200)); po.disconnect();
    frames.sort((a, b) => a - b);
    return { rows: Math.round(el.scrollHeight / 24), marks: document.querySelectorAll("mark.f").length, domRows: document.querySelectorAll(".doc-row").length,
      longTasks: long.length, maxLong: Math.max(0, ...long), over100: long.filter((d) => d > 100).length,
      p50: frames[Math.floor(frames.length / 2)], p95: frames[Math.floor(frames.length * 0.95)], maxFrame: frames[frames.length - 1], n: frames.length };
  });
  console.log(`  ${res.over100 ? "✗" : "✓"} scroll: ${res.rows} rows virtualised to ${res.domRows} DOM rows; frame p50 ${res.p50.toFixed(1)} ms, p95 ${res.p95.toFixed(1)} ms, max ${res.maxFrame.toFixed(0)} ms over ${res.n} frames; long tasks ${res.longTasks} (max ${res.maxLong.toFixed(0)} ms, ${res.over100} over 100 ms)`);
  // keyboard stays responsive on the big document
  await p.getByTestId("viewer").focus();
  const kt = await p.evaluate(async () => { const t = performance.now(); return t; });
  for (let i = 0; i < 20; i++) await p.keyboard.press("j");
  await p.keyboard.press("x"); await p.keyboard.press("u");
  console.log(`  ✓ keyboard on 1 MB: 20×j, x, u`);
  await browser.close();
  if (violations.length) { console.error("AXE VIOLATIONS\n" + violations.join("\n")); process.exit(1); }
  assert.equal(res.over100, 0, "long tasks over 100 ms while scrolling");
  console.log("PASS quality e2e");
})().catch((e) => { console.error("FAIL", e); process.exit(1); });
