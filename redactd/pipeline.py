"""The detection pipeline: rules -> models -> finalize (merge, filters, propagate). Same stages as the browser worker.

    Pipeline.detect(text, mode) -> (list[Span], timings)

mode: 'rules' | 'standard' | 'thorough'. Which models each mode runs is data (MODES below), so swapping the
Standard model for the distilled one is a one-line change. Models load lazily and are shared across requests.
"""
from __future__ import annotations
import os, time
from . import rules
from .post import Span, Options, finalize, spans_json, trim_bounds  # noqa: F401  (re-exported)

MODEL_NAMES = {"openmed": "OpenMed", "gliner": "GLiNER", "distilled": "redactd-small"}
DEFAULT_MODES = {"rules": [], "standard": ["openmed"], "thorough": ["openmed", "gliner"]}

def _modes_from_env():
    """REDACTD_STANDARD / REDACTD_THOROUGH = comma-separated model names override the defaults."""
    m = {k: list(v) for k, v in DEFAULT_MODES.items()}
    for k in ("standard", "thorough"):
        v = os.getenv(f"REDACTD_{k.upper()}")
        if v is not None: m[k] = [x for x in v.split(",") if x]
    return m

class Pipeline:
    def __init__(self, openmed_dir: str | None = None, gliner_dir: str | None = None, threads: int = 0,
                 distilled_dir: str | None = None, modes: dict | None = None):
        self.dirs = {"openmed": openmed_dir, "gliner": gliner_dir, "distilled": distilled_dir}
        self.threads = threads; self.modes = modes or _modes_from_env(); self._models: dict = {}

    @classmethod
    def from_env(cls, threads: int | None = None):
        root = os.path.join(os.path.dirname(__file__), "..")
        return cls(os.getenv("OPENMED_DIR", os.path.join(root, "browser/models/openmed-small")),
                   os.getenv("GLINER_DIR", os.path.join(root, "browser/models/gliner")),
                   int(os.getenv("MODEL_THREADS", "0")) if threads is None else threads,
                   os.getenv("DISTILLED_DIR", os.path.join(root, "browser/models/redactd-small")))

    def model(self, name: str):
        if name not in self._models:
            from .models import TokenClassifierOnnx, GlinerOnnx
            d = self.dirs[name]
            self._models[name] = GlinerOnnx(d, self.threads) if name == "gliner" else TokenClassifierOnnx(d, self.threads)
        return self._models[name]

    def warm(self, mode: str):
        for n in self.modes[mode]: self.model(n)

    def versions(self) -> dict:
        return {"rules": rules.RULES_VERSION, **{n: os.path.basename(os.path.normpath(self.dirs[n] or "")) for ns in self.modes.values() for n in ns}}

    def detect_raw(self, text: str, mode: str = "thorough", sensitivity: float = 0.35, progress=None) -> tuple[list[Span], dict]:
        """Unmerged findings from every stage (used by detect() and by bench/calibrate.py)."""
        t0 = time.perf_counter(); timings = {}
        raw = [Span(s, e, t, "rules", None, rid, [rules.WHY[rid]], ["rules"]) for s, e, t, rid in rules.detect_detailed(text)]
        timings["rules_ms"] = (time.perf_counter() - t0) * 1000
        names = self.modes[mode]
        for k, name in enumerate(names):
            t = time.perf_counter(); disp = MODEL_NAMES[name]
            cb = (lambda f, k=k, disp=disp: progress(f"Scanning with {disp}", 100 * (k + f) / len(names))) if progress else None
            for sp in self.model(name)(text, sensitivity, cb):
                raw.append(Span(sp.start, sp.end, sp.type, name, sp.score, sp.label, [f"{disp}: {sp.label.replace('_', ' ')} {sp.score:.2f}"], [name]))
            timings[f"{name}_ms"] = (time.perf_counter() - t) * 1000
        return raw, timings

    def detect(self, text: str, mode: str = "thorough", sensitivity: float = 0.35, options: Options | None = None,
               progress=None) -> tuple[list[Span], dict]:
        t0 = time.perf_counter()
        raw, timings = self.detect_raw(text, mode, sensitivity, progress)
        if progress: progress("Merging findings", 99)
        t = time.perf_counter()
        o = options or Options(sensitivity=sensitivity)
        out = finalize(text, raw, o)
        timings["finalize_ms"] = (time.perf_counter() - t) * 1000
        timings["total_ms"] = (time.perf_counter() - t0) * 1000
        return out, timings
