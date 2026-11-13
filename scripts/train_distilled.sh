#!/usr/bin/env bash
# Build the single distilled detection model (task B1): label -> train -> export int8 ONNX -> web manifest.
# About 1.5-2.5 hours on 4 vCPU without a GPU. Needs scripts/setup.sh to have run (datasets + teacher models).
#   bash scripts/train_distilled.sh [nemotron_docs=3500] [gretel_docs=3500]
set -euo pipefail
cd "$(dirname "$0")/.."; . .venv/bin/activate
# 1. teacher labels: the full shipped ensemble (Thorough) on TRAIN splits only, united with gold labels.
#    WORKERS=2 keeps memory under 8 GB (each worker holds OpenMed + GLiNER).
[ -s data/processed/train_distill.jsonl ] || WORKERS="${WORKERS:-2}" python bench/make_distill.py --nemotron "${1:-3500}" --gretel "${2:-3500}"
# 2. student: deberta-v3-xsmall (MIT), float32 (fp16 on CPU gives NaN), checkpoints every 100 steps, resumable
THREADS="${THREADS:-4}" BASE=microsoft/deberta-v3-xsmall OUT=models/redactd-xsmall EPOCHS="${EPOCHS:-2}" BS=16 LR=8e-5 SAVE_EVERY=100 RESUME=1 python bench/train_deberta.py
# 3. int8 ONNX in the layout both the API and transformers.js load
python bench/export_onnx.py models/redactd-xsmall browser/models/redactd-small
rm -f browser/models/redactd-small/onnx/model.onnx
# 4. hashes for the on-device loader (ships in the web bundle)
(cd apps/web && node scripts/model-manifest.mjs)
echo "done: browser/models/redactd-small  (evaluate with: REDACTD_STANDARD=distilled python bench/report.py --mode standard)"
