"""One-command benchmark report for the SHIPPED pipeline (redactd.pipeline.Pipeline), not the bench wrappers.

    python bench/report.py                       # every eval set, Thorough mode -> bench/out/report.md + report.json
    python bench/report.py --mode standard --sets eval_gretel_fin,eval_adversarial --limit 50 --tag quick

For each set: entity recall per tier at >=50% / >=90% character coverage and character precision, on raw labels
and on policy-adjusted labels (bench/gold_policy.py), side by side; recall per coarse type, per fine label and per
document type; latency percentiles; and the leak regression (task A3): render every document with the shipped
redact(), require leak_check == [] and search the output for every gold DIRECT value.

Privacy/eval hygiene: this script never prints document text. `--miss` prints missed gold strings for DEV sets
only; for held-out sets it prints label counts, so held-out documents are never inspected while tuning.
"""
from __future__ import annotations
import argparse, collections, json, os, re, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from gold_policy import excluded
from redactd.coarse import COARSE
from redactd.types import DIRECT_TYPES

SETS = [  # (name, role, description)
    ("eval_gretel_fin_holdout", "held-out", "Gretel finance test, 300 docs — headline"),
    ("eval_fin_holdout2", "held-out", "Gretel finance test, 300 more docs, never inspected"),
    ("eval_nemotron_fin_structured", "held-out", "Nemotron finance, structured format, 300 docs"),
    ("eval_gretel_en", "held-out", "Gretel general-domain PII, 300 docs (labels recovered by exact match)"),
    ("eval_adversarial", "held-out", "Synthetic hard cases, 160 docs (half the templates unseen in training)"),
    ("eval_gretel_fin", "dev", "Gretel finance test, 200 docs — used for tuning"),
    ("eval_nemotron_fin", "dev", "Nemotron finance, unstructured, 300 docs — used for tuning; optimistic"),
    ("dev_nemotron_fin_structured", "dev", "Nemotron finance, structured, 200 docs — used for tuning"),
]
ROLE = {n: r for n, r, _ in SETS}
_P = None

def _init(mode, threads):
    global _P, _MODE
    from redactd.pipeline import Pipeline
    _P = Pipeline.from_env(threads=threads); _MODE = mode; _P.warm(mode)

def _run(row):
    from redactd.vault import redact, leak_check
    text = row["text"]
    spans, tm = _P.detect(text, _MODE)
    tup = [(s.start, s.end, s.type) for s in spans]
    out, vault = redact(text, tup)
    direct = sorted({text[g["start"]:g["end"]] for g in row["spans"] if g["tier"] == "direct"})
    return {"id": row["id"], "preds": [(s.start, s.end, s.type, s.source) for s in spans], "ms": tm["total_ms"],
            "stage_ms": {k: v for k, v in tm.items() if k != "total_ms"},
            "leak_check": len(leak_check(out, vault)),
            "gold_direct_in_output": sum(1 for v in direct if len(v.strip()) >= 2 and v in out), "gold_direct_values": len(direct)}

def load(name, limit=0):
    rows = [json.loads(l) for l in open(f"{ROOT}/data/eval/{name}.jsonl")]
    return rows[:limit] if limit else rows

def pct(a, n): return None if not n else 100.0 * a / n
def f1(x): return "–" if x is None else f"{x:.1f}"

def score_set(rows, results, policy):
    """Aggregate metrics. Returns dict with tiers, char precision, breakdowns."""
    tot = collections.Counter(); by = {k: collections.defaultdict(collections.Counter) for k in ("coarse", "label", "doctype", "tpl")}
    ptype = collections.defaultdict(collections.Counter)
    for row, res in zip(rows, results):
        text = row["text"]; n = len(text)
        gold = [g for g in row["spans"] if not (policy and excluded(text[g["start"]:g["end"]], g["label"]))]
        mask = np.zeros(n + 1, bool); gmask = np.zeros(n + 1, bool)
        for s, e, *_ in res["preds"]: mask[max(0, s):min(n, e)] = True
        for g in gold: gmask[g["start"]:g["end"]] = True
        tot["pred_chars"] += int(mask.sum()); tot["tp_chars"] += int((mask & gmask).sum())
        for s, e, t, *_ in res["preds"]:
            k = "direct" if t in DIRECT_TYPES else "indirect"
            for key in (t, "tier:" + k):
                ptype[key]["pred"] += e - s; ptype[key]["tp"] += int(gmask[s:e].sum())
        for g in gold:
            cov = mask[g["start"]:g["end"]].mean(); k = g["tier"]
            tot[f"{k}_n"] += 1; tot[f"{k}_r50"] += cov >= 0.5; tot[f"{k}_r90"] += cov >= 0.9
            keys = {"coarse": COARSE.get(g["label"], "OTHER"), "label": f'{k}:{g["label"]}', "doctype": row.get("doc_type") or row.get("domain") or "?"}
            if "tpl_in_train" in row: keys["tpl"] = "templates also rendered (other values) for training" if row["tpl_in_train"] else "templates never used in training"
            for dim, key in keys.items():
                c = by[dim][key]; c["n"] += 1; c["r50"] += cov >= 0.5; c["r90"] += cov >= 0.9
    out = {"char_precision": pct(tot["tp_chars"], tot["pred_chars"])}
    for k in ("direct", "indirect"):
        out[f"{k}_n"] = tot[f"{k}_n"]; out[f"{k}_r50"] = pct(tot[f"{k}_r50"], tot[f"{k}_n"]); out[f"{k}_r90"] = pct(tot[f"{k}_r90"], tot[f"{k}_n"])
    out["by"] = {dim: {key: {"n": c["n"], "r50": pct(c["r50"], c["n"]), "r90": pct(c["r90"], c["n"])} for key, c in d.items()} for dim, d in by.items()}
    out["precision_by_pred"] = {k: {"pred_chars": c["pred"], "precision": pct(c["tp"], c["pred"])} for k, c in ptype.items()}
    return out

