"""The detection pipeline: rules -> models -> merge -> propagate. Same stages as the browser worker."""
from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from . import rules
from .vault import merge, propagate

@dataclass
class Span:
    start: int
    end: int
    type: str
    source: str
    score: float | None = None

class Pipeline:
    """mode: 'rules' | 'standard' (+OpenMed) | 'thorough' (+GLiNER). Models load lazily and are shared."""
    def __init__(self, openmed_dir: str | None, gliner_dir: str | None, threads: int = 0):
        self.openmed_dir, self.gliner_dir, self.threads = openmed_dir, gliner_dir, threads
        self._openmed = self._gliner = None

    @property
    def openmed(self):
        if self._openmed is None:
            from .models import OpenMedOnnx
            self._openmed = OpenMedOnnx(self.openmed_dir, self.threads)
        return self._openmed

    @property
    def gliner(self):
        if self._gliner is None:
            from .models import GlinerOnnx
            self._gliner = GlinerOnnx(self.gliner_dir)
        return self._gliner

    def warm(self, mode: str):
        if mode in ("standard", "thorough"): self.openmed
        if mode == "thorough": self.gliner

    def detect(self, text: str, mode: str = "thorough", sensitivity: float = 0.35) -> tuple[list[Span], dict]:
        t0 = time.perf_counter(); timings = {}
        raw = [Span(s, e, t, "rules") for s, e, t in rules.detect(text) + rules.detect_org(text)]
        timings["rules_ms"] = (time.perf_counter() - t0) * 1000
        if mode in ("standard", "thorough"):
            t = time.perf_counter()
            raw += [Span(s, e, ty, "openmed", sc) for s, e, ty, sc in self.openmed(text, sensitivity)]
            timings["openmed_ms"] = (time.perf_counter() - t) * 1000
        if mode == "thorough":
            t = time.perf_counter()
            raw += [Span(s, e, ty, "gliner", sc) for s, e, ty, sc in self.gliner(text, sensitivity)]
            timings["gliner_ms"] = (time.perf_counter() - t) * 1000
        # merge overlapping spans, then redact every other occurrence of each value (consistency)
        raw = [x for x in (trim(text, sp) for sp in raw) if x.end > x.start]
        merged = propagate(text, merge([(s.start, s.end, s.type) for s in raw]))
        src = sorted(raw, key=lambda s: s.start)
        out = []
        for s, e, t in merged:
            contrib = [x for x in src if x.start < e and x.end > s]
            rule = next((x for x in contrib if x.source == "rules"), None)  # validated rules win on type
            t = rule.type if rule else t
            out.append(Span(s, e, t, contrib[0].source if contrib else "propagated",
                            max((x.score or 0 for x in contrib), default=None) or None))
        out = [x for x in (trim(text, sp) for sp in out) if x.end > x.start]
        timings["total_ms"] = (time.perf_counter() - t0) * 1000
        return out, timings

def trim(text: str, sp: Span) -> Span:
    """Tokenizer offsets can include the leading space or trailing punctuation; strip them."""
    s, e = sp.start, sp.end
    while s < e and (text[s].isspace() or text[s] in ",;:"): s += 1
    while e > s and (text[e - 1].isspace() or text[e - 1] in ",;:"): e -= 1
    sp.start, sp.end = s, e
    return sp

def spans_json(spans):
    return [asdict(s) for s in spans]
