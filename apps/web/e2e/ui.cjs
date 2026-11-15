// Shared helpers for the e2e scripts: the workspace keeps its options in a drawer and export extras under "More".
const scanButton = (p) => p.locator("button.btn-primary").filter({ hasText: /^(Redact|Redact again|Scanning…)$/ }).first();

async function loadSample(p) {
  const scan = scanButton(p);
  for (let i = 0; i < 20 && !(await scan.isEnabled()); i++) { await p.getByRole("button", { name: "Try a sample" }).click().catch(() => {}); await p.waitForTimeout(300); }
  return scan;
}
/** opts: { mode: "Fast"|"Standard"|"Thorough", where: "server"|"device", preset: "standard"|"llm"|"legal"|"analytics", keepLast4: boolean } */
async function setOptions(p, opts) {
  await p.getByRole("button", { name: /Options/ }).click();
  const d = p.getByRole("dialog", { name: "Options" }); await d.waitFor();
  if (opts.mode) await d.getByRole("group", { name: "Detection mode" }).getByRole("button", { name: opts.mode, exact: true }).click();
  if (opts.where) await d.getByRole("group", { name: "Where to process" }).getByRole("button", { name: opts.where === "device" ? "This device" : "Our server" }).click();
  if (opts.preset) await d.locator("#preset").selectOption(opts.preset);
  if (opts.keepLast4 !== undefined) {
    const sw = d.getByRole("switch", { name: "Keep last 4 digits" });
    if ((await sw.getAttribute("aria-checked")) !== String(opts.keepLast4)) await sw.click();
  }
  await p.keyboard.press("Escape"); await d.waitFor({ state: "detached" });
}
async function openMore(p) {
  const more = p.getByRole("button", { name: /More$/ });
  if ((await more.getAttribute("aria-expanded")) !== "true") await more.click();
}
module.exports = { scanButton, loadSample, setOptions, openMore };
