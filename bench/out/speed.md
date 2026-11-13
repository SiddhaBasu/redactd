# Speed (task B1)

`MODEL_THREADS=2 python bench/speed.py --docs 100` — one process, the first 100 documents of eval_gretel_fin
(150,657 characters), best of two passes after warm-up, post-processing included. 4 vCPU dev container; an idle
API server was running alongside.

| Configuration | ms per 1k chars | 100 docs |
|---|---:|---:|
| distilled (shipped Standard) | 73.7 | 11.1 s |
| OpenMed (old Standard) | 84.6 | 12.8 s |
| OpenMed + GLiNER (old Thorough) | 533.3 | 80.3 s |
| distilled + GLiNER (shipped Thorough) | 527.0 | 79.4 s |

* Distilled alone vs OpenMed + GLiNER: **7.2× faster** (target ≥ 2×: met).
* Shipped Thorough is no faster than the old Thorough: GLiNER is ~86% of its time.
