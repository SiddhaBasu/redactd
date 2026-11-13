/// <reference lib="webworker" />
// Runs all detection off the main thread. Nothing here makes network requests except loading model files
// from MODEL_BASE (same origin by default). Document text never leaves the browser.
import { AutoTokenizer, AutoModelForTokenClassification, env, type PreTrainedTokenizer, type PreTrainedModel, type Tensor } from "@huggingface/transformers";
import { env as xenv } from "@xenova/transformers";
import { Gliner } from "gliner";
import { detectRules, RULES_VERSION } from "../lib/rules";
import { FINE_TO_COARSE, GLINER_LABELS } from "../lib/labels";
import type { PiiType, Span, WorkerRequest, WorkerResponse } from "../lib/types";

const MODEL_BASE = (process.env.NEXT_PUBLIC_MODEL_BASE || "/models/").replace(/\/?$/, "/");
const ORT_GLINER = "/ort-gliner/"; // self-hosted ORT 1.19 binaries for gliner.js (see scripts-copy-ort.mjs)
env.allowRemoteModels = false;
env.allowLocalModels = true;
env.localModelPath = MODEL_BASE;
(env.backends.onnx as { wasm: { wasmPaths: string } }).wasm.wasmPaths = "/ort/";
xenv.allowRemoteModels = false;
xenv.localModelPath = MODEL_BASE;

const post = (m: WorkerResponse) => (self as unknown as DedicatedWorkerGlobalScope).postMessage(m);

/** Split text into chunks at whitespace, keeping absolute offsets. */
function chunks(text: string, n = 1500): [number, string][] {
  const out: [number, string][] = [];
  let i = 0;
  while (i < text.length) {
    let j = Math.min(text.length, i + n);
    if (j < text.length) { const k = text.lastIndexOf(" ", j); if (k > i + n / 2) j = k; }
    out.push([i, text.slice(i, j)]);
    i = j;
  }
  return out;
}

// ---------- OpenMed (DeBERTa token classifier) ----------
let tok: PreTrainedTokenizer | null = null, model: PreTrainedModel | null = null;

async function loadOpenMed() {
  if (model) return;
  post({ kind: "progress", stage: "Loading OpenMed model (first time only)", pct: 5 });
  tok = await AutoTokenizer.from_pretrained("openmed-small");
  model = await AutoModelForTokenClassification.from_pretrained("openmed-small", {
    dtype: "q8", device: "wasm",
    progress_callback: (p: { status: string; progress?: number }) => {
      if (p.status === "progress" && p.progress) post({ kind: "progress", stage: "Downloading OpenMed model", pct: 5 + p.progress * 0.4 });
    },
  });
}

/** Align sentencepiece tokens back to character offsets in `text`. */
function align(text: string, pieces: string[]): ([number, number] | null)[] {
  let cur = 0;
  return pieces.map((p) => {
    if (/^\[(CLS|SEP|PAD|UNK)\]$/.test(p)) return null;
    const piece = p.replace(/^▁/, "");
    if (!piece) return null;
    while (cur < text.length && /\s/.test(text[cur]) && !text.startsWith(piece, cur)) cur++;
    let at = text.startsWith(piece, cur) ? cur : text.indexOf(piece, cur);
    if (at < 0 || at - cur > 20) return null;
    cur = at + piece.length;
    return [at, cur];
  });
}

