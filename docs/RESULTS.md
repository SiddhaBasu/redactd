# Results against the definition of done

Measured 2026-11-13/14 on the code in this branch. **Shipped configuration:** Standard = distilled model
(`redactd-small`, deberta-v3-xsmall, int8, 87 MB); Thorough = distilled + GLiNER-PII. Fast = rules only.
Held-out sets were never used for tuning (see `data/eval/README.md`). Full tables: `bench/out/report.md` (Thorough),
`bench/out/report_leakfix_std.md` (Standard), `bench/out/load.md`, `bench/out/speed.md`, `bench/out/on_device.md`.

## §3 targets

"Headline" = `eval_gretel_fin_holdout` (300 docs); "new held-out" = `eval_fin_holdout2` (300 docs, built for task A2).

| Metric | Target | Thorough (shipped) headline / new held-out | Standard (shipped) headline / new held-out | Met? |
|---|---|---|---|---|
| Direct recall ≥50%, raw labels | ≥ 99% | 99.3 / 99.3 | 99.3 / 99.1 | **yes** (both modes) |
| Direct recall ≥90%, raw labels | ≥ 96% | 98.1 / 98.7 | 98.1 / 98.2 | **yes** (both modes) |
| Indirect recall ≥50%, policy-adjusted | ≥ 97% | 99.4 / **96.4** | 98.6 / **95.3** | **no**: met on the headline set, missed on the new held-out set |
| Indirect recall ≥90%, policy-adjusted | ≥ 95% | 99.2 / 96.2 | 97.6 / **94.0** | Thorough **yes**; Standard no on the new set |
| Character precision, Gretel | ≥ 55% | 28.1 / 29.4 | 32.9 / 34.6 | **no** |
| Character precision, Nemotron | ≥ 85% | 69.5 (`eval_nemotron_fin_structured`, held-out) | 77.7 | **no** |
| API latency, Thorough, 10 KB, 4 vCPU, p95 | < 1.5 s | 12.8 s | (Standard: 1.43 s) | **no** for Thorough; Standard meets it |
| 1 MB document via `/v1/jobs` | < 60 s | ~797 s, and not delivered (job-TTL bug, below) | 121 s | **no** |
| On-device model download (Standard) | ≤ 80 MB | — | 87.0 MB | **no** (a 62.8 MB candidate exists, not shipped) |
| Leak check: 0 leaks on every eval doc after rendering | 0 | 0 on all 8 sets | 0 on all 8 sets | **yes** |

The same metrics with raw and policy-adjusted labels side by side, Thorough (shipped):

| Set | Direct ≥50 raw | Direct ≥90 raw | Indirect ≥50 raw | Indirect ≥90 raw | Prec raw | Indirect ≥50 policy | Indirect ≥90 policy | Prec policy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| eval_gretel_fin_holdout (held-out) | 99.3 | 98.1 | 96.9 | 95.5 | 28.1 | 99.4 | 99.2 | 27.1 |
| eval_fin_holdout2 (held-out) | 99.3 | 98.7 | 93.5 | 93.1 | 29.4 | 96.4 | 96.2 | 29.0 |
| eval_nemotron_fin_structured (held-out) | 99.9 | 99.8 | 94.0 | 93.8 | 69.5 | 97.6 | 97.5 | 69.5 |
| eval_gretel_en (held-out) | 100.0 | 100.0 | 100.0 | 100.0 | 69.2 | 100.0 | 100.0 | 69.2 |
| eval_adversarial (regression; rules tuned on it) | 100.0 | 100.0 | 100.0 | 100.0 | 72.0 | 100.0 | 100.0 | 71.9 |
| eval_gretel_fin (dev) | 99.6 | 98.8 | 97.3 | 96.2 | 29.9 | 100.0 | 99.4 | 28.4 |
| eval_nemotron_fin (dev) | 99.9 | 99.9 | 97.7 | 97.4 | 66.9 | 98.8 | 98.5 | 66.9 |
| dev_nemotron_fin_structured (dev) | 100.0 | 99.7 | 94.0 | 92.4 | 66.1 | 98.6 | 97.7 | 66.0 |

Before this work (old pipeline, headline set): direct 98.9/94.2 raw, indirect 98.8/98.0 policy, precision 35%.

Leak check note: `leak_check` (a redacted value surviving elsewhere in the output) is 0 everywhere. A separate raw
string search for every gold DIRECT value in the output still finds 4 of 773 (headline), 3 of 720 and 2 of 1,287
values: identifiers the detectors missed entirely, which no leak check can see. They are part of the ~0.7% direct
misses above.

## Other acceptance criteria with numbers

| Item | Target | Result | Met? |
|---|---|---|---|
| B1 single model + rules, policy, ≥50% | ≥ 97% direct / ≥ 93% indirect | 99.3 / 98.6 headline; 99.1 / 95.3 new held-out | **yes** |
| B1 int8 file | ≤ 80 MB | 87.0 MB shipped; 62.8 MB pruned candidate missed the held-out accuracy budget by 0.01 point | **no** |
| B1 speed vs OpenMed + GLiNER | ≥ 2× faster | 7.2× (73.7 vs 533.3 ms per 1k chars, 2 threads) | **yes** |
| B2 precision targets, recall drop ≤ 0.3 | see §3 | precision not met; see `bench/report_notes.md` for what was tried | **no** |
| B4 `eval_nemotron_fin_structured` direct recall | ≥ 98% | 99.9 | **yes** |
| D1 1 MB / ~10k findings, no long task > 100 ms while scrolling | 0 | 24,023 findings, 0 long tasks, frame p95 16.7 ms | **yes** |
| D6 axe-core violations | 0 | 0 on 36 page states, 360 and 1280 px, light and dark | **yes** |
| D7 on-device cold load (Standard, 50 Mbit/s) | < 15 s | 20.4–22.0 s (download 15.9 s of it) | **no** |
| D7 on-device warm load | < 2 s | 3.9–5.0 s (ONNX session creation 2.5 s) | **no** |
| C3 load report | written | `bench/out/load.md` | **yes** |

## Open problems

1. **Thorough is slow on CPU.** GLiNER is ~86% of Thorough's compute. 10 KB p95 is 12.8 s and 1 MB takes ~13 min
   on 4 vCPU. Options: run GLiNER only on chunks the distilled model is unsure about, a GPU instance for GLiNER, or
   make Standard the default for large files.
2. **Job-TTL bug (API):** the SSE progress stream and the job TTL are both counted from job creation
   (`JOB_TTL_S = 600 s`), so a job running longer than 10 minutes is never delivered. Fix in `apps/api/app/main.py`
   and `jobs.py`: count the TTL from completion and keep the stream open while the job runs.
3. **Precision** is half the Gretel target. A manual audit (`bench/report_notes.md`) suggests about a third of
   "false positives" are unlabelled real identifiers; most of the rest comes from two GLiNER labels.
4. **Indirect recall on `eval_fin_holdout2`** (96.4 policy) is below the 97% target.
5. **On-device** needs a ≤ ~55 MB model for the cold target and faster session start-up for the warm one.