def misses(rows, results, role, top=40):
    c = collections.Counter()
    for row, res in zip(rows, results):
        n = len(row["text"]); mask = np.zeros(n + 1, bool)
        for s, e, *_ in res["preds"]: mask[max(0, s):min(n, e)] = True
        for g in row["spans"]:
            if mask[g["start"]:g["end"]].mean() < 0.5:
                c[(g["tier"], g["label"], row["text"][g["start"]:g["end"]] if role == "dev" or row["source"] == "adversarial" else "<held-out: text withheld>")] += 1
    return c.most_common(top)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="thorough"); ap.add_argument("--sets", default="")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--threads", type=int, default=1); ap.add_argument("--tag", default="")
    ap.add_argument("--miss", action="store_true"); ap.add_argument("--save-preds", action="store_true")
    a = ap.parse_args()
    names = a.sets.split(",") if a.sets else [n for n, _, _ in SETS]
    t_start = time.time(); report = {"mode": a.mode, "sets": {}, "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "limit": a.limit}
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a.mode, a.threads)) as ex:
        list(ex.map(_warm, range(a.workers)))
        for name in names:
            rows = load(name, a.limit); t0 = time.time()
            results = list(ex.map(_run, rows, chunksize=4))
            wall = time.time() - t0; ms = sorted(r["ms"] for r in results); chars = sum(len(r["text"]) for r in rows)
            q = lambda p: ms[min(len(ms) - 1, int(p * len(ms)))]
            stage = collections.Counter()
            for r in results: stage.update(r["stage_ms"])
            report["sets"][name] = {
                "role": ROLE.get(name, "?"), "docs": len(rows), "chars": chars, "raw": score_set(rows, results, False), "policy": score_set(rows, results, True),
                "latency_ms": {"p50": q(.5), "p95": q(.95), "p99": q(.99), "mean": statistics.mean(ms), "per_1k_chars": 1000 * sum(ms) / chars,
                               "stage_share": {k: v / sum(ms) for k, v in stage.items()}},
                "wall_s": wall, "leak_check_failures": sum(r["leak_check"] for r in results),
                "gold_direct_in_output": sum(r["gold_direct_in_output"] for r in results), "gold_direct_values": sum(r["gold_direct_values"] for r in results),
                "docs_with_gold_direct_in_output": sum(1 for r in results if r["gold_direct_in_output"])}
            x = report["sets"][name]["raw"]
            print(f'{name:30s} direct {f1(x["direct_r50"])}/{f1(x["direct_r90"])} indirect {f1(x["indirect_r50"])}/{f1(x["indirect_r90"])} '
                  f'prec {f1(x["char_precision"])} policy-indirect {f1(report["sets"][name]["policy"]["indirect_r50"])}/{f1(report["sets"][name]["policy"]["indirect_r90"])} '
                  f'policy-prec {f1(report["sets"][name]["policy"]["char_precision"])} leaks {report["sets"][name]["leak_check_failures"]} wall {wall:.0f}s', flush=True)
            if a.miss:
                for k, v in misses(rows, results, ROLE.get(name, "?")): print("   miss", v, k)
            if a.save_preds:
                with open(f"{ROOT}/bench/out/preds_pipeline_{name}.jsonl", "w") as f:
                    for r in results: f.write(json.dumps({"id": r["id"], "preds": [p[:3] for p in r["preds"]]}) + "\n")
                for src in sorted({p[3].split("+")[0] for r in results for p in r["preds"]}):
                    pass
    report["total_wall_s"] = time.time() - t_start; report["workers"] = a.workers; report["threads_per_worker"] = a.threads
    sfx = f"_{a.tag}" if a.tag else ""
    os.makedirs(f"{ROOT}/bench/out", exist_ok=True)
    json.dump(report, open(f"{ROOT}/bench/out/report{sfx}.json", "w"), indent=1)
    open(f"{ROOT}/bench/out/report{sfx}.md", "w").write(render(report))
    print(f"wrote bench/out/report{sfx}.md in {report['total_wall_s']:.0f}s")

