"""python bench/run_eval.py <detector> [eval_set ...]  -> prints metrics, appends to bench/out/results.jsonl"""
import json, os, sys, time, torch
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(__file__), "..")
import detectors
from score import score_doc, aggregate
torch.set_num_threads(int(os.environ.get("THREADS", 1)))
name = sys.argv[1]
sets = sys.argv[2:] or ["eval_nemotron_fin", "eval_gretel_fin"]
limit = int(os.environ.get("LIMIT", 0))
DET = {
    "regex": detectors.regex, "presidio": detectors.presidio,
    "gliner_knowledgator": lambda: detectors.gliner("knowledgator/gliner-pii-base-v1.0"),
    "gliner_nvidia": lambda: detectors.gliner("nvidia/gliner-PII"),
    "openmed_base": lambda: detectors.openmed("Base-184M"), "openmed_small": lambda: detectors.openmed("Small-44M"),
    "deberta_ours": detectors.deberta_ours,
    "deberta_ours+regex": lambda: detectors.union(detectors.deberta_ours(), detectors.regex()),
    "slm_qwen1.5b": lambda: __import__("slm").SLMDetector(mode="solo", threads=int(os.environ.get("THREADS", 4))),
    "openmed_small+regex+slm_verify": lambda: __import__("slm").SLMDetector(mode="verify", threads=int(os.environ.get("THREADS", 4)),
        first_stage=detectors.union(detectors.openmed("Small-44M"), detectors.regex())),
    "openmed_small+regex": lambda: detectors.union(detectors.openmed("Small-44M"), detectors.regex()),
    "org_rules": detectors.org_rules,
    "gliner_org": detectors.gliner_org,
    "openmed_small_split": lambda: detectors.split_glued(detectors.openmed("Small-44M")),
    "gliner+regex": lambda: detectors.union(detectors.gliner("knowledgator/gliner-pii-base-v1.0"), detectors.regex()),
}
f = DET[name]()
for s in sets:
    rows = [json.loads(l) for l in open(f"{ROOT}/data/processed/{s}.jsonl")]
    if limit: rows = rows[:limit]
    per, preds_all, t0 = [], [], time.time()
    for r in rows:
        p = f(r["text"]); preds_all.append({"id": r["id"], "preds": p})
        per.append(score_doc(r["text"], r["spans"], p))
    dt = time.time() - t0
    chars = sum(len(r["text"]) for r in rows)
    res = {"detector": name, "eval": s, "docs": len(rows), **aggregate(per),
           "cpu_threads": torch.get_num_threads(), "ms_per_1k_chars": round(1000 * dt / chars * 1000, 2)}
    print(json.dumps(res), flush=True)
    with open(f"{ROOT}/bench/out/results.jsonl", "a") as fo: fo.write(json.dumps(res) + "\n")
    with open(f"{ROOT}/bench/out/preds_{name}_{s}.jsonl", "w") as fo:
        for x in preds_all: fo.write(json.dumps(x) + "\n")
