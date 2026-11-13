#!/usr/bin/env bash
# Put every model file the API image and the on-device app need under browser/models, without training anything.
#   redactd-small  <- private Hugging Face repo (needs a token: HF_TOKEN, or a proxy that injects one)
#   openmed-small  <- exported from OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 (Apache-2.0) by bench/export_onnx.py
#   gliner         <- knowledgator/gliner-pii-base-v1.0 (Apache-2.0), published int8 ONNX
# Idempotent. Run from anywhere:  bash scripts/fetch_models.sh
set -euo pipefail
cd "$(dirname "$0")/.."
HF=https://huggingface.co
REPO="${REDACTD_MODEL_REPO:-sybasu/redactd-small}"
dl() { [ -s "$2" ] || { mkdir -p "$(dirname "$2")"; curl -sSL --fail --retry 4 ${3:+-H "Authorization: Bearer $3"} -o "$2" "$1"; }; }
M=browser/models/redactd-small
for f in config.json tokenizer.json tokenizer_config.json onnx/model_quantized.onnx; do dl "$HF/$REPO/resolve/main/$f" "$M/$f" "${HF_TOKEN:-}"; done
G=browser/models/gliner
for f in tokenizer.json tokenizer_config.json gliner_config.json special_tokens_map.json added_tokens.json onnx/model_quint8.onnx; do
  dl "$HF/knowledgator/gliner-pii-base-v1.0/resolve/main/$f" "$G/$f"; done
[ -s $G/config.json ] || echo '{"model_type":"deberta-v2"}' > $G/config.json
if [ ! -s browser/models/openmed-small/onnx/model_quantized.onnx ]; then
  python bench/export_onnx.py OpenMed/OpenMed-PII-SuperClinical-Small-44M-v1 browser/models/openmed-small
  rm -f browser/models/openmed-small/onnx/model.onnx      # fp32 export: not shipped
fi
sha256sum $M/onnx/model_quantized.onnx $G/onnx/model_quint8.onnx browser/models/openmed-small/onnx/model_quantized.onnx
