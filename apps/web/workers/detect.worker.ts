/// <reference lib="webworker" />
// On-device detection, off the main thread. The document never leaves the browser: the only network requests made
// here are model file downloads from MODEL_BASE, and every file is checked against the SHA-256 in the bundled
// manifest before it is used (lib/models.ts). Returns RAW findings; the page applies the policy with finalize().
//
// Standard uses the single distilled model when this build ships it (redactd-small), otherwise OpenMed-Small.
// Thorough adds GLiNER-PII. Backend: WebGPU is tried only when the manifest lists an fp16 file for the model
// (int8 graphs run on WASM; WebGPU has no kernels for the quantised ops), then WASM with threads.
import { AutoTokenizer, AutoModelForTokenClassification, env, type PreTrainedTokenizer, type PreTrainedModel, type Tensor } from "@huggingface/transformers";
import { env as xenv } from "@xenova/transformers";   // gliner.js loads its tokenizer through this older package
import { Gliner } from "gliner";
import { detectRules, RULES_VERSION, SPEC } from "../lib/rules";
import { FINE_TO_COARSE, GLINER_LABELS } from "../lib/labels";
import { MANIFEST, hasModel, prepareModels, verifiedCache } from "../lib/models";
import type { PiiType, Span, WorkerRequest, WorkerResponse } from "../lib/types";

const MODEL_BASE = (process.env.NEXT_PUBLIC_MODEL_BASE || "/models/").replace(/\/?$/, "/");
const ORT_GLINER = "/ort-gliner/"; // self-hosted ORT 1.19 binaries for gliner.js (see scripts-copy-ort.mjs)
const TOKEN_MODEL = hasModel("redactd-small") ? "redactd-small" : "openmed-small";
const SOURCE = TOKEN_MODEL === "redactd-small" ? "distilled" : "openmed";
const DISPLAY = TOKEN_MODEL === "redactd-small" ? "redactd-small" : "OpenMed";

env.allowRemoteModels = false;
env.allowLocalModels = true;
env.localModelPath = MODEL_BASE;
env.useBrowserCache = false;
(env.backends.onnx as { wasm: { wasmPaths: string } }).wasm.wasmPaths = "/ort/";
xenv.allowRemoteModels = false; xenv.allowLocalModels = true; xenv.localModelPath = MODEL_BASE; xenv.useBrowserCache = false;

const post = (m: WorkerResponse) => (self as unknown as DedicatedWorkerGlobalScope).postMessage(m);
let files = new Map<string, ArrayBuffer>();
let stageMs: Record<string, number> = {};          // per-stage timings of the current request (metadata only)
const timed = async <T,>(name: string, f: () => Promise<T>): Promise<T> => {
  const t = performance.now();
  try { return await f(); } finally { stageMs[name] = Math.round((stageMs[name] ?? 0) + performance.now() - t); }
};

async function ensure(ids: string[], from: number, to: number) {
  const missing = ids.filter((id) => !Object.keys(MANIFEST.models[id]?.files ?? {}).every((f) => files.has(`${id}/${f}`)));
  if (!missing.length) return;
  const got = await timed("model files (download or cache + SHA-256)", () => prepareModels(MODEL_BASE, missing, (done, total) =>
    post({ kind: "progress", stage: `Getting the detection model (${(done / 1e6).toFixed(0)} of ${(total / 1e6).toFixed(0)} MB, first time only)`, pct: from + ((to - from) * done) / Math.max(1, total) })));
  files = new Map([...files, ...got]);
  (env as unknown as { useCustomCache: boolean; customCache: unknown }).useCustomCache = true;
  (env as unknown as { customCache: unknown }).customCache = verifiedCache(MODEL_BASE, files);
  (xenv as unknown as { useCustomCache: boolean }).useCustomCache = true;
  (xenv as unknown as { customCache: unknown }).customCache = verifiedCache(MODEL_BASE, files);
}

// ---------- glued text (mirrors redactd/models.py Glued): virtual spaces before the model, offsets mapped back
const GLUE = new RegExp(SPEC.lexicon.glue_pattern, "g");
function glue(text: string): { text: string; map: (s: number, e: number) => [number, number] } {
  const cuts: number[] = [];
  for (const m of text.matchAll(GLUE)) cuts.push(m.index!);
  if (!cuts.length) return { text, map: (s, e) => [s, e] };
  const parts: string[] = [];
  let last = 0;
  for (const c of cuts) { parts.push(text.slice(last, c), " "); last = c; }
  parts.push(text.slice(last));
  const pos = cuts.map((c, k) => c + k);                       // index of each inserted space
  const before = (x: number) => { let lo = 0, hi = pos.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (pos[mid] < x) lo = mid + 1; else hi = mid; } return lo; };
  return { text: parts.join(""), map: (s, e) => [s - before(s), e - before(e)] };
}

