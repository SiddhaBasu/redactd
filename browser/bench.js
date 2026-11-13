// Browser speed benchmark: runs inside headless Chromium (WASM backend; WebGPU if available).
import { pipeline, env } from "@huggingface/transformers";
import { Gliner } from "gliner";
env.allowRemoteModels = false; env.localModelPath = "/models/"; env.useBrowserCache = false;
env.backends.onnx.wasm.wasmPaths = "/ort/"; env.backends.onnx.wasm.numThreads = navigator.hardwareConcurrency;

const RULES = [
  /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g, /\bhttps?:\/\/[^\s<>"')]+/g, /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g,
  /\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b/g, /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b/g,
  /\b(?:\d[ -]?){12,18}\d\b/g, /\b\d{9}\b/g, /\b\d{3}-\d{2}-\d{4}\b/g,
  /(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?!\w)/g, /\b\d{4}-\d{2}-\d{2}\b/g,
  /\b\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4}\b/g, /\b[A-Za-z0-9_\-]{32,}\b/g,
];
function chunks(t, n = 1500) { const out = []; let i = 0; while (i < t.length) { let j = Math.min(t.length, i + n);
  if (j < t.length) { const k = t.lastIndexOf(" ", j); if (k > i + n / 2) j = k; } out.push(t.slice(i, j)); i = j; } return out; }

async function timeIt(fn) { const t0 = performance.now(); await fn(); return performance.now() - t0; }

window.runBench = async (which, text) => {
  const res = { which, chars: text.length, threads: env.backends.onnx.wasm.numThreads,
                isolated: self.crossOriginIsolated, webgpu: !!navigator.gpu };
  const parts = chunks(text);
  if (which === "regex") {
    res.load_ms = 0; let n = 0;
    res.run_ms = await timeIt(() => { for (const r of RULES) for (const _ of text.matchAll(r)) n++; }); res.hits = n;
  } else if (which === "gliner") {
    const g = new Gliner({ tokenizerPath: "gliner", onnxSettings: { modelPath: "/models/gliner/onnx/model_quint8.onnx",
      executionProvider: "wasm", wasmPaths: "/ort/", multiThread: true, maxThreads: navigator.hardwareConcurrency },
      transformersSettings: { allowLocalModels: true, useBrowserCache: false }, maxWidth: 12, modelType: "span-level" });
    res.load_ms = await timeIt(() => g.initialize());
    const labels = ["person name","email address","phone number","street address","city","social security number",
      "bank account number","credit card number","routing number","iban","customer id","date","company name","occupation","age"];
    let n = 0;
    res.run_ms = await timeIt(async () => { for (const p of parts) { const r = await g.inference({ texts: [p], entities: labels, threshold: 0.3, flatNer: true }); n += r[0].length; } });
    res.hits = n;
  } else {
    let p; res.load_ms = await timeIt(async () => { p = await pipeline("token-classification", which, { dtype: "q8", device: "wasm" }); });
    let n = 0;
    res.run_ms = await timeIt(async () => { for (const c of parts) { const r = await p(c); n += r.length; } });
    res.hits = n;
  }
  res.ms_per_1k_chars = +(res.run_ms / text.length * 1000).toFixed(2);
  res.est_seconds_per_MB = +(res.ms_per_1k_chars * 1000 / 1000).toFixed(1);
  return res;
};
window.benchReady = true;
