"""CI gate (tasks A3 + F2). Runs bench/report.py and compares with bench/baseline.json.

    python bench/gate.py --mode rules                 # all eval docs, no model files needed (fast)
    python bench/gate.py --mode thorough --limit 50   # 50 docs per set, needs the ONNX models
    python bench/gate.py --mode thorough --limit 50 --update   # accept the current numbers as the new baseline

Fails the build when, for any set:
  * leak_check is non-empty for any rendered document (a redacted value survives elsewhere in the output), or
  * more gold DIRECT values are found in the output by raw string search than in the baseline, or
  * any tier's recall (>=50% or >=90%, raw labels) is more than 0.5 points below the baseline.
"""
import argparse, json, os, subprocess, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="thorough"); ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--update", action="store_true"); ap.add_argument("--tolerance", type=float, default=0.5)
ap.add_argument("--reuse", action="store_true", help="score an existing bench/out/report_gate_*.json instead of re-running")
a = ap.parse_args()
key = f"{a.mode}:{a.limit or 'all'}"; tag = f"gate_{a.mode}_{a.limit or 'all'}"
if not a.reuse:
    subprocess.run([sys.executable, f"{ROOT}/bench/report.py", "--mode", a.mode, "--limit", str(a.limit), "--tag", tag], check=True)
rep = json.load(open(f"{ROOT}/bench/out/report_{tag}.json"))
cur = {n: {"direct_r50": s["raw"]["direct_r50"], "direct_r90": s["raw"]["direct_r90"], "indirect_r50": s["raw"]["indirect_r50"],
           "indirect_r90": s["raw"]["indirect_r90"], "char_precision": s["raw"]["char_precision"],
           "gold_direct_in_output": s["gold_direct_in_output"], "leak_check_failures": s["leak_check_failures"]} for n, s in rep["sets"].items()}
path = f"{ROOT}/bench/baseline.json"
base_all = json.load(open(path)) if os.path.exists(path) else {}
if a.update:
    base_all[key] = cur; json.dump(base_all, open(path, "w"), indent=1, sort_keys=True); print("baseline updated:", key); sys.exit(0)
base = base_all.get(key)
if base is None: sys.exit(f"no baseline for {key}; run with --update")
fail = []
for n, c in cur.items():
    b = base.get(n)
    if c["leak_check_failures"]: fail.append(f"{n}: leak_check failed on {c['leak_check_failures']} value(s)")
    if not b: continue
    if c["gold_direct_in_output"] > b["gold_direct_in_output"]:
        fail.append(f"{n}: gold direct values in output {b['gold_direct_in_output']} -> {c['gold_direct_in_output']}")
    for k in ("direct_r50", "direct_r90", "indirect_r50", "indirect_r90"):
        if c[k] is not None and b[k] is not None and c[k] < b[k] - a.tolerance: fail.append(f"{n}: {k} {b[k]:.1f} -> {c[k]:.1f}")
    print(f"{n:30s} " + " ".join(f"{k}={c[k]:.1f}({c[k] - b[k]:+.1f})" for k in ("direct_r50", "direct_r90", "indirect_r50", "indirect_r90") if c[k] is not None and b[k] is not None)
          + f" direct-in-output={c['gold_direct_in_output']}({c['gold_direct_in_output'] - b['gold_direct_in_output']:+d})")
if fail: sys.exit("GATE FAILED\n  " + "\n  ".join(fail))
print("gate passed:", key)
