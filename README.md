# redactd

Privacy-first redaction for unstructured financial text: bank emails, loan notes, statements, SWIFT/FIX/EDI
messages, insurance policies and support tickets, up to 1 MB. redactd finds personal and sensitive identifiers,
lets the user review every finding, and exports a redacted copy. Redaction is optionally reversible: placeholders
such as `[NAME_1]` plus a password-encrypted restore key that never leaves the browser.

**No hosted LLM ever sees user data.** Detection is pattern rules with checksum validators plus small open-weight
models (Apache-2.0 / MIT) running on our own servers or in the user's browser.

| | |
|---|---|
| `redactd/` | Core library: rules (`rules.py`, single source for both engines), post-processing (`post.py`), models, pipeline, vault |
| `apps/api/` | FastAPI service: `/v1/detect`, `/v1/redact`, `/v1/jobs` (+ SSE progress), `/v1/extract`; usage metering only |
| `apps/web/` | Next.js app: workspace (`/redact`), `/restore`, `/privacy`; on-device worker; the TypeScript port of the pipeline |
| `bench/` | Evaluation: `report.py` (one-command benchmark), `gate.py` (CI gate), calibration, distillation, load test |
| `data/eval/` | Committed synthetic eval sets, with sources, licences and the held-out rules |
| `docs/` | [Architecture](docs/ARCHITECTURE.md) · [Threat model](docs/THREAT_MODEL.md) · [Deployment](docs/DEPLOY.md) |

## Run it

```bash
bash scripts/setup.sh                      # Python env, datasets, ONNX models, web deps (idempotent)
. .venv/bin/activate
(cd apps/api && PRELOAD_MODES=thorough uvicorn app.main:app --port 8000)
(cd apps/web && npx next build && npx next start -p 3000)
```

## Test it

```bash
python -m pytest -q tests                  # Python <-> TypeScript parity on every eval doc, ReDoS fuzz
(cd apps/api && python -m pytest -q tests) # privacy, SSE, Redis stores, API keys, formats, logs, migrations
(cd apps/web && npm test)                  # rules, post-processing, vault, layout, review reducer, presets, report
(cd apps/web && node e2e/flow.e2e.cjs Thorough && node e2e/quality.e2e.cjs && node e2e/device.e2e.cjs Standard)
python bench/report.py                     # full benchmark -> bench/out/report.md (about 10 min on 4 vCPU)
python bench/gate.py --mode thorough --limit 50
python scripts/licence_audit.py
```

## Rules of the house

* Change a rule in `redactd/rules.py` or a word list in `redactd/lexicon.py`, then run
  `python -m redactd.rules --export`. Never edit `apps/web/lib/rules.generated.json` by hand. Mirror any change to
  `redactd/post.py` in `apps/web/lib/redact.ts`; the parity test will tell you if you forgot.
* Tune only on the dev sets. Never open a held-out document. See `data/eval/README.md`.
* Nothing derived from document text goes into logs, errors, the database or analytics. `app/obs.py` enforces it.
* Recall first: never trade a missed identifier for precision.

Current accuracy, with the misses and the targets that are not met, is in `bench/out/report.md`.
