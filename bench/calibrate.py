"""B2: per-source, per-type confidence thresholds, calibrated on DEV sets only.

For each (source, predicted type) pick the HIGHEST threshold such that, on every dev set,
  * recall (>=50% and >=90% coverage) of every gold coarse type stays >= 99% of its unthresholded value, and
  * neither tier (direct / indirect) loses more than TIER_BUDGET points in total across all thresholds chosen so far.
Greedy, one (source, type) at a time, largest precision gain first. Prints a table and, with --write, stores the
result in redactd/lexicon.py (THRESHOLDS). Requires `python bench/devtools.py cache` first.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
import devtools
from redactd.post import Options
from redactd.coarse import TYPES
GRID = [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
MIN_GAIN = 0.3          # keep a threshold only if it buys this many points of precision on some dev set
TIER_BUDGET = 0.12      # points of tier recall we allow thresholds to cost on any dev set, in total

def metrics(data, th, solo=None):
    return {n: devtools.score(d, Options(thresholds=th, solo_thresholds=solo)) for n, d in data.items()}

SOLO_GRID = [0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 1.01]
def solo():
    """`python bench/calibrate.py solo [--write]`: per (source, fine label) threshold for findings nothing else supports."""
    data = {n: devtools.raw_spans(n) for n in devtools.DEV}
    from redactd import lexicon as lex
    import collections
    vol = collections.Counter((s.source, s.label) for d in data.values() for _, sp in d for s in sp if s.score is not None)
    th = {}; base = metrics(data, None, {}); prev = base
    print("base", {n: (base[n].get("direct"), base[n].get("indirect"), base[n]["precision"]) for n in base})
    for (src, lab), _ in vol.most_common():
        best = None
        for g in SOLO_GRID:
            trial = {k: dict(v) for k, v in th.items()}; trial.setdefault(src, {})[lab] = g
            cur = metrics(data, None, trial)
            if ok(base, cur): best = (g, cur)
            else: break
        gain = max(best[1][n]["precision"] - prev[n]["precision"] for n in data) if best else 0
        if best and gain >= 0.1:
            th.setdefault(src, {})[lab] = best[0]; prev = best[1]
            print(f"{src:9s} {lab:24s} solo >= {best[0]:.2f}   precision " + " ".join(f'{n[:14]} {best[1][n]["precision"]:.1f}' for n in data), flush=True)
    fin = metrics(data, None, th)
    print("final", {n: (fin[n].get("direct"), fin[n].get("indirect"), fin[n]["precision"]) for n in fin}); print(json.dumps(th, sort_keys=True))
    if "--write" in sys.argv:
        p = os.path.join(HERE, "..", "redactd", "lexicon.py"); s = open(p, encoding="utf-8").read()
        s = re.sub(r"SOLO_THRESHOLDS: dict = \{.*\}\n", "SOLO_THRESHOLDS: dict = " + json.dumps(th, sort_keys=True) + "\n", s)
        open(p, "w", encoding="utf-8").write(s); print("wrote SOLO_THRESHOLDS to redactd/lexicon.py")

def ok(base, cur):
    for n in base:
        for k, v in base[n].items():
            if k in ("precision", "ptype"): continue
            c = cur[n].get(k, (0, 0, 0))
            if k in ("direct", "indirect"):
                if c[1] < v[1] - TIER_BUDGET or c[2] < v[2] - TIER_BUDGET: return False
            elif c[1] < 0.99 * v[1] or c[2] < 0.99 * v[2]: return False
    return True

def main():
    data = {n: devtools.raw_spans(n) for n in devtools.DEV}
    sources = sorted({s.source for d in data.values() for _, sp in d for s in sp if s.score is not None})
    th = {s: {} for s in sources}; base = metrics(data, th); prev = base
    print("base", {n: (base[n].get("direct"), base[n].get("indirect"), base[n]["precision"]) for n in base})
    for src in sources:
        for t in TYPES:
            best = None
            for g in GRID:
                trial = {s: dict(v) for s, v in th.items()}; trial[src][t] = g
                cur = metrics(data, trial)
                if ok(base, cur): best = (g, cur)
                else: break
            gain = max(best[1][n]["precision"] - prev[n]["precision"] for n in data) if best else 0
            if best and gain < MIN_GAIN: print(f"{src:9s} {t:12s} >= {best[0]:.2f}   skipped: gain {gain:.2f} < {MIN_GAIN}", flush=True); best = None
            if best:
                th[src][t] = best[0]; prev = best[1]
                print(f"{src:9s} {t:12s} >= {best[0]:.2f}   precision " + " ".join(f'{n[:14]} {best[1][n]["precision"]:.1f}' for n in data), flush=True)
    fin = metrics(data, th)
    print("final", {n: (fin[n].get("direct"), fin[n].get("indirect"), fin[n]["precision"]) for n in fin})
    print(json.dumps(th, indent=1))
    if "--write" in sys.argv:
        p = os.path.join(HERE, "..", "redactd", "lexicon.py"); s = open(p, encoding="utf-8").read()
        th = {k: v for k, v in th.items() if v}
        s = re.sub(r"THRESHOLDS: dict = \{.*\}\n", "THRESHOLDS: dict = " + json.dumps(th, sort_keys=True) + "\n", s)
        open(p, "w", encoding="utf-8").write(s); print("wrote THRESHOLDS to redactd/lexicon.py")

if __name__ == "__main__":
    solo() if "solo" in sys.argv else main()
