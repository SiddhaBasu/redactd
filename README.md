# redactd

Private redaction for financial and other unstructured text. Detects personal and sensitive identifiers with pattern
rules plus small open-source models (OpenMed-PII, GLiNER-PII), lets you review every finding, and exports a redacted
copy — optionally reversible with a password-encrypted restore key. No hosted LLM ever sees your text.

- Architecture & accuracy: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Roadmap / handoff tasks: [`docs/HANDOFF_PROMPT.md`](docs/HANDOFF_PROMPT.md)

## Run it locally

**Prerequisites:** macOS or Linux (on Windows, use WSL2), Python 3.11+, Node.js 20+, git, ~2 GB free disk.

```bash
git clone -b claude/upbeat-bohr-sabzbz https://github.com/SiddhaBasu/redactd.git
cd redactd
bash scripts/setup.sh          # first time only: Python env, datasets, ONNX models (~1 GB), web deps
```

Then start the two servers (two terminals), or in VS Code run **Terminal → Run Task → redactd: run app**:

```bash
cd apps/api && ../../.venv/bin/uvicorn app.main:app --port 8000     # API (models load in ~20 s)
cd apps/web && npm run dev                                          # web app
```

Open <http://localhost:3000/redact>.

| Folder | What it is |
|---|---|
| `apps/web` | Next.js UI (redact, review, export, restore) |
| `apps/api` | FastAPI detection service |
| `redactd/` | Core Python library: rules, models, pipeline, reversible vault |
| `bench/` | Evaluation harness and model training |

Tests: `cd apps/api && ../../.venv/bin/python -m pytest -q tests` and `cd apps/web && npm test`.
