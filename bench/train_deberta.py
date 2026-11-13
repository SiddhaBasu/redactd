"""B1 step 3: train the single distilled token classifier (BIO over the 10 coarse types) on CPU.

    BASE=microsoft/deberta-v3-xsmall OUT=models/redactd-xsmall EPOCHS=2 python bench/train_deberta.py

Data: data/processed/train_distill.jsonl (gold ∪ ensemble labels; see bench/make_distill.py).
Lessons kept: transformers v5 loads DeBERTa-v3 in its stored fp16; fp16 on CPU gives NaN loss from step 1, so the
model is loaded with dtype=torch.float32 and training aborts on a non-finite loss. Checkpoints are written every
SAVE_EVERY steps so a long CPU run can be evaluated (or resumed with RESUME=1) before it finishes.
"""
import json, os, sys, time, random, torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, get_linear_schedule_with_warmup
sys.path.insert(0, os.path.dirname(__file__))
from coarse import TYPES

ROOT = os.path.join(os.path.dirname(__file__), "..")
E = os.environ.get
torch.set_num_threads(int(E("THREADS", 3)))
random.seed(0); torch.manual_seed(0)
BASE = E("BASE", "microsoft/deberta-v3-xsmall"); OUT = os.path.join(ROOT, E("OUT", "models/redactd-xsmall"))
MAXLEN, STRIDE, BS, EPOCHS, LR = int(E("MAXLEN", 256)), 64, int(E("BS", 16)), float(E("EPOCHS", 2)), float(E("LR", 8e-5))
NDOCS, SAVE_EVERY, MAX_MIN = int(E("NDOCS", 0)), int(E("SAVE_EVERY", 250)), float(E("MAX_MINUTES", 0))
labels = ["O"] + [f"{p}-{t}" for t in TYPES for p in ("B", "I")]
l2i = {l: i for i, l in enumerate(labels)}

resume = E("RESUME") == "1" and os.path.exists(f"{OUT}/train_state.json")
tok = AutoTokenizer.from_pretrained(BASE)
rows = [json.loads(l) for l in open(f"{ROOT}/data/processed/{E('DATA', 'train_distill')}.jsonl")]
if NDOCS: rows = rows[:NDOCS]

def encode(r):
    enc = tok(r["text"], return_offsets_mapping=True, truncation=True, max_length=MAXLEN, stride=STRIDE, return_overflowing_tokens=True)
    spans = sorted(r["spans"]); out = []
    for w in range(len(enc["input_ids"])):
        lab = []; k = 0
        for (a, b) in enc["offset_mapping"][w]:
            if a == b: lab.append(-100); continue
            while k < len(spans) and spans[k][1] <= a: k += 1
            tag = "O"
            if k < len(spans) and b > spans[k][0] and a < spans[k][1]:
                # offsets include the leading space: a token that starts at or before the span start opens it
                tag = ("B-" if a <= spans[k][0] or (a == spans[k][0] + 0) else "I-") + spans[k][2]
            lab.append(l2i[tag])
        out.append((enc["input_ids"][w], lab))
    return out

data = [x for r in rows for x in encode(r)]
print("docs", len(rows), "windows", len(data), "base", BASE, flush=True)
model = AutoModelForTokenClassification.from_pretrained(OUT if resume else BASE, num_labels=len(labels), dtype=torch.float32,
            id2label=dict(enumerate(labels)), label2id=l2i)
opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
steps = int(len(data) / BS * EPOCHS)
sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
step = 0
if resume:
    st = json.load(open(f"{OUT}/train_state.json")); step = st["step"]
    for _ in range(step): sch.step()
    print("resumed at step", step, flush=True)
def save():
    model.save_pretrained(OUT); tok.save_pretrained(OUT); json.dump({"step": step, "steps": steps, "base": BASE}, open(f"{OUT}/train_state.json", "w"))
model.train(); t0 = time.time(); start = step; stop = False
# length-bucketed batches: sort windows by length inside shuffled chunks so padding is small
while step < steps and not stop:
    random.shuffle(data)
    chunks = [sorted(data[i:i + BS * 50], key=lambda x: len(x[0])) for i in range(0, len(data), BS * 50)]
    batches = [c[i:i + BS] for c in chunks for i in range(0, len(c), BS)]; random.shuffle(batches)
    for b in batches:
        if step >= steps: break
        L = max(len(x[0]) for x in b)
        ids = torch.tensor([x[0] + [tok.pad_token_id] * (L - len(x[0])) for x in b])
        att = torch.tensor([[1] * len(x[0]) + [0] * (L - len(x[0])) for x in b])
        lab = torch.tensor([x[1] + [-100] * (L - len(x[1])) for x in b])
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        if not torch.isfinite(loss):
            raise SystemExit(f'non-finite loss at step {step}; aborting (check dtype / LR)')
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sch.step(); opt.zero_grad(); step += 1
        if step % 25 == 0:
            el = time.time() - t0
            print(f"step {step}/{steps} loss {loss.item():.4f} elapsed {el/60:.1f}m eta {(steps-step)*el/(step-start)/60:.1f}m", flush=True)
        if step % SAVE_EVERY == 0: save()
        if MAX_MIN and (time.time() - t0) / 60 > MAX_MIN: print("time budget reached", flush=True); stop = True; break
save()
print("saved", OUT, "train_minutes", (time.time() - t0) / 60, "step", step, "of", steps, flush=True)