def _warm(_):
    _P.detect("Warm-up: John Smith, account 12345678.", _MODE); return 1

def render(rep):
    L = [f"# redactd benchmark report", "",
         f"Generated {rep['generated']} · mode **{rep['mode']}** · shipped `redactd.pipeline.Pipeline` · {rep['workers']} worker processes × {rep['threads_per_worker']} thread · "
         f"total wall time {rep['total_wall_s'] / 60:.1f} min" + (f" · LIMITED to first {rep['limit']} docs per set" if rep["limit"] else ""), "",
         "Recall = share of gold identifiers with ≥50% / ≥90% of their characters redacted. Precision = share of redacted characters that fall inside a gold span "
         "(Gretel leaves real PII unlabelled, so its precision understates reality). *Raw* uses dataset labels as-is; *policy* removes gold spans that are template "
         "placeholders and, for organisation labels only, generic phrases and public bodies (`bench/gold_policy.py`).", "",
         "**Held-out** sets are never used to tune rules, thresholds or prompts. **Dev** sets are.", "",
         "## Summary", "",
         "| Set | Role | Docs | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Direct ≥50 pol | Direct ≥90 pol | Indirect ≥50 pol | Indirect ≥90 pol | Prec pol |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n, s in rep["sets"].items():
        r, p = s["raw"], s["policy"]
        L.append(f'| {n} | {s["role"]} | {s["docs"]} | {f1(r["direct_r50"])} | {f1(r["direct_r90"])} | {f1(r["indirect_r50"])} | {f1(r["indirect_r90"])} | {f1(r["char_precision"])} | '
                 f'{f1(p["direct_r50"])} | {f1(p["direct_r90"])} | {f1(p["indirect_r50"])} | {f1(p["indirect_r90"])} | {f1(p["char_precision"])} |')
    L += ["", "## Leak regression (A3)", "",
          "`leak_check` must be empty for every rendered document. *Gold direct values in output* is a raw string search of the redacted output for every gold DIRECT value; "
          "it counts every miss and also short values that survive as substrings of unrelated words.", "",
          "| Set | leak_check failures | Gold direct values still in output | of | Docs affected |", "|---|---:|---:|---:|---:|"]
    for n, s in rep["sets"].items():
        L.append(f'| {n} | {s["leak_check_failures"]} | {s["gold_direct_in_output"]} | {s["gold_direct_values"]} | {s["docs_with_gold_direct_in_output"]} / {s["docs"]} |')
    L += ["", "## Latency (per document, measured inside the worker; all workers busy)", "", "| Set | mean chars | p50 ms | p95 ms | p99 ms | ms / 1k chars | stage share |", "|---|---:|---:|---:|---:|---:|---|"]
    for n, s in rep["sets"].items():
        l = s["latency_ms"]
        L.append(f'| {n} | {s["chars"] // max(1, s["docs"])} | {l["p50"]:.0f} | {l["p95"]:.0f} | {l["p99"]:.0f} | {l["per_1k_chars"]:.0f} | '
                 + ", ".join(f'{k[:-3]} {v:.0%}' for k, v in l["stage_share"].items()) + " |")
    for n, s in rep["sets"].items():
        L += ["", f"## {n} ({s['role']})", ""]
        for dim, title in (("coarse", "Recall per coarse type (raw labels)"), ("label", "Recall per fine label (raw labels)"), ("doctype", "Recall per document type (raw labels)"), ("tpl", "Recall by template exposure")):
            d = s["raw"]["by"].get(dim) or {}
            if not d: continue
            items = sorted(d.items(), key=lambda kv: -kv[1]["n"])
            if dim == "doctype" and len(items) > 25: items = items[:25]
            L += [f"### {title}", "", "| | n | ≥50% | ≥90% |", "|---|---:|---:|---:|"]
            L += [f'| {k} | {v["n"]} | {f1(v["r50"])} | {f1(v["r90"])} |' for k, v in items] + [""]
        pp = s["policy"]["precision_by_pred"]
        L += ["### Character precision by predicted type (policy-adjusted gold)", "", "| predicted | chars | precision |", "|---|---:|---:|"]
        L += [f'| {k} | {v["pred_chars"]} | {f1(v["precision"])} |' for k, v in sorted(pp.items(), key=lambda kv: -kv[1]["pred_chars"])]
    notes = os.path.join(ROOT, "bench", "report_notes.md")
    if os.path.exists(notes): L += ["", open(notes).read().rstrip()]
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    main()
