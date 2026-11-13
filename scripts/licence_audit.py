#!/usr/bin/env python3
"""E3: dependency and licence audit for SHIPPED artifacts. Fails (exit 1) on copyleft or non-commercial licences.

    python scripts/licence_audit.py            # API runtime deps + web runtime deps + models + datasets
    python scripts/licence_audit.py --json

Scope = what reaches users or runs in production:
  * Python: apps/api/requirements.txt and everything it pulls in (resolved from the active environment)
  * JavaScript: apps/web production dependencies (devDependencies such as axe-core are tools, not shipped)
  * Models and datasets: the explicit table below; adding a model means adding a row here
Unknown licences fail too: someone has to look and add an entry to REVIEWED with a reason.
"""
import json, os, re, subprocess, sys
from importlib import metadata
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

ALLOW = re.compile(r"\b(MIT|MIT-0|Apache|BSD|ISC|PSF|Python Software Foundation|Unlicense|CC0|0BSD|Zlib|HPND|Public Domain|BlueOak|CC-BY-4\.0|CC BY 4\.0|WTFPL|Artistic-2)", re.I)
DENY = re.compile(r"\b(A?GPL|LGPL|SSPL|EUPL|CC[- ]BY[- ]NC|NonCommercial|Non-Commercial|CC[- ]BY[- ]ND|NoDerivatives|BUSL|Commons Clause|Elastic License|CPAL|OSL)\b", re.I)
# Weak (file-level) copyleft that is acceptable when used unmodified as a library, each with a reason.
REVIEWED = {
    "certifi": "MPL-2.0: CA bundle, used unmodified as data",
    "tqdm": "MIT AND MPL-2.0: used unmodified",
    "pathspec": "MPL-2.0: used unmodified",
    "orjson": "Apache-2.0 OR MIT (dual; metadata lists both)",
    "typing_extensions": "PSF-2.0", "typing-extensions": "PSF-2.0",
    "numpy": "BSD-3-Clause with bundled BSD/MIT/Zlib components",
    "torch": "BSD-3-Clause", "sympy": "BSD-3-Clause", "networkx": "BSD-3-Clause", "mpmath": "BSD-3-Clause", "fsspec": "BSD-3-Clause",
    "onnxruntime": "MIT", "protobuf": "BSD-3-Clause", "flatbuffers": "Apache-2.0", "coloredlogs": "MIT", "humanfriendly": "MIT",
    "huggingface_hub": "Apache-2.0", "huggingface-hub": "Apache-2.0", "hf-xet": "Apache-2.0", "sentencepiece": "Apache-2.0", "regex": "Apache-2.0 AND CNRI-Python",
    "python-multipart": "Apache-2.0", "lxml": "BSD-3-Clause", "pillow": "MIT-CMU (HPND)", "packaging": "Apache-2.0 OR BSD-2-Clause", "idna": "BSD-3-Clause",
    "caniuse-lite": "CC-BY-4.0: browser support data, attribution in THIRD_PARTY notices",
    "sharp": "Apache-2.0", "@img/sharp-libvips-linux-x64": "LGPL-3.0-or-later: prebuilt libvips, dynamically linked optional dependency of Next image optimisation; not used by this app (no next/image) and excluded from the client bundle",
    "@img/sharp-libvips-linuxmusl-x64": "LGPL-3.0-or-later: see above",
}
MODELS = [  # (name, licence, shipped?, note)
    ("microsoft/deberta-v3-xsmall (base of redactd-small)", "MIT", True, "distilled weights are ours"),
    ("OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1", "Apache-2.0", True, "Standard model until redactd-small meets the targets"),
    ("knowledgator/gliner-pii-base-v1.0", "Apache-2.0", True, "Thorough mode"),
    ("Qwen/Qwen2.5-1.5B-Instruct (GGUF)", "Apache-2.0", False, "bench only (B5); not shipped"),
    ("gretelai/synthetic_pii_finance_multilingual", "Apache-2.0", True, "eval + training data"),
    ("gretelai/gretel-pii-masking-en-v1", "Apache-2.0", True, "eval data"),
    ("nvidia/Nemotron-PII", "CC-BY-4.0", True, "eval + training data; attribution in data/eval/README.md"),
]
BANNED_MODELS = ["piiranha", "nvidia/gliner-pii", "qwen2.5-3b"]   # CC BY-NC-ND / NVIDIA Open Model Licence (unreviewed) / non-commercial

