"""Fast iteration on DEV sets: cache raw (unmerged) model + rule findings once, then re-run only the cheap
post-processing (redactd.post.finalize) to try rules, filters and thresholds in seconds.

    python bench/devtools.py cache [sets...]         # run models once per dev doc -> bench/out/raw_<set>.jsonl
    python bench/devtools.py eval [--miss N] [--fp N] [--norules] [sets...]

Refuses to run on held-out sets: they must never be inspected or tuned on.
"""
from __future__ import annotations
import collections, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from gold_policy import excluded
from redactd import rules
from redactd.coarse import COARSE
from redactd.post import Span, Options, finalize
from redactd.types import DIRECT_TYPES
DEV = ["eval_gretel_fin", "eval_nemotron_fin", "dev_nemotron_fin_structured"]
_P = None

def _init():
    global _P
    from redactd.pipeline import Pipeline
    _P = Pipeline.from_env(threads=1); _P.warm("thorough")

def _raw(row):
    raw, _ = _P.detect_raw(row["text"], "thorough", 0.2)       # low floor so thresholds can be explored upward
    return {"id": row["id"], "raw": [[s.start, s.end, s.type, s.source, s.score, s.label] for s in raw if s.source != "rules"]}

def load(name):
    assert name in DEV, f"{name} is not a dev set"
    return [json.loads(l) for l in open(f"{ROOT}/data/eval/{name}.jsonl")]

def cache(names):
    with ProcessPoolExecutor(os.cpu_count(), initializer=_init) as ex:
        for n in names:
            rows = load(n)
            with open(f"{ROOT}/bench/out/raw_{n}.jsonl", "w") as f:
                for r in ex.map(_raw, rows, chunksize=4): f.write(json.dumps(r) + "\n")
            print("cached", n, flush=True)

def raw_spans(name, sensitivity=0.35, floor=0.15, with_rules=True):
    """-> [(row, [Span])] with the same score cut-offs the shipped pipeline applies at the default sensitivity."""
    rows = load(name); raws = [json.loads(l) for l in open(f"{ROOT}/bench/out/raw_{name}.jsonl")]
    assert [x["id"] for x in raws] == [r["id"] for r in rows], "stale cache: re-run `devtools.py cache`"
    out = []
    for r, x in zip(rows, raws):
        sp = [Span(s, e, t, "rules", None, rid, [], ["rules"]) for s, e, t, rid in rules.detect_detailed(r["text"])] if with_rules else []
        for s, e, t, src, sc, lab in x["raw"]:
            if sc >= (max(floor, sensitivity - 0.2) if src == "gliner" else sensitivity): sp.append(Span(s, e, t, src, sc, lab, [], [src]))
        out.append((r, sp))
    return out

def score(data, opts=None, policy=False):
    """-> metrics dict: tiers, per-coarse-type recall, char precision, per-predicted-type precision."""
    tot = collections.Counter(); bt = collections.defaultdict(collections.Counter); pt = collections.defaultdict(collections.Counter)
    for r, sp in data:
        text = r["text"]; n = len(text); fin = finalize(text, sp, opts or Options())
        gold = [g for g in r["spans"] if not (policy and excluded(text[g["start"]:g["end"]], g["label"]))]
        m = np.zeros(n + 1, bool); gm = np.zeros(n + 1, bool)
        for s in fin: m[s.start:s.end] = True
        for g in gold: gm[g["start"]:g["end"]] = True
        tot["pred"] += int(m.sum()); tot["tp"] += int((m & gm).sum())
        for s in fin: pt[s.type]["pred"] += s.end - s.start; pt[s.type]["tp"] += int(gm[s.start:s.end].sum())
        for g in gold:
            cov = m[g["start"]:g["end"]].mean(); k = g["tier"]; c = COARSE.get(g["label"], "OTHER")
            for key in (k, c): bt[key]["n"] += 1; bt[key]["r50"] += cov >= .5; bt[key]["r90"] += cov >= .9
    res = {k: (v["n"], round(100 * v["r50"] / v["n"], 2), round(100 * v["r90"] / v["n"], 2)) for k, v in bt.items()}
    res["precision"] = round(100 * tot["tp"] / max(1, tot["pred"]), 2)
    res["ptype"] = {k: (v["pred"], round(100 * v["tp"] / max(1, v["pred"]), 1)) for k, v in sorted(pt.items(), key=lambda kv: -kv[1]["pred"])}
    return res

def show(name, data, opts=None, miss=0, fp=0):
    for pol in (False, True):
        r = score(data, opts, pol)
        print(f'{name:28s} {"policy" if pol else "raw   "} direct {r.get("direct", (0, 0, 0))[1:]} indirect {r.get("indirect", (0, 0, 0))[1:]} prec {r["precision"]}')
    print("   recall", {k: v for k, v in sorted(r.items()) if k.isupper()}); print("   prec  ", r["ptype"])
    if miss or fp:
        mc, fc = collections.Counter(), collections.Counter()
        for row, sp in data:
            text = row["text"]; n = len(text); fin = finalize(text, sp, opts or Options())
            m = np.zeros(n + 1, bool); gm = np.zeros(n + 1, bool)
            for s in fin: m[s.start:s.end] = True
            for g in row["spans"]:
                gm[g["start"]:g["end"]] = True
                if m[g["start"]:g["end"]].mean() < 0.9: mc[(g["label"], text[g["start"]:g["end"]][:60], row.get("doc_type") or row["domain"])] += 1
            for s in fin:
                if gm[s.start:s.end].mean() < 0.5: fc[(s.type, "+".join(s.sources), text[s.start:s.end][:50])] += 1
        for k, v in mc.most_common(miss): print("   MISS", v, k)
        for k, v in fc.most_common(fp): print("   FP  ", v, k)

if __name__ == "__main__":
    cmd = sys.argv[1]; args = sys.argv[2:]
    def opt(flag):
        if flag in args: i = args.index(flag); v = int(args[i + 1]); del args[i:i + 2]; return v
        return 0
    miss, fp = opt("--miss"), opt("--fp"); norules = "--norules" in args
    names = [a for a in args if not a.startswith("--")] or DEV
    if cmd == "cache": cache(names)
    else:
        for n in names: show(n, raw_spans(n, with_rules=not norules), None, miss, fp)
