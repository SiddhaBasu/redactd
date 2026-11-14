# Load test

Generated 2026-11-13 18:26 UTC · mode **thorough** · instance: 4 vCPU / 15 GB (dev container), MODEL_THREADS=2, MAX_CONCURRENT_RUNS=2; shipped Thorough = distilled + GLiNER · API versions {'rules': '92cf0e967c37', 'distilled': 'redactd-small', 'gliner': 'gliner'}

Latency is end to end from the client (HTTP + queueing + detection). Raw findings are requested (`raw: true`), as the web app does.

## Targets

| Target | Result | Met |
|---|---|---|
| 10 KB, thorough, p95 < 1.5 s (20 sequential requests) | p50 7.50 s, p95 12.77 s | NO |
| 1 MB via /v1/jobs + SSE < 60 s | not delivered: the job needs ~800 s (API log: 1,000,000 chars, 797 s) and the progress stream closes at JOB_TTL_S = 600 s, see notes | NO |

## Realistic mix

40 requests: 24 under 10 KB, 14 of 10-200 KB, 2 of 200 KB-1 MB; 2.4 MB in total.

| Concurrency | p50 s | p95 s | p99 s | max s | req/s | KB/s | errors |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6.73 | 223.90 | 564.91 | 564.91 | 0.02 | 1 | 0 |
| 2 | 8.03 | 166.03 | 260.77 | 260.77 | 0.04 | 2 | 1 |
| 4 | 54.23 | 295.58 | 347.52 | 347.52 | 0.04 | 2 | 1 |

At the highest concurrency, requests under 10 KB: p50 37.81 s, p95 154.24 s.


---

# Load test: Standard mode (distilled)

Generated 2026-11-13 19:55 UTC · mode **standard** · instance: 4 vCPU / 15 GB (dev container), MODEL_THREADS=2, MAX_CONCURRENT_RUNS=2; Standard = distilled · API versions {'rules': '92cf0e967c37', 'distilled': 'redactd-small', 'gliner': 'gliner'}

Latency is end to end from the client (HTTP + queueing + detection). Raw findings are requested (`raw: true`), as the web app does.

## Targets

| Target | Result | Met |
|---|---|---|
| 10 KB, standard, p95 < 1.5 s (20 sequential requests) | p50 1.27 s, p95 1.43 s | yes |
| 1 MB via /v1/jobs + SSE < 60 s | 121.1 s, 17738 raw findings | NO |

## Realistic mix

40 requests: 24 under 10 KB, 14 of 10-200 KB, 2 of 200 KB-1 MB; 2.4 MB in total.

| Concurrency | p50 s | p95 s | p99 s | max s | req/s | KB/s | errors |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.97 | 37.78 | 89.16 | 89.16 | 0.14 | 9 | 0 |
| 2 | 1.33 | 45.85 | 104.41 | 104.41 | 0.24 | 14 | 0 |
| 4 | 8.73 | 53.39 | 131.32 | 131.32 | 0.23 | 14 | 0 |

At the highest concurrency, requests under 10 KB: p50 6.27 s, p95 25.17 s.


---

# Comparison: old Thorough (OpenMed + GLiNER), fixed targets only

Generated 2026-11-13 19:43 UTC · mode **thorough** · instance: 4 vCPU / 15 GB (dev container), MODEL_THREADS=2, MAX_CONCURRENT_RUNS=2; OLD Thorough = OpenMed + GLiNER · API versions {'rules': '92cf0e967c37', 'distilled': 'redactd-small', 'openmed': 'openmed-small', 'gliner': 'gliner'}

Latency is end to end from the client (HTTP + queueing + detection). Raw findings are requested (`raw: true`), as the web app does.

## Targets

| Target | Result | Met |
|---|---|---|
| 10 KB, thorough, p95 < 1.5 s (20 sequential requests) | p50 7.08 s, p95 11.07 s | NO |
| 1 MB via /v1/jobs + SSE < 60 s | not delivered: the job needs ~800 s (API log: 1,000,000 chars, 797 s) and the progress stream closes at JOB_TTL_S = 600 s, see notes | NO |



---

## Notes (added after the run)

* **Thorough misses both latency targets** on 4 vCPU with `MODEL_THREADS=2`: 10 KB p95 12.8 s (target 1.5 s), 1 MB
  about 800 s (target 60 s). GLiNER is ~86% of Thorough's compute (`bench/out/speed.md`); the old OpenMed + GLiNER
  configuration is no better (10 KB p95 11.1 s). **Standard (distilled) meets the 10 KB target** (p95 1.43 s) but
  not the 1 MB one (121 s).
* **API bug found:** `GET /v1/jobs/{id}/events` stops after `JOB_TTL_S` (600 s) counted from job creation, and the
  in-memory store's TTL is also counted from creation, so a job that runs longer than 600 s can never be delivered.
  The "errors" column above (1 at concurrency 2 and 4) is the 782 KB job hitting the same limit. Fix in
  `apps/api/app/main.py` / `jobs.py`: count the TTL from completion, and keep the stream open while the job runs.
* Under concurrency the 2 detection slots (`MAX_CONCURRENT_RUNS=2`) are the bottleneck: small requests queue behind
  large Thorough jobs (concurrency 4: p50 54 s). Separate slots or instances for small and large documents would fix
  the tail for small requests.
* The 1 MB scans earlier in the browser (2.6 s) were Fast mode (rules only); these numbers are model inference.
