"""Build the held-out sets added in task A2 (deterministic; reads only data/raw, writes data/eval).

  eval_fin_holdout2            300 Gretel finance test docs not in eval_gretel_fin or eval_gretel_fin_holdout
  eval_nemotron_fin_structured 300 Nemotron test docs, finance domains, document_format == structured
  eval_gretel_en               300 docs from gretelai/gretel-pii-masking-en-v1 (general domain). Its labels are
                               entity strings, so spans are recovered by exact match at token boundaries; entities
                               that cannot be located, or that carry several types, are dropped as ambiguous.
The script never prints document text. Nobody should look at these documents while changing rules or thresholds.
"""
import ast, json, os, random, re, sys
import pandas as pd
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import tier
FIN = {"Banking", "User Account and Transaction Services", "Brokerage", "Credit", "Investment", "Mortgage", "Insurance"}
EV = f"{ROOT}/data/eval"

def ids(name): return {json.loads(l)["id"] for l in open(f"{EV}/{name}.jsonl")}
def dump(rows, name):
    with open(f"{EV}/{name}.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(name, len(rows), "docs", sum(len(r["spans"]) for r in rows), "spans")
def norm(spans, text):
    return [{"start": s["start"], "end": s["end"], "label": s["label"], "tier": tier(s["label"])} for s in spans
            if tier(s["label"]) and 0 <= s["start"] < s["end"] <= len(text)]

# 1. second Gretel finance hold-out
used = ids("eval_gretel_fin") | ids("eval_gretel_fin_holdout")
df = pd.read_parquet(f"{ROOT}/data/raw/gretel_fin_English_test.parquet"); out = []
for i, r in enumerate(df.itertuples()):
    rid = f"gftest{i}"
    if rid in used or len(r.generated_text) >= 4000: continue
    sp = norm(json.loads(r.pii_spans), r.generated_text)
    if sp: out.append({"id": rid, "source": "gretel_fin", "domain": r.document_type, "fmt": "mixed", "text": r.generated_text, "spans": sp})
random.seed(2); random.shuffle(out); assert not ({r["id"] for r in out[:300]} & used)
dump(out[:300], "eval_fin_holdout2")

# 2. Nemotron finance, structured format
df = pd.read_parquet(f"{ROOT}/data/raw/nemotron_test.parquet"); out = []
for r in df[(df.document_format == "structured") & df.domain.isin(FIN)].itertuples():
    if len(r.text) >= 4000: continue
    sp = norm(ast.literal_eval(r.spans), r.text)
    if sp: out.append({"id": r.uid, "source": "nemotron", "domain": r.domain, "fmt": "structured", "doc_type": r.document_type, "text": r.text, "spans": sp})
random.seed(3); random.shuffle(out)
dump(out[:300], "eval_nemotron_fin_structured")

# 3. Gretel general-domain: entity strings -> spans
RENAME = {"address": "street_address", "unique_identifier": "unique_id"}
df = pd.read_parquet(f"{ROOT}/data/raw/gretel_en_test.parquet"); out = []; dropped = kept = 0
# GitHub push protection blocks files containing strings in live provider token formats, even synthetic ones.
# Documents with such strings are left out of this committed set (4 of the first 300; noted in data/eval/README.md).
PROVIDER_TOKEN = re.compile(r"SG\.[\w-]{16,}\.[\w-]{16,}|sq0[a-z]{3}-[\w-]{20,}|EAAA[\w-]{40,}|xox[baprs]-[\w-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|sk_live_[0-9a-zA-Z]{20,}|AIza[\w-]{30,}")
for r in df.itertuples():
    if len(r.text) >= 4000 or PROVIDER_TOKEN.search(r.text): continue
    sp = []; ok = True
    for e in ast.literal_eval(r.entities):
        v = e["entity"]; types = [RENAME.get(t, t) for t in e["types"]]
        hits = [m.span() for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])", r.text)] if len(v) >= 2 else []
        if len(types) != 1 or not tier(types[0]) or not hits: dropped += 1; continue
        kept += 1
        sp += [{"start": a, "end": b, "label": types[0], "tier": tier(types[0])} for a, b in hits]
    sp = sorted({(s["start"], s["end"]): s for s in sp}.values(), key=lambda s: s["start"])
    if sp: out.append({"id": r.uid, "source": "gretel_en", "domain": r.domain, "fmt": "mixed", "doc_type": r.document_type, "text": r.text, "spans": sp})
random.seed(4); random.shuffle(out)
dump(out[:300], "eval_gretel_en")
print("gretel_en entities kept", kept, "dropped as ambiguous/unlocatable/untiered", dropped)

# 4. structured DEV set (tuning allowed), disjoint from the structured held-out set above
used = ids("eval_nemotron_fin_structured"); df = pd.read_parquet(f"{ROOT}/data/raw/nemotron_test.parquet"); out = []
for r in df[(df.document_format == "structured") & df.domain.isin(FIN)].itertuples():
    if len(r.text) >= 4000 or r.uid in used: continue
    sp = norm(ast.literal_eval(r.spans), r.text)
    if sp: out.append({"id": r.uid, "source": "nemotron", "domain": r.domain, "fmt": "structured", "doc_type": r.document_type, "text": r.text, "spans": sp})
random.seed(5); random.shuffle(out)
dump(out[:200], "dev_nemotron_fin_structured")
