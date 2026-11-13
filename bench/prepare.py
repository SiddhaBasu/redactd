"""Build eval + train sets in a common JSONL format: {id, source, domain, text, spans:[{start,end,label,tier}]}"""
import json, ast, random, pandas as pd
import os, sys
sys.path.insert(0, os.path.dirname(__file__)); os.chdir(os.path.join(os.path.dirname(__file__), ".."))
from taxonomy import tier
random.seed(0)
FIN = {"Banking", "User Account and Transaction Services", "Brokerage", "Credit", "Investment", "Mortgage", "Insurance"}

def norm_spans(spans, text):
    out = []
    for s in spans:
        t = tier(s["label"])
        if t is None or not (0 <= s["start"] < s["end"] <= len(text)):
            continue
        out.append({"start": s["start"], "end": s["end"], "label": s["label"], "tier": t})
    return out

def nemotron(split):
    df = pd.read_parquet(f"data/raw/nemotron_{split}.parquet")
    for r in df.itertuples():
        yield {"id": r.uid, "source": "nemotron", "domain": r.domain, "fmt": r.document_format,
               "text": r.text, "spans": norm_spans(ast.literal_eval(r.spans), r.text)}

def gretel_fin(split):
    df = pd.read_parquet(f"data/raw/gretel_fin_English_{split}.parquet")
    for i, r in enumerate(df.itertuples()):
        yield {"id": f"gf{split}{i}", "source": "gretel_fin", "domain": r.document_type, "fmt": "mixed",
               "text": r.generated_text, "spans": norm_spans(json.loads(r.pii_spans), r.generated_text)}

def dump(rows, path):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(path, len(rows))

# --- EVAL sets ---
nt = [r for r in nemotron("test") if r["spans"]]
fin_unstr = [r for r in nt if r["domain"] in FIN and r["fmt"] == "unstructured" and len(r["text"]) < 4000]
random.shuffle(fin_unstr)
dump(fin_unstr[:300], "data/processed/eval_nemotron_fin.jsonl")
gf = [r for r in gretel_fin("test") if r["spans"] and len(r["text"]) < 4000]
random.shuffle(gf)
dump(gf[:200], "data/processed/eval_gretel_fin.jsonl")

# --- TRAIN set (for DeBERTa fine-tune): Nemotron train only (Gretel kept as out-of-distribution test) ---
ntr = [r for r in nemotron("train") if r["spans"] and len(r["text"]) < 3000]
fin_tr = [r for r in ntr if r["domain"] in FIN]
other_tr = [r for r in ntr if r["domain"] not in FIN]
random.shuffle(fin_tr); random.shuffle(other_tr)
train = fin_tr[:5000] + other_tr[:3000]
random.shuffle(train)
dump(train, "data/processed/train_nemotron.jsonl")
