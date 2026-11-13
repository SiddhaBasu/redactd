// Writes lib/models.manifest.json: SHA-256, size and path of every model file the on-device worker may load.
// The manifest ships INSIDE the app bundle (trusted origin), so a compromised model CDN cannot swap a file:
// the worker hashes every download and refuses anything that does not match (task E1).
//   node scripts/model-manifest.mjs [modelsDir=../../browser/models]
import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const dir = process.argv[2] || new URL("../../../browser/models", import.meta.url).pathname;
// model id -> files (relative to the model directory). Optional files are skipped when absent.
const MODELS = {
  "redactd-small": { kind: "token-classifier", licence: "MIT (microsoft/deberta-v3-xsmall) + our weights", files: ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "onnx/model_quantized.onnx"] },
  "openmed-small": { kind: "token-classifier", licence: "Apache-2.0 (OpenMed)", files: ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json", "onnx/model_quantized.onnx"] },
  gliner: { kind: "gliner", licence: "Apache-2.0 (knowledgator/gliner-pii-base-v1.0)", files: ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json", "gliner_config.json", "onnx/model_quint8.onnx"] },
};
const out = { models: {} };
for (const [id, m] of Object.entries(MODELS)) {
  if (!existsSync(join(dir, id))) continue;
  const files = {};
  for (const f of m.files) {
    const p = join(dir, id, f);
    if (!existsSync(p)) continue;
    files[f] = { sha256: createHash("sha256").update(readFileSync(p)).digest("hex"), bytes: statSync(p).size };
  }
  const bytes = Object.values(files).reduce((a, f) => a + f.bytes, 0);
  out.models[id] = { kind: m.kind, licence: m.licence, megabytes: Math.round(bytes / 1e5) / 10, files };
}
out.version = createHash("sha256").update(JSON.stringify(out.models)).digest("hex").slice(0, 12);
const target = new URL("../lib/models.manifest.json", import.meta.url).pathname;
writeFileSync(target, JSON.stringify(out, null, 1) + "\n");
console.log("wrote", target, Object.fromEntries(Object.entries(out.models).map(([k, v]) => [k, `${v.megabytes} MB`])), "version", out.version);
