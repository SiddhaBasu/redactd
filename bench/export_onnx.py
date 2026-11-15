"""Export a HF token-classification model to ONNX (+ dynamic int8) in transformers.js layout.

    python bench/export_onnx.py <hf model dir or id> <out dir> [--matmul-only] [--requantize]

--matmul-only          quantise MatMul only. The default quantises every op ORT supports, which already includes
                       the Gather on the token-embedding matrix (checked: it is stored as uint8). To make the file
                       smaller than that, prune the vocabulary first (bench/prune_vocab.py).
--requantize           skip the export and re-quantise an existing <out dir>/onnx/model.onnx
--weights=u8|s8|s8-7bit  weight format (default u8). With signed weights (s8), ONNX Runtime's AVX2 kernel for CPUs
                       without VNNI multiplies u8 x s8 in saturating 16-bit steps, so the same model gave 1-4 points lower
                       strict recall on some GitHub runners than on VNNI CPUs. Unsigned weights (u8) use the u8 x u8
                       kernel, which does not saturate, at full 8-bit precision. s8-7bit (reduce_range) also avoids the
                       saturation but cost 2-4 points of indirect recall in our measurements.
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
wfmt = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--weights=")), "u8")
reduce_range = wfmt == "s8-7bit"
quantize_dynamic(fp32, f"{dst}/onnx/model_quantized.onnx", weight_type=QuantType.QUInt8 if wfmt == "u8" else QuantType.QInt8, reduce_range=reduce_range,
                 op_types_to_quantize=["MatMul"] if matmul_only else None)
print({f: round(os.path.getsize(f"{dst}/onnx/{f}") / 1e6, 1) for f in os.listdir(f"{dst}/onnx")}, "MB",
      "(MatMul only)" if matmul_only else "(all supported ops, incl. the embedding Gather)", f"weights={wfmt}")
