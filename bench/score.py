"""Label-agnostic redaction scoring. For redaction, what matters is whether the characters got covered.
Entity recall@50: gold span counts as caught if >=50% of its chars are covered by predictions.
Entity recall@90 (strict): >=90% covered.  Char precision: share of predicted chars inside any gold span."""
import numpy as np

def score_doc(text, gold, preds):
    mask = np.zeros(len(text) + 1, bool)
    for s, e, *_ in preds: mask[max(0, s):min(len(text), e)] = True
    gmask = np.zeros(len(text) + 1, bool)
    for g in gold: gmask[g["start"]:g["end"]] = True
    res = {"pred_chars": int(mask.sum()), "tp_chars": int((mask & gmask).sum())}
    for g in gold:
        cov = mask[g["start"]:g["end"]].mean()
        k = g["tier"]
        res[f"{k}_n"] = res.get(f"{k}_n", 0) + 1
        res[f"{k}_r50"] = res.get(f"{k}_r50", 0) + (cov >= 0.5)
        res[f"{k}_r90"] = res.get(f"{k}_r90", 0) + (cov >= 0.9)
    return res

def aggregate(per_doc):
    tot = {}
    for r in per_doc:
        for k, v in r.items(): tot[k] = tot.get(k, 0) + v
    out = {}
    for k in ("direct", "indirect"):
        n = tot.get(f"{k}_n", 0)
        out[f"{k}_recall50"] = round(tot.get(f"{k}_r50", 0) / n, 4) if n else None
        out[f"{k}_recall90"] = round(tot.get(f"{k}_r90", 0) / n, 4) if n else None
        out[f"{k}_n"] = n
    out["char_precision"] = round(tot["tp_chars"] / tot["pred_chars"], 4) if tot.get("pred_chars") else None
    return out
