"""ONNX Runtime model wrappers used by the API (no PyTorch needed for OpenMed).

OpenMedOnnx : DeBERTa token classifier (OpenMed-PII-SuperClinical-Small), int8 ONNX, offsets from HF tokenizers.
GlinerOnnx  : GLiNER-PII (Knowledgator, Apache-2.0) via the gliner package's ONNX runtime path.
Both return spans as (start, end, coarse_type, score) with absolute character offsets.
"""
from __future__ import annotations
import json, os
import numpy as np

from .types import FINE_TO_COARSE, GLINER_LABELS

def chunks(text: str, n: int):
    i = 0
    while i < len(text):
        j = min(len(text), i + n)
        if j < len(text):
            k = text.rfind(" ", i + n // 2, j)
            j = k if k > 0 else j
        yield i, text[i:j]
        i = j

class OpenMedOnnx:
    def __init__(self, model_dir: str, threads: int = 0):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        so = ort.SessionOptions()
        if threads: so.intra_op_num_threads = threads
        path = os.path.join(model_dir, "onnx", "model_quantized.onnx")
        self.sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        self.tok.enable_truncation(512)
        cfg = json.load(open(os.path.join(model_dir, "config.json")))
        self.id2label = {int(k): v for k, v in cfg["id2label"].items()}
        self.o_idx = next(k for k, v in self.id2label.items() if v == "O")

    def __call__(self, text: str, sensitivity: float = 0.35):
        out = []
        for off, chunk in chunks(text, 1200):
            enc = self.tok.encode(chunk)
            ids = np.array([enc.ids], dtype=np.int64)
            logits = self.sess.run(None, {"input_ids": ids, "attention_mask": np.ones_like(ids)})[0][0]
            ex = np.exp(logits - logits.max(-1, keepdims=True)); probs = ex / ex.sum(-1, keepdims=True)
            cur = None
            for t, (a, b) in enumerate(enc.offsets):
                if a == b:
                    continue
                p_pii = 1 - probs[t, self.o_idx]
                typ = None
                if p_pii >= sensitivity:
                    pr = probs[t].copy(); pr[self.o_idx] = -1
                    typ = FINE_TO_COARSE.get(self.id2label[int(pr.argmax())].split("-", 1)[-1], "FIN_ID")
                if typ and cur and cur[2] == typ and off + a - cur[1] <= 1:
                    cur = (cur[0], off + b, typ, max(cur[3], float(p_pii)))
                else:
                    if cur: out.append(cur)
                    cur = (off + a, off + b, typ, float(p_pii)) if typ else None
            if cur: out.append(cur)
        return out

class GlinerOnnx:
    def __init__(self, model_dir: str, threshold_floor: float = 0.15):
        from gliner import GLiNER
        self.m = GLiNER.from_pretrained(model_dir, load_onnx_model=True, onnx_model_file="onnx/model_quint8.onnx",
                                        local_files_only=True)
        self.labels = list(GLINER_LABELS)
        self.floor = threshold_floor

    def __call__(self, text: str, sensitivity: float = 0.35):
        th = max(self.floor, sensitivity - 0.2)
        out = []
        for off, chunk in chunks(text, 1500):
            for e in self.m.predict_entities(chunk, self.labels, threshold=th):
                out.append((off + e["start"], off + e["end"], GLINER_LABELS[e["label"]], float(e["score"])))
        return out
