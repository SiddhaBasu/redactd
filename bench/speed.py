"""B1 speed check: ms per 1k characters, one process, MODEL_THREADS threads, same documents for every config.

    MODEL_THREADS=2 python bench/speed.py [--docs 100] [--set eval_gretel_fin]

Configs: distilled alone (Standard), OpenMed + GLiNER (the old Thorough), distilled + GLiNER (shipped Thorough),
OpenMed alone. Each config is warmed up on 3 documents, then timed over the same documents twice; the faster pass
counts. Pipeline post-processing is included (it is part of every request).
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from redactd.pipeline import Pipeline

ap = argparse.ArgumentParser(); ap.add_argument("--docs", type=int, default=100); ap.add_argument("--set", default="eval_gretel_fin")
a = ap.parse_args()
rows = [json.loads(l)["text"] for l in open(os.path.join(os.path.dirname(__file__), "..", "data", "eval", f"{a.set}.jsonl"))][:a.docs]
chars = sum(map(len, rows)); threads = int(os.getenv("MODEL_THREADS", "2"))
CONFIGS = [("distilled", ["distilled"]), ("openmed+gliner", ["openmed", "gliner"]), ("distilled+gliner", ["distilled", "gliner"]), ("openmed", ["openmed"])]
res = {}
for name, models in CONFIGS:
    p = Pipeline.from_env(threads=threads); p.modes["x"] = models; p.warm("x")
    for t in rows[:3]: p.detect(t, "x")
    best = 1e9
    for _ in range(2):
        t0 = time.perf_counter()
        for t in rows: p.detect(t, "x")
        best = min(best, time.perf_counter() - t0)
    res[name] = 1000 * best / chars * 1000
    print(f"{name:18s} {res[name]:7.1f} ms per 1k chars  ({best:.1f} s for {len(rows)} docs, {chars} chars, {threads} threads)", flush=True)
    del p
print(f"distilled vs openmed+gliner: {res['openmed+gliner'] / res['distilled']:.1f}x faster (target >= 2x)")
print(f"distilled+gliner vs openmed+gliner: {res['openmed+gliner'] / res['distilled+gliner']:.2f}x")
