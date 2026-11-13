"""Two-way (reversible) redaction.

redact():  text -> (redacted_text, vault)   e.g. "Pay John Smith from 0123456789" -> "Pay [NAME_1] from [FIN_ID_1]"
restore(): redacted_or_processed_text + vault -> original values put back

* Consistent placeholders: the same value always gets the same placeholder within a document, and every
  occurrence of a detected value is redacted (even ones the detector missed).
* The vault is encrypted with a key that stays with the user (client-side in the website), so the server
  can process redacted text and the user can still restore it.
* Optional keyed-HMAC tokens give the same placeholder for the same value across documents (for joins)
  without being reversible on their own.
"""
import hmac, hashlib, json, re, base64, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def merge(spans):
    spans = sorted((s, e, t) for s, e, t in spans if e > s)
    out = []
    for s, e, t in spans:
        if out and s < out[-1][1]:
            ps, pe, pt = out[-1]
            out[-1] = (ps, max(pe, e), pt if (pe - ps) >= (e - s) else t)
        else:
            out.append((s, e, t))
    return out

def propagate(text, spans, min_len=3):
    """Redact every occurrence of each detected value (consistency), plus name parts for NAME spans."""
    extra = []
    vals = {(text[s:e], t) for s, e, t in spans if e - s >= min_len}
    for v, t in vals:
        for m in re.finditer(re.escape(v), text):
            extra.append((m.start(), m.end(), t))
        if t == "NAME":
            for part in v.split():
                if len(part) >= 3 and part[0].isupper():
                    for m in re.finditer(rf"\b{re.escape(part)}\b", text):
                        extra.append((m.start(), m.end(), t))
    return merge(list(spans) + extra)

def redact(text, spans, hmac_key: bytes | None = None):
    spans = propagate(text, merge(spans))
    out, vault, counters, seen, last = [], {}, {}, {}, 0
    for s, e, t in spans:
        val = text[s:e]
        key = (t, val)
        if key not in seen:
            if hmac_key:
                tag = hmac.new(hmac_key, f"{t}:{val}".encode(), hashlib.sha256).hexdigest()[:8]
                ph = f"[{t}_{tag}]"
            else:
                counters[t] = counters.get(t, 0) + 1
                ph = f"[{t}_{counters[t]}]"
            seen[key] = ph; vault[ph] = val
        out.append(text[last:s]); out.append(seen[key]); last = e
    out.append(text[last:])
    return "".join(out), vault

def restore(text, vault):
    return re.sub(r"\[[A-Z_]+_[0-9a-f]+\]", lambda m: vault.get(m.group(0), m.group(0)), text)

def leak_check(redacted, vault):
    """Verify no redacted value survives in the output (the step most tools skip)."""
    return [v for v in set(vault.values()) if len(v) >= 3 and v in redacted]

def seal(vault, key: bytes):
    n = os.urandom(12)
    return base64.b64encode(n + AESGCM(key).encrypt(n, json.dumps(vault).encode(), None)).decode()

def unseal(blob, key: bytes):
    raw = base64.b64decode(blob)
    return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], None))