/** ~n-char chunks cut at whitespace, each overlapping the previous by ~overlap chars (mirrors models.char_chunks). */
function chunks(text: string, n: number, overlap: number): { off: number; chunk: string; cutL: boolean; cutR: boolean }[] {
  const out: { off: number; chunk: string; cutL: boolean; cutR: boolean }[] = [], L = text.length;
  let i = 0;
  while (i < L) {
    let j = Math.min(L, i + n);
    if (j < L) { const k = text.lastIndexOf(" ", j - 1); if (k >= i + n / 2) j = k; }
    out.push({ off: i, chunk: text.slice(i, j), cutL: i > 0, cutR: j < L });
    if (j >= L) break;
    const nxt = j - overlap, k = text.indexOf(" ", nxt);
    i = Math.max(i + 1, k > 0 && k < j ? k + 1 : nxt);
  }
  return out;
}

// ---------- token classifier (distilled model or OpenMed)
let tok: PreTrainedTokenizer | null = null, model: PreTrainedModel | null = null;

async function loadTokenModel() {
  if (model) return;
  await ensure([TOKEN_MODEL], 3, 40);
  post({ kind: "progress", stage: "Starting the model", pct: 42 });
  tok = await timed("tokenizer load", () => AutoTokenizer.from_pretrained(TOKEN_MODEL));
  const fp16 = Object.keys(MANIFEST.models[TOKEN_MODEL].files).includes("onnx/model_fp16.onnx");
  if (fp16 && "gpu" in navigator) {
    try { model = await AutoModelForTokenClassification.from_pretrained(TOKEN_MODEL, { dtype: "fp16", device: "webgpu" }); return; }
    catch { /* no usable adapter: fall through to WASM */ }
  }
  model = await timed("ONNX session (wasm)", () => AutoModelForTokenClassification.from_pretrained(TOKEN_MODEL, { dtype: "q8", device: "wasm" }));
}

/** Align sentencepiece tokens back to character offsets in `text`. */
function align(text: string, pieces: string[]): ([number, number] | null)[] {
  let cur = 0;
  return pieces.map((p) => {
    if (/^\[(CLS|SEP|PAD|UNK)\]$/.test(p)) return null;
    const piece = p.replace(/^▁/, "");
    if (!piece) return null;
    while (cur < text.length && /\s/.test(text[cur]) && !text.startsWith(piece, cur)) cur++;
    const at = text.startsWith(piece, cur) ? cur : text.indexOf(piece, cur);
    if (at < 0 || at - cur > 20) return null;
    cur = at + piece.length;
    return [at, cur];
  });
}

async function runTokenModel(text: string, sensitivity: number, from: number, to: number): Promise<Span[]> {
  await loadTokenModel();
  const id2label = (model!.config as unknown as { id2label: Record<string, string> }).id2label;
  const oIdx = Number(Object.entries(id2label).find(([, l]) => l === "O")![0]);
  const g = glue(text), out: Span[] = [];
  const parts = chunks(g.text, 1200, 200);
  for (let c = 0; c < parts.length; c++) {
    const { off, chunk, cutL, cutR } = parts[c];
    const inputs = tok!(chunk, { truncation: true, max_length: 512 });
    const { logits } = (await model!(inputs)) as { logits: Tensor };
    const [, seq, nl] = logits.dims as number[];
    const data = logits.data as Float32Array;
    const ids = Array.from((inputs.input_ids as Tensor).data as BigInt64Array, Number);
    const offsets = align(chunk, tok!.model.convert_ids_to_tokens(ids));
    const found: Span[] = [];
    let cur: Span | null = null;
    for (let t = 0; t < seq; t++) {
      const o = offsets[t];
      if (!o) continue;
      let mx = -Infinity;
      for (let k = 0; k < nl; k++) if (data[t * nl + k] > mx) mx = data[t * nl + k];
      let sum = 0, best = -1, bi = -1, exO = 0;
      for (let k = 0; k < nl; k++) { const ex = Math.exp(data[t * nl + k] - mx); sum += ex; if (k === oIdx) exO = ex; else if (ex > best) { best = ex; bi = k; } }
      const pPii = 1 - exO / sum;
      let type: PiiType | null = null, fine = "";
      if (pPii >= sensitivity) {
        fine = id2label[bi].replace(/^[BI]-/, "");
        type = (FINE_TO_COARSE[fine] ?? (fine in SPEC.groups ? (fine as PiiType) : "FIN_ID")) as PiiType;
      }
      if (type && cur && cur.type === type && o[0] - cur.end <= 1) {
        cur.end = o[1];
        if (pPii > (cur.score ?? 0)) { cur.score = pPii; cur.label = fine; }
      } else {
        if (cur) found.push(cur);
        cur = type ? { start: o[0], end: o[1], type, source: SOURCE, score: pPii, label: fine, why: [], sources: [SOURCE] } : null;
      }
    }
    if (cur) found.push(cur);
    for (const s of found) {
      // a finding touching an internal chunk edge may be truncated; the overlapping neighbour has it whole
      if ((cutL && s.start === 0) || (cutR && s.end >= chunk.length)) continue;
      const [a, b] = g.map(off + s.start, off + s.end);
      if (b > a) out.push({ ...s, start: a, end: b, why: [`${DISPLAY}: ${(s.label ?? "").replace(/_/g, " ").toLowerCase()} ${(s.score ?? 0).toFixed(2)}`] });
    }
    post({ kind: "progress", stage: `Scanning with ${DISPLAY}`, pct: from + ((to - from) * (c + 1)) / parts.length });
  }
  return out;
}

