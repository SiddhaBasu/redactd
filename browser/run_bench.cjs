// node run_bench.cjs <model...>   -> launches Chromium, runs window.runBench for each model, prints JSON
const { chromium } = require("playwright");
const { spawn } = require("child_process"); const fs = require("fs");
(async () => {
  const srv = spawn("python3", ["serve.py", "8765"], { cwd: __dirname, stdio: "ignore" });
  await new Promise(r => setTimeout(r, 800));
  const chars = +(process.env.CHARS || 20000);
  const text = fs.readFileSync(__dirname + "/sample.txt", "utf8").slice(0, chars);
  const browser = await chromium.launch({ args: ["--enable-unsafe-webgpu"] });
  for (const m of process.argv.slice(2)) {
    const page = await browser.newPage(); page.on("pageerror", e => console.error("pageerror", e.message));
    page.setDefaultTimeout(0);
    await page.goto("http://127.0.0.1:8765/index.html"); await page.waitForFunction("window.benchReady === true");
    try { console.log(JSON.stringify(await page.evaluate(([w, t]) => window.runBench(w, t), [m, text]))); }
    catch (e) { console.log(JSON.stringify({ which: m, error: String(e).slice(0, 300) })); }
    await page.close();
  }
  await browser.close(); srv.kill();
})();
