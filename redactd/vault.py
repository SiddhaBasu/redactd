"""Two-way (reversible) redaction.

redact():  text + spans -> (redacted_text, vault)   "Pay John Smith from 0123456789" -> "Pay [NAME_1] from [FIN_ID_1]"
restore(): redacted_or_processed_text + vault -> original values put back

* Consistent placeholders: the same value always gets the same placeholder within a document.
* The vault is encrypted with a key that stays with the user (client-side in the website), so the server
  can process redacted text and the user can still restore it.
* Optional keyed-HMAC tokens give the same placeholder for the same value across documents (for joins)
  without being reversible on their own.
Mirrored by apps/web/lib/redact.ts (render/restore/leakCheck) and apps/web/lib/vault.ts (sealing, WebCrypto).
"""
import hmac, hashlib, json, re, base64, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .post import Span, merge_spans, propagate_spans, occurrences, occurrences_many, PLACEHOLDER  # noqa: F401

def _spans(tuples):
    return [Span(s, e, t, "x") for s, e, t, *_ in tuples]

def merge(spans):
    """Union overlapping (start, end, type) tuples; the longer member's type wins."""
    return [(s.start, s.end, s.type) for s in merge_spans("", _spans(spans))]

def propagate(text, spans, min_len=3):
    """Redact every occurrence of each detected value, plus coreferent name forms. Tuple wrapper around post.propagate_spans."""
    return [(s.start, s.end, s.type) for s in propagate_spans(text, merge_spans(text, _spans(spans)), min_len)]

def redact(text, spans, hmac_key: bytes | None = None, style: str = "placeholder"):
    """spans: (start, end, type) tuples that are already final (Pipeline.detect output). style: placeholder | label | block."""
    spans = merge(spans)
    out, vault, counters, seen, last = [], {}, {}, {}, 0
    taken = set(PLACEHOLDER.findall(text))      # placeholders the document already contains must not be reused
    for s, e, t in spans:
        val = text[s:e]
        key = (t, val)
        if key not in seen:
            if hmac_key:
                tag = hmac.new(hmac_key, f"{t}:{val}".encode(), hashlib.sha256).hexdigest()[:8]
                ph = f"[{t}_{tag}]"
            else:
                counters[t] = counters.get(t, 0) + 1
                while f"[{t}_{counters[t]}]" in taken: counters[t] += 1
                ph = f"[{t}_{counters[t]}]"
            seen[key] = ph; vault[ph] = val
        out.append(text[last:s]); last = e
        out.append(seen[key] if style == "placeholder" else f"[{t}]" if style == "label" else "█" * 6)
    out.append(text[last:])
    return "".join(out), vault

def restore(text, vault):
    return re.sub(r"\[[A-Z_]+_[0-9a-f]+\]", lambda m: vault.get(m.group(0), m.group(0)), text)

def leak_check(redacted, vault):
    """Verify no redacted value survives in the output (the step most tools skip). Uses the same occurrence
    test as propagation: 'Art' inside 'Article' is not a leak, 'Art' on its own is."""
    vals = sorted({v for v in vault.values() if len(v) >= 3})
    return sorted({vals[k] for _, _, k in occurrences_many(redacted, vals)})

def seal(vault, key: bytes):
    n = os.urandom(12)
    return base64.b64encode(n + AESGCM(key).encrypt(n, json.dumps(vault).encode(), None)).decode()

def unseal(blob, key: bytes):
    raw = base64.b64decode(blob)
    return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], None))
