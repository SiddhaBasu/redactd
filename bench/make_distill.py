"""B1 step 1+2: build the distillation corpus.

    python bench/make_distill.py [--nemotron 4500] [--gretel 4500]

Sources (TRAIN splits only; nothing from any eval or dev set):
  * Nemotron-PII train (data/processed/train_nemotron.jsonl, finance-weighted; CC-BY-4.0)
  * Gretel finance English train split (Apache-2.0)
  * synthetic hard cases from `bench/make_adversarial.py train` (templates + seeded values; no LLM)
Every document is labelled twice: its gold spans (mapped to the 10 coarse types, minus spans the gold policy
excludes) and the full shipped ensemble's document-level output (Thorough mode after merge, filters and
propagation). The student is trained on the union; where they overlap the gold type wins.
Output: data/processed/train_distill.jsonl  {id, source, text, spans: [[start, end, TYPE], ...]}
"""
import argparse, json, os, random, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from gold_policy import excluded
from taxonomy import tier
from redactd.coarse import COARSE
_P = None

def _init():
    global _P
    from redactd.pipeline import Pipeline
    _P = Pipeline.from_env(threads=1); _P.warm("thorough")

def _label(row):
    from redactd.post import Span, merge_spans
    text = row["text"]
    teacher, _ = _P.detect(text, "thorough")
    gold = [Span(g["start"], g["end"], COARSE[g["label"]], "rules") for g in row["spans"]
            if g["label"] in COARSE and not excluded(text[g["start"]:g["end"]], g["label"])]      # source "rules": gold wins the type
    both = merge_spans(text, gold + [Span(s.start, s.end, s.type, "teacher") for s in teacher if s.type != "CUSTOM"])
    return {"id": row["id"], "source": row["source"], "text": text, "spans": [[s.start, s.end, s.type] for s in both],
            "n_gold": len(gold), "n_teacher": len(teacher)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--nemotron", type=int, default=4500); ap.add_argument("--gretel", type=int, default=4500)
    a = ap.parse_args(); random.seed(11)
    evalids = set()
    for f in os.listdir(f"{ROOT}/data/eval"):
        if f.endswith(".jsonl"): evalids |= {json.loads(l)["id"] for l in open(f"{ROOT}/data/eval/{f}")}
    nem = [json.loads(l) for l in open(f"{ROOT}/data/processed/train_nemotron.jsonl")]; random.shuffle(nem); nem = nem[:a.nemotron]
    import pandas as pd
    df = pd.read_parquet(f"{ROOT}/data/raw/gretel_fin_English_train.parquet"); gf = []
    for i, r in enumerate(df.itertuples()):
        if len(r.generated_text) >= 3500: continue
        sp = [{"start": s["start"], "end": s["end"], "label": s["label"]} for s in json.loads(r.pii_spans) if tier(s["label"]) and 0 <= s["start"] < s["end"] <= len(r.generated_text)]
        gf.append({"id": f"gftrain{i}", "source": "gretel_fin", "text": r.generated_text, "spans": sp})
    random.shuffle(gf); gf = gf[:a.gretel]
    adv = [json.loads(l) for l in open(f"{ROOT}/data/processed/train_adversarial.jsonl")]
    rows = nem + gf + adv
    assert not ({r["id"] for r in rows} & evalids), "train/eval overlap"
    random.shuffle(rows)
    print(len(nem), "nemotron +", len(gf), "gretel-fin train +", len(adv), "adversarial-train =", len(rows), "docs", flush=True)
    out = f"{ROOT}/data/processed/train_distill.jsonl"; n = 0
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", os.cpu_count())), initializer=_init) as ex, open(out, "w") as f:
        for r in ex.map(_label, rows, chunksize=8):
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
            if n % 500 == 0: print(n, "labelled", flush=True)
    print("wrote", out)

if __name__ == "__main__":
    main()