// ---------- GLiNER-PII (zero-shot span model)
let gliner: Gliner | null = null;
async function runGliner(text: string, threshold: number, from: number, to: number): Promise<Span[]> {
  if (!gliner) {
    await ensure(["gliner"], from, from + (to - from) * 0.4);
    post({ kind: "progress", stage: "Starting GLiNER-PII", pct: from + (to - from) * 0.42 });
    // hand gliner.js the verified bytes through a blob: URL so it cannot read an unverified copy from the network
    const modelUrl = URL.createObjectURL(new Blob([files.get("gliner/onnx/model_quint8.onnx")!]));
    gliner = new Gliner({
      tokenizerPath: "gliner",
      onnxSettings: { modelPath: modelUrl, executionProvider: "wasm", wasmPaths: ORT_GLINER, multiThread: true, maxThreads: navigator.hardwareConcurrency },
      transformersSettings: { allowLocalModels: true, useBrowserCache: false },
      maxWidth: 12, modelType: "span-level",
    });
    await gliner.initialize();
  }
  const labels = Object.keys(GLINER_LABELS), g = glue(text), out: Span[] = [];
  const parts = chunks(g.text, 1500, 200), base = from + (to - from) * 0.45;
  for (let c = 0; c < parts.length; c++) {
    const { off, chunk, cutL, cutR } = parts[c];
    const [res] = await gliner.inference({ texts: [chunk], entities: labels, threshold, flatNer: true });
    for (const e of res) {
      if ((cutL && e.start === 0) || (cutR && e.end >= chunk.length)) continue;
      const [a, b] = g.map(off + e.start, off + e.end);
      if (b > a) out.push({ start: a, end: b, type: GLINER_LABELS[e.label], source: "gliner", score: e.score, label: e.label, why: [`GLiNER: ${e.label} ${e.score.toFixed(2)}`], sources: ["gliner"] });
    }
    post({ kind: "progress", stage: "Scanning with GLiNER-PII", pct: base + ((to - base) * (c + 1)) / parts.length });
  }
  return out;
}

self.onmessage = async (ev: MessageEvent<WorkerRequest>) => {
  const { text, mode, sensitivity } = ev.data;
  const t0 = performance.now();
  stageMs = {};
  try {
    post({ kind: "progress", stage: "Applying pattern rules", pct: 2 });
    let spans: Span[] = detectRules(text);
    if (mode !== "rules") {
      await loadTokenModel();
      spans = spans.concat(await timed("inference (token model)", () => runTokenModel(text, sensitivity, 3, mode === "thorough" ? 55 : 98)));
    }
    if (mode === "thorough") spans = spans.concat(await runGliner(text, Math.max(0.15, sensitivity - 0.2), 55, 98));
    const versions: Record<string, string> = { rules: RULES_VERSION, "model manifest": MANIFEST.version };
    if (mode !== "rules") versions[SOURCE] = TOKEN_MODEL;
    if (mode === "thorough") versions.gliner = "gliner-pii-base-v1.0";
    post({ kind: "result", spans, ms: performance.now() - t0, versions, timings: stageMs });
  } catch (e) {
    post({ kind: "error", message: e instanceof Error ? e.message : String(e) });
  }
};
