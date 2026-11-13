#!/usr/bin/env bash
# Reproducible setup for a fresh checkout: Python env, datasets, eval sets, ONNX models, web deps.
# Idempotent: skips anything already present. Run from the repo root:  bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
HF=https://huggingface.co

# 1. Python env (CPU torch)
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q --upgrade pip
python -c "import torch" 2>/dev/null || pip install -q torch --index-url https://download.pytorch.org/whl/cpu
pip install -q transformers datasets accelerate gliner presidio-analyzer presidio-anonymizer onnx onnxruntime \
  seqeval sentencepiece cryptography fastapi "uvicorn[standard]" sqlalchemy httpx pytest tokenizers pandas pyarrow
python -c "import spacy; spacy.load('en_core_web_lg')" 2>/dev/null || \
  pip install -q https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# 2. Datasets (synthetic, public): Gretel finance (Apache-2.0), Nemotron-PII (CC-BY-4.0), Gretel general (Apache-2.0)
mkdir -p data/raw data/processed
dl() { [ -s "$2" ] || curl -sSL --fail -o "$2" "$1"; }
for f in English_train English_test; do
  dl "$HF/datasets/gretelai/synthetic_pii_finance_multilingual/resolve/main/data/$f-00000-of-00001.parquet" "data/raw/gretel_fin_$f.parquet"; done
for f in train test; do
  dl "$HF/datasets/nvidia/Nemotron-PII/resolve/main/data/$f-00000-of-00001.parquet" "data/raw/nemotron_$f.parquet"; done
dl "$HF/datasets/gretelai/gretel-pii-masking-en-v1/resolve/main/data/test-00000-of-00001.parquet" data/raw/gretel_en_test.parquet

# 3. Eval/train splits (deterministic seeds)
[ -s data/processed/eval_nemotron_fin.jsonl ] || python bench/prepare.py
[ -s data/processed/eval_gretel_fin_holdout.jsonl ] || python bench/make_holdout.py

# 4. Models -> browser/models (served to the web app in on-device mode, loaded by the API)
[ -s browser/models/openmed-small/onnx/model_quantized.onnx ] || \
  python bench/export_onnx.py OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 browser/models/openmed-small
G=browser/models/gliner; mkdir -p $G/onnx
for f in tokenizer.json tokenizer_config.json gliner_config.json special_tokens_map.json added_tokens.json; do
  dl "$HF/knowledgator/gliner-pii-base-v1.0/resolve/main/$f" "$G/$f"; done
dl "$HF/knowledgator/gliner-pii-base-v1.0/resolve/main/onnx/model_quint8.onnx" "$G/onnx/model_quint8.onnx"
[ -s $G/config.json ] || echo '{"model_type":"deberta-v2"}' > $G/config.json
# Optional (1.1 GB): small LLM used only by bench/slm.py experiments. Enable with WITH_SLM=1.
if [ "${WITH_SLM:-0}" = "1" ]; then
  mkdir -p models
  dl "$HF/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf" models/qwen2.5-1.5b-q4_k_m.gguf
  pip install -q llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary llama-cpp-python
fi

# 5. Web app deps (+ copies ORT wasm into public/ via postinstall) and model symlink
(cd apps/web && npm install --silent && ln -sfn ../../../browser/models public/models)
echo "setup complete"