async function runOpenMed(text: string, sensitivity: number): Promise<Span[]> {
  await loadOpenMed();
  const id2label = (model!.config as unknown as { id2label: Record<string, string> }).id2label;
  const oIdx = Number(Object.entries(id2label).find(([, l]) => l === "O")![0]);
  const out: Span[] = [];
  const parts = chunks(text, 1200);
  for (let c = 0; c < parts.length; c++) {
    const [off, chunk] = parts[c];
    const inputs = tok!(chunk, { truncation: true, max_length: 512 });
    const { logits } = (await model!(inputs)) as { logits: Tensor };
    const [, seq, nl] = logits.dims as number[];
    const data = logits.data as Float32Array;
    const ids = Array.from((inputs.input_ids as Tensor).data as BigInt64Array, Number);
    const offsets = align(chunk, tok!.model.convert_ids_to_tokens(ids));
    let cur: Span | null = null;
    for (let t = 0; t < seq; t++) {
      const o = offsets[t];
      if (!o) continue;
      const row = data.subarray(t * nl, (t + 1) * nl);
      const mx = Math.max(...row);
      const ex = Array.from(row, (v) => Math.exp(v - mx));
      const sum = ex.reduce((a, b) => a + b, 0);
      const pPii = 1 - ex[oIdx] / sum;
      let type: PiiType | null = null, fine = "";
      if (pPii >= sensitivity) {
        let best = -1, bi = -1;
        for (let k = 0; k < nl; k++) if (k !== oIdx && ex[k] > best) { best = ex[k]; bi = k; }
        fine = id2label[bi].replace(/^[BI]-/, "");
        type = FINE_TO_COARSE[fine] ?? "FIN_ID";
      }
      if (type && cur && cur.type === type && off + o[0] - cur.end <= 1) {
        cur.end = off + o[1]; cur.score = Math.max(cur.score ?? 0, pPii);
      } else {
        if (cur) out.push(cur);
        cur = type ? { start: off + o[0], end: off + o[1], type, source: "openmed", score: pPii, label: fine, why: [`OpenMed: ${fine.replace(/_/g, " ")} ${pPii.toFixed(2)}`], sources: ["openmed"] } : null;
      }
    }
    if (cur) out.push(cur);
    post({ kind: "progress", stage: "Scanning with OpenMed", pct: 45 + (25 * (c + 1)) / parts.length });
  }
  return out;
}

// ---------- GLiNER-PII (zero-shot span model) ----------
let gliner: Gliner | null = null;
async function runGliner(text: string, threshold: number): Promise<Span[]> {
  if (!gliner) {
    post({ kind: "progress", stage: "Loading GLiNER-PII model (first time only)", pct: 70 });
    gliner = new Gliner({
      tokenizerPath: "gliner",
      onnxSettings: { modelPath: `${MODEL_BASE}gliner/onnx/model_quint8.onnx`, executionProvider: "wasm",
        wasmPaths: ORT_GLINER, multiThread: true, maxThreads: navigator.hardwareConcurrency },
      transformersSettings: { allowLocalModels: true, useBrowserCache: true },
      maxWidth: 12, modelType: "span-level",
    });
    await gliner.initialize();
  }
  const labels = Object.keys(GLINER_LABELS);
  const out: Span[] = [];
  const parts = chunks(text, 1500);
  for (let c = 0; c < parts.length; c++) {
    const [off, chunk] = parts[c];
    const [res] = await gliner.inference({ texts: [chunk], entities: labels, threshold, flatNer: true });
    for (const e of res) out.push({ start: off + e.start, end: off + e.end, type: GLINER_LABELS[e.label], source: "gliner", score: e.score, label: e.label, why: [`GLiNER: ${e.label} ${e.score.toFixed(2)}`], sources: ["gliner"] });
    post({ kind: "progress", stage: "Scanning with GLiNER-PII", pct: 70 + (28 * (c + 1)) / parts.length });
  }
  return out;
}

self.onmessage = async (ev: MessageEvent<WorkerRequest>) => {
  const { text, mode, sensitivity } = ev.data;
  const t0 = performance.now();
  try {
    post({ kind: "progress", stage: "Applying pattern rules", pct: 2 });
    let spans: Span[] = detectRules(text);
    if (mode !== "rules") spans = spans.concat(await runOpenMed(text, sensitivity));
    if (mode === "thorough") spans = spans.concat(await runGliner(text, Math.max(0.15, sensitivity - 0.2)));
    post({ kind: "result", spans, ms: performance.now() - t0, versions: { rules: RULES_VERSION, ...(mode !== "rules" ? { openmed: "openmed-small" } : {}), ...(mode === "thorough" ? { gliner: "gliner-pii-base" } : {}) } });
  } catch (e) {
    post({ kind: "error", message: e instanceof Error ? e.message : String(e) });
  }
};
