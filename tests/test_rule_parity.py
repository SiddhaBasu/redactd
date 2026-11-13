"""A4: the Python and TypeScript pipelines must return identical spans.

Runs redactd.rules + redactd.post.finalize + vault.redact (Python) and lib/rules.ts + lib/redact.ts (Node) on every
fixture and every eval document and compares: rule spans, final spans (after merge / filters / propagation), the
rendered output and the leak check. Gold spans stand in for model output so the merge and coreference code is
exercised with realistic names. Also checks that rules.generated.json is up to date.

Intentional differences: none. (Python offsets are code points, JS offsets are UTF-16; the Node script converts.)
"""
import glob, json, os, shutil, subprocess, sys, tempfile
import pytest
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from redactd import rules
from redactd.coarse import COARSE
from redactd.post import Span, Options, finalize
from redactd.vault import redact, leak_check

EXTRA = [  # hand-written edge cases: astral characters, non-breaking spaces, odd whitespace, coreference forms
    "Pay 😀 John Smith 💳 4111 1111 1111 1111 then call +44 20 7946 0958 😀😀 IBAN GB82 WEST 1234 5698 7654 32.",
    "Name: Priya Raman SSN 123-45-6789 ZIP 83702\nP. Raman / PR / RAMAN / Raman’s / praman42 / priya.raman@x.io",
    "Mr. Art Banks wrote the Article. ART BANKS. Bill to: Bill Stone. BILL STONE's bill. FY2025, Q3 2025, the SEC and Acme Bank.",
    "acct ending 4471; card ****4471; XXXX-XXXX-XXXX-4471; last four 4471; password: hunter2\ttab\x0bvt\x1cfs 90210",
    "", "\n", "x",
]
OPTION_SETS = [{}, {"keep_last4": True, "custom_terms": ["Project Falcon", "wire"], "allow_terms": ["Royal Bank of Canada"], "exclude_types": ["DATE"]},
               {"org_allowlist": False, "drop_nonpersonal_dates": False}]
TS_OPTS = {"keep_last4": "keepLast4", "custom_terms": "customTerms", "allow_terms": "allowTerms", "exclude_types": "excludeTypes",
           "org_allowlist": "orgAllowlist", "drop_nonpersonal_dates": "dropNonpersonalDates"}

def docs():
    out = []
    for p in sorted(glob.glob(f"{ROOT}/tests/fixtures/*.txt")):
        out.append({"id": os.path.basename(p), "text": open(p, encoding="utf-8").read(), "raw": []})
    for i, t in enumerate(EXTRA): out.append({"id": f"extra{i}", "text": t, "raw": []})
    limit = int(os.getenv("PARITY_LIMIT", "0"))
    for p in sorted(glob.glob(f"{ROOT}/data/eval/*.jsonl")):
        rows = [json.loads(l) for l in open(p, encoding="utf-8")]
        for r in rows[:limit] if limit else rows:
            raw = [{"start": g["start"], "end": g["end"], "type": COARSE.get(g["label"], "FIN_ID"), "source": "openmed", "score": 0.9,
                    "label": g["label"], "why": [], "sources": ["openmed"]} for g in r["spans"]]
            out.append({"id": r["id"], "text": r["text"], "raw": raw})
    for k, o in enumerate(OPTION_SETS):
        for d in out: d.setdefault("options", {})
    return out

def py(d, o):
    text = d["text"]
    r = [(s, e, t, rid) for s, e, t, rid in rules.detect_detailed(text)]
    raw = [Span(s, e, t, "rules", None, rid, [rules.WHY[rid]], ["rules"]) for s, e, t, rid in r] + \
          [Span(x["start"], x["end"], x["type"], x["source"], x["score"], x["label"], [], ["openmed"]) for x in d["raw"]]
    fin = finalize(text, raw, Options(**o))
    out, vault = redact(text, [(s.start, s.end, s.type) for s in fin])
    return {"id": d["id"], "rules": [list(x) for x in r], "final": [[s.start, s.end, s.type, s.label] for s in fin], "output": out,
            "leaks": len(leak_check(out, vault))}

def test_generated_spec_is_current():
    assert open(rules.SPEC_PATH).read() == rules.spec_text(), "run `python -m redactd.rules --export`"

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("k", range(len(OPTION_SETS)))
def test_python_and_typescript_agree(k):
    o = OPTION_SETS[k]; ds = docs()
    if k: ds = ds[:len(EXTRA) + 1] + ds[len(EXTRA) + 1::7]     # option variants on a sample; defaults on everything
    with tempfile.TemporaryDirectory() as tmp:
        with open(f"{tmp}/in.jsonl", "w", encoding="utf-8") as f:
            for d in ds: f.write(json.dumps({**d, "options": {TS_OPTS[a]: b for a, b in o.items()}}) + "\n")
        subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "scripts/parity.ts", f"{tmp}/in.jsonl", f"{tmp}/out.jsonl"],
                       cwd=f"{ROOT}/apps/web", check=True)
        js = [json.loads(l) for l in open(f"{tmp}/out.jsonl", encoding="utf-8")]
    assert len(js) == len(ds)
    bad = []
    for d, j in zip(ds, js):
        p = py(d, o)
        for field in ("rules", "final", "output", "leaks"):
            if p[field] != j[field]:
                diff = ""
                if field in ("rules", "final"):
                    a, b = {tuple(x) for x in p[field]}, {tuple(x) for x in j[field]}
                    diff = f" only-python={sorted(a - b)[:3]} only-ts={sorted(b - a)[:3]}"   # offsets and labels only, never text
                bad.append(f"{d['id']}:{field}{diff}")
    assert not bad, f"{len(bad)} mismatches, first: {bad[:8]}"
