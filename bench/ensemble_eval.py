"""Score combinations of saved detector predictions (+ consistency propagation) without re-running models.
python bench/ensemble_eval.py eval_gretel_fin regex,openmed_small,gliner_knowledgator [--prop] [--miss]"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from score import score_doc, aggregate
from redactd.vault import propagate, merge
ROOT = os.path.join(os.path.dirname(__file__), "..")
ev, names = sys.argv[1], sys.argv[2].split(",")
rows = {json.loads(l)["id"]: json.loads(l) for l in open(f"{ROOT}/data/eval/{ev}.jsonl")}
if "--policy" in sys.argv:
    from gold_policy import excluded
    for r in rows.values(): r["spans"] = [g for g in r["spans"] if not excluded(r["text"][g["start"]:g["end"]], g["label"])]
preds = collections.defaultdict(list)
for n in names:
    for l in open(f"{ROOT}/bench/out/preds_{n}_{ev}.jsonl"):
        x = json.loads(l); preds[x["id"]] += [tuple(p) for p in x["preds"]]
per, miss = [], collections.Counter()
for i, r in rows.items():
    p = preds[i]
    if "--prop" in sys.argv: p = propagate(r["text"], merge(p))
    per.append(score_doc(r["text"], r["spans"], p))
    if "--miss" in sys.argv:
        import numpy as np
        m = np.zeros(len(r["text"]) + 1, bool)
        for s, e, *_ in p: m[s:e] = True
        for g in r["spans"]:
            if m[g["start"]:g["end"]].mean() < 0.5: miss[(g["tier"], g["label"])] += 1
print(json.dumps({"combo": "+".join(names), "prop": "--prop" in sys.argv, "policy": "--policy" in sys.argv, **aggregate(per)}))
if miss: print(miss.most_common(15))
