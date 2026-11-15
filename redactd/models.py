"""ONNX Runtime model wrappers used by the API.

TokenClassifierOnnx : DeBERTa-style token classifier (OpenMed-Small today, the distilled model after B1), int8 ONNX.
GlinerOnnx          : GLiNER-PII (Knowledgator, Apache-2.0) via the gliner package's ONNX runtime path.
Both return RawSpan(start, end, coarse_type, score, fine_label) with absolute character offsets in the ORIGINAL text.

Speed/recall notes (task C1):
  * the whole document is tokenised once and cut into overlapping token windows (stride 64), so an entity is never
    split at a chunk edge; each token takes its prediction from the window where it sits furthest from an edge
  * windows are length-sorted and run in padded batches through one session.run call per batch
  * sessions are created once and reused; intra-op threads are configurable (MODEL_THREADS)
  * glued text ("041316.75Corona Requena") is given virtual spaces before the model sees it, and offsets are mapped back
"""
from __future__ import annotations
import json, os, re
from typing import NamedTuple
import numpy as np

from .types import FINE_TO_COARSE, GLINER_LABELS
from . import lexicon as lex

class RawSpan(NamedTuple):
    start: int
    end: int
    type: str
    score: float
    label: str

_GLUE = re.compile(lex.GLUE_PATTERN, re.ASCII)

class Glued:
    """Text with a virtual space inserted at every digit/letter glue point, plus the offset map back."""
    def __init__(self, text: str):
        cuts = [m.start() for m in _GLUE.finditer(text)]
        self.cuts = np.asarray(cuts, dtype=np.int64)
        if cuts:
            parts, last = [], 0
            for c in cuts: parts.append(text[last:c]); parts.append(" "); last = c
            parts.append(text[last:]); self.text = "".join(parts)
            self.pos = self.cuts + np.arange(len(cuts))      # index of each inserted space in self.text
        else:
            self.text = text; self.pos = self.cuts
    def span(self, s: int, e: int) -> tuple[int, int]:
        if not len(self.pos): return s, e
        return (s - int(np.searchsorted(self.pos, s, "left")), e - int(np.searchsorted(self.pos, e, "left")))

