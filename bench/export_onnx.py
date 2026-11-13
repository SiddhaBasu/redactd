"""Export a HF token-classification model to ONNX (+ dynamic int8) in transformers.js layout.

    python bench/export_onnx.py <hf model dir or id> <out dir> [--matmul-only] [--requantize]

--matmul-only          quantise MatMul only. The default quantises every op ORT supports, which already includes
                       the Gather on the token-embedding matrix (checked: it is stored as uint8). To make the file
                       smaller than that, prune the vocabulary first (bench/prune_vocab.py).
--requantize           skip the export and re-quantise an existing <out dir>/onnx/model.onnx
"""
import os, sys
from onnxruntime.quantization import quantize_dynamic, QuantType

args = [a for a in sys.argv[1:] if not a.startswith("--")]
src, dst = args[0], args[1]
matmul_only = "--matmul-only" in sys.argv
os.makedirs(f"{dst}/onnx", exist_ok=True)
fp32 = f"{dst}/onnx/model.onnx"
if "--requantize" not in sys.argv or not os.path.exists(fp32):
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    tok = AutoTokenizer.from_pretrained(src); model = AutoModelForTokenClassification.from_pretrained(src, dtype=torch.float32).eval()
    tok.save_pretrained(dst); model.config.save_pretrained(dst)
    x = tok("Wire 500 USD to John Smith account 12345678", return_tensors="pt")
    torch.onnx.export(model, (x["input_ids"], x["attention_mask"]), fp32,
                      input_names=["input_ids", "attention_mask"], output_names=["logits"],
                      dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "logits": {0: "b", 1: "s"}},
                      opset_version=17, dynamo=False)
quantize_dynamic(fp32, f"{dst}/onnx/model_quantized.onnx", weight_type=QuantType.QInt8,
                 op_types_to_quantize=["MatMul"] if matmul_only else None)
print({f: round(os.path.getsize(f"{dst}/onnx/{f}") / 1e6, 1) for f in os.listdir(f"{dst}/onnx")}, "MB",
      "(MatMul only)" if matmul_only else "(all supported ops, incl. the embedding Gather)")
