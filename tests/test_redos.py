"""E2: regex denial-of-service guard. Every rule (and the post-processing chain) must stay near-linear on long
adversarial input. Python's `re` has no timeout, so the defence is by construction (bounded quantifiers, see the
portability contract in redactd/rules.py) and this fuzz test, which fails the build if a rule goes super-linear.
The API additionally caps input at 1 MB and runs detection in a bounded worker pool.
"""
import os, random, sys, time
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd import rules
from redactd.post import Span, finalize

N = 60_000
SEEDS = {
    "spaces": " " * N, "digits": "1" * N, "digit groups": "1234 " * (N // 5), "digit dashes": "12-" * (N // 3),
    "caps words": "Abc " * (N // 4), "caps of": "Abc of the and " * (N // 15), "initials": "A.B." * (N // 4), "upper": "ABCD " * (N // 5),
    "upper run": "A" * N, "lower run": "a" * N, "email-ish": "a@" * (N // 2), "email dots": "a.b-c+d" * (N // 7) + "@", "dots": "a." * (N // 2),
    "url-ish": "http://" * (N // 7), "www": "www." * (N // 4), "colons": "ab:" * (N // 3), "hex colons": "ff:" * (N // 3),
    "iban-ish": "GB82 WEST " * (N // 10), "iban glued": "GB82" + "A1B2" * (N // 4), "iban sep": "DE89 " + "1 " * (N // 2),
    "masks": "*" * N, "mask groups": "**** " * (N // 5), "x run": "xX" * (N // 2), "plus": "+1 " * (N // 3), "parens": "(0" * (N // 2),
    "street-ish": "12 Abc Def " * (N // 11), "street tail": "1 Main St" + ", Abc" * (N // 5), "zip-ish": "12345 " * (N // 6),
    "keywords": "account number " * (N // 15), "kw colon": "password:" * (N // 9), "ending": "ending in " * (N // 10),
    "coords": "1.2345 " * (N // 7), "quotes": "'s" * (N // 2), "mr": "Mr. " * (N // 4), "bank of": "Bank of " * (N // 8),
    "newlines": "\n" * N, "mixed": "".join(random.Random(1).choice("aA1 .-@:/,*\n") for _ in range(N)),
    "unicode": "é漢😀 " * (N // 5), "tabs": "\t1\t" * (N // 3), "swift tags": ":50K:/" * (N // 6), "fix": "448=" * (N // 4),
}

def _time(fn, arg):
    best = 1e9
    for _ in range(2):
        t = time.perf_counter(); fn(arg); best = min(best, time.perf_counter() - t)
    return best

@pytest.mark.parametrize("name", sorted(SEEDS))
def test_rules_are_near_linear(name):
    s = SEEDS[name]
    t1 = _time(rules.detect_detailed, s[:N // 2]); t2 = _time(rules.detect_detailed, s)
    assert t2 < 3.0, f"{name}: {t2:.2f}s for {N} chars"
    assert t2 < max(0.05, 3.5 * t1), f"{name}: super-linear ({t1:.3f}s -> {t2:.3f}s when input doubles)"

def test_each_rule_alone_is_fast_on_every_seed():
    slow = []
    for rid, _, rx, _ in rules.COMPILED:
        for name, s in SEEDS.items():
            t = time.perf_counter(); sum(1 for _ in rx.finditer(s + "\n")); dt = time.perf_counter() - t
            if dt > 1.0: slow.append((rid, name, round(dt, 2)))
    assert not slow, slow

def test_postprocessing_is_near_linear_in_findings():
    def run(n):
        text = " ".join(f"Name{i} Sur{i} {1000000 + i}" for i in range(n))
        raw, pos = [], 0
        for i in range(n):
            a = f"Name{i} Sur{i}"; raw.append(Span(pos, pos + len(a), "NAME", "openmed", 0.9, "name", [], ["openmed"])); pos += len(a) + 1
            b = str(1000000 + i); raw.append(Span(pos, pos + len(b), "FIN_ID", "gliner", 0.5, "customer id", [], ["gliner"])); pos += len(b) + 1
        t = time.perf_counter(); out = finalize(text, raw); return time.perf_counter() - t, len(out)
    t1, n1 = run(500); t2, n2 = run(1000)
    assert n2 >= 2000 and t2 < 20, (t2, n2)
    assert t2 < 5 * t1 + 0.5, f"post-processing looks quadratic in the number of findings: {t1:.2f}s -> {t2:.2f}s"