def char_chunks(text: str, n: int, overlap: int):
    """Chunks of ~n chars cut at whitespace, each overlapping the previous by ~overlap chars. -> [(offset, chunk, cut_left, cut_right)]"""
    out, i, L = [], 0, len(text)
    while i < L:
        j = min(L, i + n)
        if j < L:
            k = text.rfind(" ", i + n // 2, j)
            j = k if k > 0 else j
        out.append((i, text[i:j], i > 0, j < L))
        if j >= L: break
        nxt = j - overlap
        k = text.find(" ", nxt, j)
        i = max(i + 1, k + 1 if k > 0 else nxt)
    return out

def _session(path: str, threads: int):
    import onnxruntime as ort
    so = ort.SessionOptions()
    if threads: so.intra_op_num_threads = threads; so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(path, so, providers=["CPUExecutionProvider"]), so

class TokenClassifierOnnx:
    def __init__(self, model_dir: str, threads: int = 0, file: str = "onnx/model_quantized.onnx", max_len: int = 512,
                 stride: int = 64, batch_tokens: int = 4096, glue: bool = True):
        from tokenizers import Tokenizer
        self.sess, _ = _session(os.path.join(model_dir, file), threads)
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.tok = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        self.tok.no_truncation(); self.tok.no_padding()
        cfg = json.load(open(os.path.join(model_dir, "config.json")))
        self.id2label = {int(k): v for k, v in cfg["id2label"].items()}
        self.o_idx = next(k for k, v in self.id2label.items() if v == "O")
        self.fine = [self.id2label[i].split("-", 1)[-1] for i in range(len(self.id2label))]
        self.coarse = [FINE_TO_COARSE.get(f, f if f in FINE_TO_COARSE.values() else "FIN_ID") for f in self.fine]
        self.cls, self.sep = self.tok.token_to_id("[CLS]"), self.tok.token_to_id("[SEP]")
        self.pad = self.tok.token_to_id("[PAD]") or 0
        self.body, self.stride, self.batch_tokens, self.glue = max_len - 2, stride, batch_tokens, glue

    def probs(self, ids: list[int], progress=None) -> np.ndarray:
        """Token-level class probabilities for an arbitrarily long id sequence, via overlapping batched windows."""
        n = len(ids); step = self.body - self.stride
        starts = list(range(0, max(1, n - self.stride), step)) if n > self.body else [0]
        wins = [(a, min(n, a + self.body)) for a in starts]
        out = np.zeros((n, len(self.id2label)), dtype=np.float32)
        order = sorted(range(len(wins)), key=lambda w: wins[w][1] - wins[w][0], reverse=True)
        i = done = 0
        while i < len(order):
            L = wins[order[i]][1] - wins[order[i]][0] + 2
            bs = max(1, self.batch_tokens // L); group = order[i:i + bs]; i += bs
            arr = np.full((len(group), L), self.pad, dtype=np.int64); att = np.zeros((len(group), L), dtype=np.int64)
            for r, w in enumerate(group):
                a, b = wins[w]; arr[r, 0] = self.cls; arr[r, 1:1 + b - a] = ids[a:b]; arr[r, 1 + b - a] = self.sep; att[r, :b - a + 2] = 1
            feed = {"input_ids": arr, "attention_mask": att}
            if "token_type_ids" in self.inputs: feed["token_type_ids"] = np.zeros_like(arr)
            logits = self.sess.run(None, feed)[0]
            for r, w in enumerate(group):
                a, b = wins[w]
                lo = a if w == 0 else a + self.stride // 2            # each token is owned by the window where it is central
                hi = b if w == len(wins) - 1 else wins[w + 1][0] + self.stride // 2
                x = logits[r, 1 + lo - a:1 + hi - a]
                ex = np.exp(x - x.max(-1, keepdims=True)); out[lo:hi] = ex / ex.sum(-1, keepdims=True)
            done += len(group)
            if progress: progress(done / len(wins))
        return out

    def __call__(self, text: str, sensitivity: float = 0.35, progress=None) -> list[RawSpan]:
        g = Glued(text) if self.glue else None
        enc = self.tok.encode(g.text if g else text, add_special_tokens=False)
        if not enc.ids: return []
        probs = self.probs(enc.ids, progress)
        p_pii = 1.0 - probs[:, self.o_idx]
        masked = probs.copy(); masked[:, self.o_idx] = -1.0
        best = masked.argmax(-1)
        out, cur = [], None       # cur = [start, end, type, score, label]
        for t, (a, b) in enumerate(enc.offsets):
            if a == b: continue
            p = float(p_pii[t]); typ = self.coarse[best[t]] if p >= sensitivity else None
            if typ and cur and cur[2] == typ and a - cur[1] <= 1:
                cur[1] = b
                if p > cur[3]: cur[3], cur[4] = p, self.fine[best[t]]
            else:
                if cur: out.append(cur)
                cur = [a, b, typ, p, self.fine[best[t]]] if typ else None
        if cur: out.append(cur)
        res = []
        for a, b, typ, p, lab in out:
            if g: a, b = g.span(a, b)
            if b > a: res.append(RawSpan(a, b, typ, p, lab))
        return res

OpenMedOnnx = TokenClassifierOnnx  # back-compat name

class GlinerOnnx:
    def __init__(self, model_dir: str, threads: int = 0, threshold_floor: float = 0.15, batch_size: int = 8, glue: bool = True):
        import onnxruntime as ort, torch
        from gliner import GLiNER
        if threads: torch.set_num_threads(threads)
        so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads: so.intra_op_num_threads = threads; so.inter_op_num_threads = 1
        self.m = GLiNER.from_pretrained(model_dir, load_onnx_model=True, onnx_model_file="onnx/model_quint8.onnx",
                                        local_files_only=True, runtime_options={"session_options": so})
        self.labels = list(GLINER_LABELS); self.floor, self.batch_size, self.glue = threshold_floor, batch_size, glue

    def __call__(self, text: str, sensitivity: float = 0.35, progress=None) -> list[RawSpan]:
        th = max(self.floor, sensitivity - 0.2)
        g = Glued(text) if self.glue else None
        parts = char_chunks(g.text if g else text, 1500, 200)
        out = []
        for i in range(0, len(parts), self.batch_size):
            batch = parts[i:i + self.batch_size]
            res = self.m.inference([c for _, c, _, _ in batch], self.labels, threshold=th, batch_size=self.batch_size)
            for (off, chunk, cut_l, cut_r), ents in zip(batch, res):
                for e in ents:
                    # an entity touching an internal chunk edge may be truncated; the neighbouring chunk has it whole
                    if (cut_l and e["start"] == 0) or (cut_r and e["end"] >= len(chunk)): continue
                    a, b = off + e["start"], off + e["end"]
                    if g: a, b = g.span(a, b)
                    if b > a: out.append(RawSpan(a, b, GLINER_LABELS[e["label"]], float(e["score"]), e["label"]))
            if progress: progress(min(1.0, (i + self.batch_size) / len(parts)))
        return out
