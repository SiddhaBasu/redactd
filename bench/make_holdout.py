"""Build eval_gretel_fin_holdout: 300 Gretel finance test docs NOT in eval_gretel_fin (which was used for tuning)."""
import json, os, random, sys
import pandas as pd
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from redactd.coarse import COARSE  # noqa: F401  (ensures package importable)
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import tier
used = {json.loads(l)["id"] for l in open(f"{ROOT}/data/eval/eval_gretel_fin.jsonl")}
df = pd.read_parquet(f"{ROOT}/data/raw/gretel_fin_English_test.parquet"); out = []
for i, r in enumerate(df.itertuples()):
    rid = f"gftest{i}"
    if rid in used or len(r.generated_text) >= 4000: continue
    sp = [{"start": s["start"], "end": s["end"], "label": s["label"], "tier": tier(s["label"])}
          for s in json.loads(r.pii_spans) if tier(s["label"])]
    if sp: out.append({"id": rid, "source": "gretel_fin", "domain": r.document_type, "text": r.generated_text, "spans": sp})
random.seed(1); random.shuffle(out)
with open(f"{ROOT}/data/eval/eval_gretel_fin_holdout.jsonl", "w") as f:
    for r in out[:300]: f.write(json.dumps(r) + "\n")
print(len(out[:300]), "holdout docs")
