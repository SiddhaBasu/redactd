# On-device timing (task D7)

`node apps/web/e2e/device.e2e.cjs Standard 50`: Chromium (Playwright) on the 4 vCPU dev container, `next start`
on localhost, the 50 Mbit/s link simulated with CDP, Standard mode, the onboarding sample document. Times are from
clicking Scan to the leak-check badge. Stage times come from the worker's own timers.

| | Total | Model files | Tokenizer | ONNX session (WASM) | Inference | Target | Met |
|---|---:|---:|---:|---:|---:|---:|---|
| OpenMed-Small, cold (before) | 41.6 s | | | | | < 15 s | no |
| OpenMed-Small, warm (before) | 7.7 s | | | | | < 2 s | no |
| **redactd-small (distilled, 87 MB), cold** | **20.4–22.0 s** | 15.9 s (download + SHA-256) | 0.4 s | 3.6 s | 0.6 s | < 15 s | **no** |
| **redactd-small, warm (Cache API)** | **3.9–5.0 s** | 0.27 s (cache + SHA-256) | 0.27 s | 2.5 s | 0.5 s | < 2 s | **no** |

* A tampered model file is still refused, and a warm load makes zero network requests.
* **Cold** is bound by the download: 87 MB at 50 Mbit/s is 13.9 s at line rate before anything else runs. Meeting
  < 15 s needs a model of roughly 55 MB or less. The 62.8 MB pruned candidate (bench commit 3125fba) would cut the
  download to about 11 s but was not shipped because it missed the held-out accuracy budget by 0.01 points.
* **Warm** is bound by ONNX Runtime creating the WASM session (2.3–2.5 s), plus ~1.4 s of worker and runtime start-up
  not captured by the stage timers. Using `graphOptimizationLevel: "basic"` changed session creation by
  0.2 s (noise), so it was not kept. Options not tried: keeping the worker and session alive across scans (already
  the case within one page; the test opens a new page per run, which is the honest cold-tab case), or shipping a
  pre-optimised ORT-format model.
