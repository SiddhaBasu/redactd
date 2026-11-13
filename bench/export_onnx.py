"""Export a HF token-classification model to ONNX (+ dynamic int8) in transformers.js layout."""
import sys, os, torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from onnxruntime.quantization import quantize_dynamic, QuantType
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(f"{dst}/onnx", exist_ok=True)
tok = AutoTokenizer.from_pretrained(src); model = AutoModelForTokenClassification.from_pretrained(src).eval()
tok.save_pretrained(dst); model.config.save_pretrained(dst)
x = tok("Wire 500 USD to John Smith account 12345678", return_tensors="pt")
torch.onnx.export(model, (x["input_ids"], x["attention_mask"]), f"{dst}/onnx/model.onnx",
                  input_names=["input_ids", "attention_mask"], output_names=["logits"],
                  dynamic_axes={"input_ids": {0: "b", 1: "s"}, "attention_mask": {0: "b", 1: "s"}, "logits": {0: "b", 1: "s"}},
                  opset_version=17, dynamo=False)
quantize_dynamic(f"{dst}/onnx/model.onnx", f"{dst}/onnx/model_quantized.onnx", weight_type=QuantType.QInt8)
print({f: round(os.path.getsize(f"{dst}/onnx/{f}") / 1e6, 1) for f in os.listdir(f"{dst}/onnx")}, "MB")
