# Deployment

| Piece | Where | Notes |
|---|---|---|
| Web (`apps/web`) | Vercel | Root directory `apps/web`. Pages are server-rendered per request (CSP nonce). |
| API (`apps/api`) | Fly.io | `fly deploy --config apps/api/fly.toml --dockerfile apps/api/Dockerfile` from the repo root. |
| Usage database | Neon Postgres | Only `usage_events` and `api_keys`. Run `alembic upgrade head` on release. |
| Jobs + rate limits | Upstash Redis | Needed as soon as there is more than one API instance. |
| On-device model files | Cloudflare R2 (public bucket + custom domain) | Upload `browser/models/<model>/…` unchanged. Integrity comes from the manifest in the web bundle, not from R2. |

None of these has been provisioned from this repository yet: each is a paid or account-bound service, so the
configuration below is ready but unapplied.

## Web (Vercel) environment

| Variable | Example | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.redactd.example` | API origin. Also added to the CSP `connect-src`. |
| `NEXT_PUBLIC_MODEL_BASE` | `https://redactd-api.fly.dev/models/` | Where the worker downloads model files (the API serves them). Added to `connect-src`. |
| `NEXT_PUBLIC_API_KEY` | (secret-ish) | The key the website sends to the API. Same value as the `WEB_API_KEY` GitHub secret. It is visible in the page code, so keep **Vercel Authentication → All Deployments** on: then only you can load the site. |

Build: `npm ci && node scripts/model-manifest.mjs <models dir> && next build`. The manifest
(`lib/models.manifest.json`) must be generated from the exact files uploaded to R2 and committed with the release.
R2 must send `Access-Control-Allow-Origin: <web origin>` and `Cross-Origin-Resource-Policy: cross-origin`
(the app is cross-origin isolated for multi-threaded WASM).

## API (Fly.io) environment

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file | `postgresql+pg8000://user:pass@host/db` for Neon (add `?ssl_context=True`). |
| `REDIS_URL` | empty | `rediss://default:<token>@<host>:6379` for Upstash. Empty = in-memory stores (single instance only). |
| `ALLOWED_ORIGINS` | localhost | Comma-separated web origins for CORS. |
| `IP_SALT` | dev value | **Set a random secret.** Salts the client hash stored with usage rows. |
| `PRELOAD_MODES` | `thorough` | Modes to warm at start. `""` loads lazily. |
| `MODEL_THREADS` | `0` (ORT default) | Intra-op threads per run. With `MAX_CONCURRENT_RUNS=2` on 4 vCPU use `2`. |
| `MAX_CONCURRENT_RUNS` | `2` | Detection slots; further requests queue. |
| `OPENMED_DIR`, `GLINER_DIR`, `DISTILLED_DIR` | `/models/...` in the image | Model directories. |
| `REDACTD_STANDARD`, `REDACTD_THOROUGH` | `openmed`, `openmed,gliner` | Which models each mode runs, e.g. `REDACTD_STANDARD=distilled`. |
| `RATE_PER_MINUTE`, `ANON_RATE_PER_MINUTE` | `60`, `20` | Default per-key and anonymous limits. |
| `REQUIRE_API_KEY` | `0` | `1` rejects every keyless POST and keyless model-file download (set automatically by the deploy workflow when `WEB_API_KEY` exists). |
| `STATIC_API_KEY_SHA256` | empty | SHA-256 of keys configured as secrets (the website key). Set by the deploy workflow; the key itself never reaches Fly. |
| `MODEL_FILES_PER_MINUTE` | `40` | On-device model downloads allowed per client per minute. |
| `JOB_MAX_RUN_S` | `3600` | How long a large-file job may run; `JOB_TTL_S` (600) is the collection window after it finishes. |
| `MAX_CHARS`, `SYNC_LIMIT_CHARS`, `MAX_UPLOAD_BYTES`, `JOB_TTL_S` | 1 000 000, 200 000, 10 000 000, 600 | Limits. |
| `LOG_FORMAT` | `json` | Metadata-only JSON lines on stdout. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` (+ standard `OTEL_*`) | empty | Set to export traces; install `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`. |

Release steps: `alembic upgrade head` (the Fly `release_command` does this), then create keys with
`python -m app.keys create "<name>" --rate 120 --monthly-chars 50000000`.

Sizing: one detection uses `MODEL_THREADS` cores; see `bench/out/load.md` for measured latency and throughput.
Give the machine a memory limit and disable swap and core dumps (see `docs/THREAT_MODEL.md`).

## Website API key (once)

1. Generate a key on your own machine: `openssl rand -hex 32`.
2. Vercel → project → Settings → Environment Variables: `NEXT_PUBLIC_API_KEY` = the key (Production and Preview), then redeploy.
3. GitHub → Settings → Secrets and variables → Actions: `WEB_API_KEY` = the same key.
4. Run **Actions → deploy-api**. The workflow stores only the key's SHA-256 on Fly, turns on `REQUIRE_API_KEY`, and its
   smoke test checks that a keyless request is refused.
5. Vercel → Settings → Deployment Protection → **Vercel Authentication**, scope **All Deployments** (free on Hobby;
   "Standard Protection" would leave the production URL public).

## Cost guard

`.github/workflows/budget-guard.yml` runs hourly with the `FLY_API_TOKEN` secret. Fly has no spending cap, so it reads
the machine's running time over the last 24 hours from Fly's metrics and turns it into a monthly pace: above $10 the
run fails (GitHub emails you), above $15 it removes the machine (`fly scale count 0`), and it restores one machine once
the last 24 hours are back under the $10 pace. Manual runs default to a dry run. Change `MONTHLY_CAP_USD`,
`MONTHLY_ALERT_USD` and `HOURLY_USD` in the workflow if the machine size changes.

## CI

`.github/workflows/ci.yml`: typecheck, unit tests and build (web); lint, rule parity, ReDoS fuzz, API tests, the
rules-mode leak/recall gate on every eval document and the licence audit (python); a 50-document Thorough
benchmark gate against `bench/baseline.json`; Playwright e2e against Vercel preview deployments
(`deployment_status` events).
