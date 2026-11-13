"""Fine-tune microsoft/deberta-v3-small for PII token classification (BIO, coarse types) on CPU.
Train data: Nemotron-PII train subset (finance-weighted). Gretel finance is held out entirely."""
import json, os, sys, time, random, torch, numpy as np
from transformers import AutoTokenizer, AutoModelForTokenClassification, get_linear_schedule_with_warmup
sys.path.insert(0, os.path.dirname(__file__))
from coarse import COARSE, TYPES

ROOT = os.path.join(os.path.dirname(__file__), "..")
torch.set_num_threads(int(os.environ.get("THREADS", 3)))
random.seed(0); torch.manual_seed(0)
BASE = "microsoft/deberta-v3-small"
MAXLEN, STRIDE, BS, EPOCHS, LR = 256, 64, 8, float(os.environ.get("EPOCHS", 1.5)), 5e-5
NDOCS = int(os.environ.get("NDOCS", 4000))
labels = ["O"] + [f"{p}-{t}" for t in TYPES for p in ("B", "I")]
l2i = {l: i for i, l in enumerate(labels)}

tok = AutoTokenizer.from_pretrained(BASE)
rows = [json.loads(l) for l in open(f"{ROOT}/data/processed/train_nemotron.jsonl")][:NDOCS]

def encode(r):
    enc = tok(r["text"], return_offsets_mapping=True, truncation=True, max_length=MAXLEN,
              stride=STRIDE, return_overflowing_tokens=True)
    out = []
    for w in range(len(enc["input_ids"])):
        offs = enc["offset_mapping"][w]; lab = []
        for (a, b) in offs:
            if a == b: lab.append(-100); continue
            tag = "O"
            for s in r["spans"]:
                if a < s["end"] and b > s["start"]:
                    t = COARSE[s["label"]]
                    tag = ("B-" if a <= s["start"] else "I-") + t
                    break
            lab.append(l2i[tag])
        out.append((enc["input_ids"][w], lab))
    return out

data = [x for r in rows for x in encode(r)]
print("windows", len(data), flush=True)
model = AutoModelForTokenClassification.from_pretrained(BASE, num_labels=len(labels),
            id2label=dict(enumerate(labels)), label2id=l2i)
opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
steps = int(len(data) / BS * EPOCHS)
sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
model.train(); t0 = time.time(); step = 0
while step < steps:
    random.shuffle(data)
    for i in range(0, len(data), BS):
        if step >= steps: break
        b = data[i:i + BS]; L = max(len(x[0]) for x in b)
        ids = torch.tensor([x[0] + [tok.pad_token_id] * (L - len(x[0])) for x in b])
        att = (ids != tok.pad_token_id).long()
        lab = torch.tensor([x[1] + [-100] * (L - len(x[1])) for x in b])
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sch.step(); opt.zero_grad(); step += 1
        if step % 25 == 0:
            el = time.time() - t0
            print(f"step {step}/{steps} loss {loss.item():.4f} elapsed {el/60:.1f}m eta {(steps-step)*el/step/60:.1f}m", flush=True)
out = f"{ROOT}/models/deberta-v3-small-pii-fin"
model.save_pretrained(out); tok.save_pretrained(out)
print("saved", out, "train_minutes", (time.time() - t0) / 60, flush=True)
