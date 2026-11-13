"""Diagnose leak_check failures WITHOUT printing document text (safe on held-out sets).

    python bench/leak_diag.py [--mode standard] [sets...]

For each leaked value prints: length, character-class shape (A=upper, a=lower, 9=digit, others kept), the type /
source of the finding that redacted it, and which situation caused the leak:
  in-placeholder      the value occurs inside a placeholder we generated, e.g. "DATE" inside "[DATE_1]"
  uncovered-original  an occurrence in the ORIGINAL text is not covered by the final spans (pipeline bug)
  formed-by-render    the value only appears in the output across a placeholder boundary / in kept text
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from redactd.pipeline import Pipeline
from redactd.post import occurrences, PLACEHOLDER
from redactd.vault import redact, leak_check, merge

def shape(v):
    return "".join("A" if c.isupper() else "a" if c.islower() else "9" if c.isdigit() else ("_" if c.isspace() else c) for c in v)[:40]

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "standard"
    args = [a for a in args if a != mode]
    sets = args or ["eval_gretel_fin_holdout", "eval_fin_holdout2", "eval_nemotron_fin_structured"]
    p = Pipeline.from_env(threads=2)
    for name in sets:
        n = 0
        for line in open(os.path.join(HERE, "..", "data", "eval", f"{name}.jsonl")):
            r = json.loads(line); t = r["text"]
            sp, _ = p.detect(t, mode)
            tup = [(s.start, s.end, s.type) for s in sp]
            out, vault = redact(t, tup)
            for v in leak_check(out, vault):
                n += 1
                final = merge(tup)
                cov = lambda a, b: any(s <= a and b <= e for s, e, _ in final)
                orig = occurrences(t, v)
                unc = [o for o in orig if not cov(*o)]
                ph = [m.span() for m in PLACEHOLDER.finditer(out)]
                in_ph = [o for o in occurrences(out, v) if any(a <= o[0] and o[1] <= b for a, b in ph)]
                why = "in-placeholder" if in_ph else "uncovered-original" if unc else "formed-by-render"
                src = [(s.type, s.source, s.label) for s in sp if t[s.start:s.end] == v][:2]
                print(f"{name[:24]:24s} doc#{r['id'][-6:]} len={len(v)} shape={shape(v)!r} {why} redacted-by={src} "
                      f"orig-occ={len(orig)} uncovered={len(unc)} out-occ={len(occurrences(out, v))}")
        print(f"{name}: {n} leaked values", flush=True)

if __name__ == "__main__":
    main()
