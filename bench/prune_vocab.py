"""B1: shrink the distilled model by pruning its vocabulary to the tokens financial text actually uses.

    python bench/prune_vocab.py models/redactd-xsmall models/redactd-xsmall-pruned [--top 12000]

DeBERTa-v3's sentencepiece (Unigram) vocabulary has 128k pieces; its embedding table is most of the int8 file.
Kept pieces: special tokens, every single-character piece (so any text still tokenises, at worst into characters),
the --top highest-scoring pieces of the original vocabulary (general coverage), and every piece produced when
tokenising the TRAINING corpus (data/processed/train_*.jsonl). Eval data is never read.
The Unigram tokenizer keeps working on the smaller vocabulary: words whose pieces were dropped are segmented into
smaller kept pieces. Embedding rows are sliced to match and the model is saved in HF format for bench/export_onnx.py.
"""
import json, os, sys, glob, copy
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
src, dst = args[0], args[1]
top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 12000

tok = AutoTokenizer.from_pretrained(src)
tj = json.load(open(os.path.join(src, "tokenizer.json")))
assert tj["model"]["type"] == "Unigram", tj["model"]["type"]
vocab = tj["model"]["vocab"]                       # [[piece, score], ...]; id == index
special = {t["id"] for t in tj.get("added_tokens", [])} | {tj["model"].get("unk_id", 0)}
keep = set(special)
keep |= {i for i, (p, _) in enumerate(vocab) if len(p.replace("\u2581", "")) <= 1}
keep |= set(sorted(range(len(vocab)), key=lambda i: -vocab[i][1])[:top])
n = 0
for f in sorted(glob.glob(os.path.join(ROOT, "data/processed/train_*.jsonl"))):
    texts = [json.loads(l)["text"] for l in open(f)]
    for i in range(0, len(texts), 256):
        for ids in tok(texts[i:i + 256], add_special_tokens=False)["input_ids"]: keep.update(ids)
    n += len(texts)
# added tokens (e.g. [MASK]) can sit above the sentencepiece vocabulary: keep them after the kept pieces
extra = sorted(i for i in keep if i >= len(vocab)) + sorted(t["id"] for t in tj.get("added_tokens", []) if t["id"] >= len(vocab) and t["id"] not in keep)
keep = sorted(i for i in keep if i < len(vocab)) + sorted(set(extra))
print(f"corpus docs {n}; keeping {len(keep)} of {len(vocab)} pieces ({100 * len(keep) / len(vocab):.1f}%)", flush=True)

old2new = {o: k for k, o in enumerate(keep)}
tj2 = copy.deepcopy(tj)
tj2["model"]["vocab"] = [vocab[o] for o in keep if o < len(vocab)]
tj2["model"]["unk_id"] = old2new[tj["model"].get("unk_id", 0)]
for t in tj2.get("added_tokens", []): t["id"] = old2new[t["id"]]
def remap(obj):  # post-processor / special-token ids (e.g. TemplateProcessing)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "ids" and isinstance(v, list) and all(isinstance(x, int) for x in v): obj[k] = [old2new[x] for x in v]
            else: remap(v)
    elif isinstance(obj, list):
        for v in obj: remap(v)
remap(tj2.get("post_processor"))

model = AutoModelForTokenClassification.from_pretrained(src, dtype=torch.float32).eval()
emb = model.get_input_embeddings()
new = torch.nn.Embedding(len(keep), emb.weight.shape[1], padding_idx=old2new.get(emb.padding_idx) if emb.padding_idx is not None else None)
new.weight.data = emb.weight.data[torch.tensor(keep)].clone()
model.set_input_embeddings(new); model.config.vocab_size = len(keep)
for name in ("pad_token_id", "bos_token_id", "eos_token_id", "cls_token_id", "sep_token_id", "mask_token_id", "unk_token_id"):
    v = getattr(model.config, name, None)
    if isinstance(v, int) and v in old2new: setattr(model.config, name, old2new[v])
os.makedirs(dst, exist_ok=True)
model.save_pretrained(dst)
json.dump(tj2, open(os.path.join(dst, "tokenizer.json"), "w"), ensure_ascii=False)
for f in ("tokenizer_config.json", "special_tokens_map.json"):
    if os.path.exists(os.path.join(src, f)):
        c = json.load(open(os.path.join(src, f)))
        dec = c.get("added_tokens_decoder")
        if isinstance(dec, dict): c["added_tokens_decoder"] = {str(old2new[int(k)]): v for k, v in dec.items() if int(k) in old2new}
        json.dump(c, open(os.path.join(dst, f), "w"), indent=1)
# sanity: the pruned tokenizer must load, and must give the same pieces as the original on typical text
t2 = AutoTokenizer.from_pretrained(dst)
s = "Wire 500 USD to Priya Raman, IBAN GB82WEST12345698765432, SWIFT NWBKGB2L, ref :50K:/0049821774471."
a = [tok.convert_ids_to_tokens(x) for x in tok(s)["input_ids"]]; b = [t2.convert_ids_to_tokens(x) for x in t2(s)["input_ids"]]
print("same tokenisation on the sanity sentence:", a == b)
print("saved", dst)
