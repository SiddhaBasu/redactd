// Copies ONNX Runtime WASM binaries into public/ so the app never loads code from a CDN.
import { cpSync, mkdirSync, readdirSync } from "node:fs";
const jobs = [
  ["node_modules/@huggingface/transformers/dist", "public/ort", (f) => f.startsWith("ort-wasm")],
  ["node_modules/gliner/node_modules/onnxruntime-web/dist", "public/ort-gliner", (f) => /^ort-wasm.*\.(wasm|mjs)$/.test(f)],
];
for (const [src, dst, keep] of jobs) {
  mkdirSync(dst, { recursive: true });
  for (const f of readdirSync(src).filter(keep)) cpSync(`${src}/${f}`, `${dst}/${f}`);
  console.log(dst, readdirSync(dst).length, "files");
}