def py_closure():
    reqs = [re.split(r"[<>=!~\[; #]", l.strip())[0] for l in open(f"{ROOT}/apps/api/requirements.txt") if l.strip() and not l.startswith("#")]
    seen, todo = {}, list(reqs)
    while todo:
        name = todo.pop()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in seen or not name: continue
        try: d = metadata.distribution(name)
        except metadata.PackageNotFoundError: seen[key] = None; continue    # marker-excluded on this platform: not installed, not shipped
        lic = d.metadata.get("License-Expression") or ""
        if not lic:
            cls = [c.split("::")[-1].strip() for c in d.metadata.get_all("Classifier") or [] if c.startswith("License ::")]
            lic = "; ".join(cls) or (d.metadata.get("License") or "").strip().split("\n")[0][:80]
        seen[key] = (d.metadata["Name"], lic)
        for r in d.requires or []:
            if "extra ==" in r: continue
            todo.append(re.split(r"[<>=!~\[; (]", r)[0].strip())
    return sorted((v for v in seen.values() if v), key=lambda x: x[0].lower())

def js_prod():
    web = f"{ROOT}/apps/web"
    out = subprocess.run(["npm", "ls", "--omit=dev", "--all", "--parseable"], cwd=web, capture_output=True, text=True).stdout.split("\n")
    res = {}
    for p in out:
        pj = os.path.join(p, "package.json")
        if not p or not os.path.exists(pj) or os.path.realpath(p) == os.path.realpath(web): continue
        j = json.load(open(pj)); lic = j.get("license") or (j.get("licenses") or [{}])[0].get("type") if not isinstance(j.get("license"), dict) else j["license"].get("type")
        res[j.get("name", p)] = lic or ""
    return sorted(res.items())

def verdict(name, lic):
    if name in REVIEWED: return "reviewed", REVIEWED[name]
    if lic and DENY.search(lic) and not re.search(r"\bOR\b.*(MIT|Apache|BSD)|(MIT|Apache|BSD).*\bOR\b", lic): return "DENIED", lic
    if lic and ALLOW.search(lic): return "ok", lic
    return "UNKNOWN", lic or "no licence metadata"

def main():
    rows, bad = [], []
    for kind, items in (("python", py_closure()), ("npm", js_prod())):
        for name, lic in items:
            v, why = verdict(name, lic)
            rows.append({"kind": kind, "name": name, "licence": lic, "verdict": v, "note": why if v == "reviewed" else ""})
            if v in ("DENIED", "UNKNOWN"): bad.append(f"{kind}: {name}: {v} ({why})")
    for name, lic, shipped, note in MODELS:
        v = "ok" if ALLOW.search(lic) and not DENY.search(lic) else "DENIED"
        rows.append({"kind": "model/data", "name": name, "licence": lic, "verdict": v if shipped else "not shipped", "note": note})
        if shipped and v != "ok": bad.append(f"model/data: {name}: {lic}")
    # banned models must not be referenced by anything that ships
    for base, _, files in os.walk(ROOT):
        if any(x in base for x in ("node_modules", ".venv", ".git", ".next", "/bench", "/docs", "/data")): continue
        for f in files:
            if f.endswith((".py", ".ts", ".tsx", ".mjs", ".json", ".sh", ".yml", "Dockerfile")) and f not in ("licence_audit.py", "package-lock.json"):
                try: t = open(os.path.join(base, f), errors="ignore").read().lower()
                except OSError: continue
                for b in BANNED_MODELS:
                    if b in t: bad.append(f"banned model reference '{b}' in {os.path.relpath(os.path.join(base, f), ROOT)}")
    if "--json" in sys.argv: print(json.dumps(rows, indent=1))
    else:
        import collections
        c = collections.Counter((r["kind"], r["verdict"]) for r in rows)
        for (k, v), n in sorted(c.items()): print(f"{k:11s} {v:12s} {n}")
        for r in rows:
            if r["verdict"] == "reviewed": print(f"  reviewed  {r['kind']:7s} {r['name']}: {r['note']}")
    if bad:
        print("\nLICENCE AUDIT FAILED\n  " + "\n  ".join(bad)); sys.exit(1)
    print("\nlicence audit passed")

if __name__ == "__main__":
    main()
