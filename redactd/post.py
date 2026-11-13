"""Span post-processing shared by the API and (as a line-for-line port) the browser: apps/web/lib/redact.ts.

    finalize(text, raw_spans, Options) -> list[Span]
        trim -> thresholds -> merge (with provenance) -> precision filters -> propagate -> user terms -> keep-last-4

Keep this file and redact.ts in step; tests/test_rule_parity.py runs both on the same inputs.
Only ASCII character classes are used for boundary logic so Python and JavaScript agree.
"""
from __future__ import annotations
import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field, asdict
from . import lexicon as lex

@dataclass
class Span:
    start: int
    end: int
    type: str
    source: str                      # "rules" | "openmed" | "gliner" | "distilled" | "slm" | "propagated" | "manual" | "custom"
    score: float | None = None       # model confidence; None for rules
    label: str | None = None         # rule id or the model's fine label
    why: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

@dataclass
class Options:
    sensitivity: float = 0.35        # floor for model scores; per-type thresholds below can only raise it
    thresholds: dict | None = None   # {source: {type: min_score}}; None -> lexicon.THRESHOLDS
    solo_thresholds: dict | None = None   # {source: {fine_label: min_score}} for findings nothing else supports; None -> lexicon
    org_allowlist: bool = True       # drop ORG spans that are public bodies / regulators / exchanges / networks
    drop_nonpersonal_dates: bool = True   # drop "Q3 2025", "FY2024", bare years
    keep_last4: bool = False         # leave the last four digits of long financial identifiers visible
    custom_terms: list[str] = field(default_factory=list)   # always redact these strings
    allow_terms: list[str] = field(default_factory=list)    # never redact these strings
    exclude_types: list[str] = field(default_factory=list)  # e.g. ["ORG", "DATE"] for the "Share with LLM" preset

def _is_letter(c: str) -> bool: return ("a" <= c <= "z") or ("A" <= c <= "Z")
def _is_digit(c: str) -> bool: return "0" <= c <= "9"
def _is_upper(c: str) -> bool: return c.upper() == c and c.lower() != c
def _has_digit(v: str) -> bool: return any(_is_digit(c) for c in v)
def _has_alnum(v: str) -> bool: return any(_is_letter(c) or _is_digit(c) or ord(c) > 127 for c in v)
WS = " \t\n\r\f\v\u00a0"
TRIM_CHARS = WS + ",;:"

def trim_bounds(text: str, s: int, e: int) -> tuple[int, int]:
    """Tokenizer offsets can include a leading space or trailing punctuation. Never strip brackets:
    that once turned "(415)" into "([CONTACT_2]"."""
    while s < e and text[s] in TRIM_CHARS: s += 1
    while e > s and text[e - 1] in TRIM_CHARS: e -= 1
    return s, e

def snap_digits(text: str, s: int, e: int) -> tuple[int, int]:
    """A finding that cuts a run of digits in half is widened to the whole run. Otherwise the redacted half can
    reappear in clear elsewhere once its neighbouring digits are replaced (the leak check found this on held-out
    data), and the half left visible usually identifies the number anyway."""
    if s < e and _is_digit(text[s]):
        while s > 0 and _is_digit(text[s - 1]): s -= 1
    if s < e and _is_digit(text[e - 1]):
        while e < len(text) and _is_digit(text[e]): e += 1
    return s, e

def occurrences(text: str, v: str) -> list[tuple[int, int]]:
    """Every place `v` occurs as a value. Letters-only values must not be glued to other letters ("Art" does not
    match inside "Article"); short numeric values must not be glued to other digits. Longer values that contain
    digits match anywhere, so identifiers glued to text (SWIFT/FIX fields) are still caught."""
    if not v: return []
    digit = _has_digit(v); out = []; n = len(v); i = text.find(v)
    while i >= 0:
        j = i + n; ok = True
        if not digit:
            if _is_letter(v[0]) and i > 0 and _is_letter(text[i - 1]): ok = False
            if _is_letter(v[-1]) and j < len(text) and _is_letter(text[j]): ok = False
        elif n < 6:
            if _is_digit(v[0]) and i > 0 and _is_digit(text[i - 1]): ok = False
            if _is_digit(v[-1]) and j < len(text) and _is_digit(text[j]): ok = False
        if ok: out.append((i, j)); i = text.find(v, j)
        else: i = text.find(v, i + 1)
    return out

def _boundary_ok(text: str, v: str, i: int, j: int, digit: bool) -> bool:
    n = j - i
    if not digit:
        if _is_letter(v[0]) and i > 0 and _is_letter(text[i - 1]): return False
        if _is_letter(v[-1]) and j < len(text) and _is_letter(text[j]): return False
    elif n < 6:
        if _is_digit(v[0]) and i > 0 and _is_digit(text[i - 1]): return False
        if _is_digit(v[-1]) and j < len(text) and _is_digit(text[j]): return False
    return True

def occurrences_many(text: str, values: list[str]) -> list[tuple[int, int, int]]:
    """occurrences() for many values in ONE pass over the text: -> [(start, end, index into values)], ordered by
    start, then by value order. Same result per value as occurrences() (left to right, non-overlapping). A 1 MB
    document with thousands of distinct values would otherwise need thousands of full scans."""
    K = 4
    by_key: dict[str, list[int]] = {}; lens = set()
    for k, v in enumerate(values):
        if len(v) < 2: continue
        key = v[:K]; lens.add(len(key)); by_key.setdefault(key, []).append(k)
    if not by_key: return []
    lens = sorted(lens); digit = [_has_digit(v) for v in values]; nxt = [0] * len(values); out = []; L = len(text)
    for i in range(L):
        for kl in lens:
            cand = by_key.get(text[i:i + kl])
            if not cand: continue
            for k in cand:
                v = values[k]; j = i + len(v)
                if i < nxt[k] or j > L or not text.startswith(v, i): continue
                if _boundary_ok(text, v, i, j, digit[k]): out.append((i, j, k)); nxt[k] = j
    return out

# ---------------------------------------------------------------- merge
def merge_spans(text: str, spans: list[Span]) -> list[Span]:
    """Union overlapping spans. Type: a rule covering at least half of the union wins (validated patterns beat model
    guesses); otherwise the longest member. Provenance (sources, why, max model score) is kept for the review UI."""
    spans = sorted((s for s in spans if s.end > s.start), key=lambda s: (s.start, s.end))
    groups: list[list[Span]] = []; end = -1
    for s in spans:
        if groups and s.start < end: groups[-1].append(s); end = max(end, s.end)
        else: groups.append([s]); end = s.end
    out = []
    for g in groups:
        a, b = g[0].start, max(x.end for x in g)
        best = None
        for x in g:  # first longest rule member that covers >= half
            if x.source == "rules" and 2 * (x.end - x.start) >= (b - a) and (best is None or x.end - x.start > best.end - best.start): best = x
        if best is None:
            for x in g:
                if best is None or x.end - x.start > best.end - best.start: best = x
        scores = [x.score for x in g if x.score is not None]
        sources, why = [], []
        for x in g:
            for src in (x.sources or [x.source]):
                if src not in sources: sources.append(src)
            for w in x.why:
                if w not in why: why.append(w)
        out.append(Span(a, b, best.type, best.source, max(scores) if scores else None, best.label, why, sources))
    return out

# ---------------------------------------------------------------- precision filters
_WS = re.compile(r"[ \t\n\r\f\v]+")
def norm_term(v: str) -> str:
    v = _WS.sub(" ", v).strip(WS).lower()
    while v and v[-1] in ".,;:": v = v[:-1]
    if v.startswith("the "): v = v[4:]
    return v

_PUBLIC_RX = re.compile(lex.PUBLIC_BODY_PATTERN, re.ASCII | re.IGNORECASE)
_NONPERSONAL_DATE_RX = re.compile(lex.NONPERSONAL_DATE_PATTERN, re.ASCII | re.IGNORECASE)
_ORG_ALLOW = frozenset(lex.ORG_ALLOWLIST); _GENERIC = frozenset(lex.GENERIC_TERMS)

def is_public_body(v: str) -> bool:
    n = norm_term(v)
    return n in _ORG_ALLOW or _PUBLIC_RX.fullmatch(n) is not None

def is_nonpersonal_date(v: str) -> bool:
    return _NONPERSONAL_DATE_RX.fullmatch(v.strip(WS)) is not None

def passes_filters(text: str, sp: Span, o: Options, allow: frozenset) -> bool:
    v = text[sp.start:sp.end]
    if not _has_alnum(v): return False
    if sp.type in o.exclude_types: return False
    if allow and norm_term(v) in allow: return False
    if sp.source in ("manual", "custom"): return True
    if norm_term(v) in _GENERIC and not (sp.type == "NAME" and v[:1].isupper() and norm_term(v) in _COMMON): return False   # "Banks" can be a surname
    if o.org_allowlist and sp.type == "ORG" and is_public_body(v): return False
    if o.drop_nonpersonal_dates and sp.type == "DATE" and is_nonpersonal_date(v): return False
    return True

def above_threshold(sp: Span, o: Options) -> bool:
    if sp.score is None: return True
    th = (o.thresholds if o.thresholds is not None else lex.THRESHOLDS).get(sp.source, {}).get(sp.type, 0.0)
    return sp.score >= max(th, 0.0)

def drop_unsupported(spans: list[Span], o: Options) -> list[Span]:
    """Drop model findings that no rule and no other model overlaps, when their score is under the per-label
    'solo' threshold. Input and output order is preserved."""
    table = o.solo_thresholds if o.solo_thresholds is not None else lex.SOLO_THRESHOLDS
    if not table: return spans
    by_other: dict[str, tuple[list[int], list[int]]] = {}
    def others(src):
        if src not in by_other:
            xs = sorted((x.start, x.end) for x in spans if x.source != src)
            starts = [a for a, _ in xs]; pmax = []; m = -1
            for _, b in xs: m = max(m, b); pmax.append(m)
            by_other[src] = (starts, pmax)
        return by_other[src]
    out = []
    for sp in spans:
        th = table.get(sp.source, {}).get(sp.label or "", 0.0) if sp.score is not None else 0.0
        if th > 0 and sp.score < th:
            starts, pmax = others(sp.source)
            i = bisect_left(starts, sp.end) - 1          # last other span starting before this one ends
            if i < 0 or pmax[i] <= sp.start: continue    # nothing overlaps: unsupported and under threshold
        out.append(sp)
    return out

# ---------------------------------------------------------------- propagation (consistency + coreference)
_POSSESSIVE = re.compile(r"['’]s$")
_SPLIT = re.compile(r"[ \t\n\r\f\v,]+")
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}", re.ASCII)
_HANDLE = re.compile(r"[A-Za-z0-9._-]+", re.ASCII)
_STOP = frozenset(lex.NAME_PART_STOP); _COMMON = frozenset(lex.COMMON_WORD_NAMES)

def name_parts(v: str) -> list[str]:
    base = _POSSESSIVE.sub("", v)
    parts = []
    for p in _SPLIT.split(base):
        p = _POSSESSIVE.sub("", p.strip(".,;:()\"'"))
        if p: parts.append(p)
    return parts

def name_variants(v: str) -> list[tuple[str, str]]:
    """Other ways a detected person name is written: its parts, ALL-CAPS forms, and initials. -> [(string, why)]"""
    out: list[tuple[str, str]] = []; seen = {v}
    def add(s, why):
        if s not in seen and len(s) >= 2: seen.add(s); out.append((s, why))
    base = _POSSESSIVE.sub("", v)
    if len(base) >= 3: add(base, "possessive form of a detected name")
    parts = [p for p in name_parts(v) if p.lower() not in _STOP]
    for p in parts:
        if len(p) >= 3 and _is_upper(p[0]): add(p, "part of a detected name")
    if len(base) >= 5 and base.upper() != base: add(base.upper(), "detected name in capitals")
    for p in parts:
        if len(p) >= 4 and _is_upper(p[0]) and p.upper() != p and p.lower() not in _COMMON: add(p.upper(), "part of a detected name in capitals")
    alpha = [p for p in parts if len(p) >= 2 and "A" <= p[0] <= "Z" and all(_is_letter(c) or c in "-'" for c in p)]
    if len(alpha) >= 2:
        f, l = alpha[0], alpha[-1]
        for s in (f"{f[0]}. {l}", f"{f[0]}.{l}", f"{f[0]} {l}"): add(s, "initial + surname of a detected name")
        ini = "".join(p[0] for p in alpha)
        if 2 <= len(ini) <= 4: add(ini, "initials of a detected name")
    return out

def propagate_spans(text: str, spans: list[Span], min_len: int = 3) -> list[Span]:
    """Redact every other occurrence of each detected value, plus the coreferent forms of person names:
    name parts, initials ("P. Raman", "PR"), possessives, ALL-CAPS headers, and email addresses / login handles
    whose local part contains a detected name."""
    extra: list[Span] = []; seen: set[tuple[str, str]] = set(); handle_parts: list[str] = []
    needles: list[str] = []; meta: list[tuple[str, str | None, str]] = []      # value -> (type, label, why)
    for sp in spans:
        v = text[sp.start:sp.end]
        if len(v) < min_len or (v, sp.type) in seen: continue
        seen.add((v, sp.type))
        needles.append(v); meta.append((sp.type, sp.label, "same value as another finding"))
        if sp.type == "NAME":
            for s, why in name_variants(v):
                needles.append(s); meta.append(("NAME", sp.label, why))
            for p in name_parts(v):
                if len(p) >= 5 and p.lower() not in _STOP and p.lower() not in _COMMON and all(_is_letter(c) for c in p):
                    if p.lower() not in handle_parts: handle_parts.append(p.lower())
    for a, b, k in occurrences_many(text, needles):
        t, lab, why = meta[k]
        extra.append(Span(a, b, t, "propagated", None, lab, [why], ["propagated"]))
    if handle_parts:
        for m in _EMAIL.finditer(text):
            local = m.group().split("@")[0].lower()
            if any(p in local for p in handle_parts):
                extra.append(Span(m.start(), m.end(), "CONTACT", "propagated", None, "email", ["email address contains a detected name"], ["propagated"]))
        for m in _HANDLE.finditer(text):
            a, b = m.start(), m.end()
            while a < b and text[a] in "._-": a += 1
            while b > a and text[b - 1] in "._-": b -= 1
            tok = text[a:b]; low = tok.lower()
            if any(_is_digit(c) or c in "._" for c in tok) and any(_is_letter(c) for c in tok) and any(p in low for p in handle_parts):
                extra.append(Span(a, b, "NAME", "propagated", None, "user_name", ["login or handle contains a detected name"], ["propagated"]))
    # existing findings keep their identity; propagated spans only add coverage
    starts = [sp.start for sp in spans]   # spans are merged: sorted and non-overlapping
    def covered(x):
        i = bisect_right(starts, x.start) - 1
        return i >= 0 and spans[i].end >= x.end
    extra = [x for x in extra if not covered(x)]
    if not extra: return spans
    return merge_spans(text, list(spans) + extra)

# ---------------------------------------------------------------- user terms + keep-last-4
def apply_terms(text: str, spans: list[Span], custom_terms: list[str], allow_terms: list[str]) -> list[Span]:
    allow = frozenset(norm_term(t) for t in allow_terms if norm_term(t))
    if allow: spans = [s for s in spans if norm_term(text[s.start:s.end]) not in allow]
    extra = []
    for t in custom_terms:
        t = t.strip(WS)
        if len(t) < 2: continue
        low, tl, i = text.lower(), t.lower(), 0
        if len(low) != len(text): low = text  # exotic case mappings change length; fall back to exact case
        while True:
            i = low.find(tl, i)
            if i < 0: break
            extra.append(Span(i, i + len(t), "CUSTOM", "custom", None, "custom_term", ["matches one of your custom terms"], ["custom"]))
            i += len(t)
    return merge_spans(text, spans + extra) if extra else spans

def keep_last4(text: str, spans: list[Span]) -> list[Span]:
    """Shrink long financial identifiers so their last four digits stay visible; drop already-masked partials."""
    out = []
    for sp in spans:
        if sp.type != "FIN_ID": out.append(sp); continue
        if sp.label in lex.MASKED_RULE_IDS: continue          # "****4471" is already a last-4 form: leave as is
        v = text[sp.start:sp.end]
        if sum(1 for c in v if _is_digit(c)) < 8: out.append(sp); continue
        k, e = 0, sp.end
        while e > sp.start and k < 4:
            e -= 1
            if _is_digit(text[e]): k += 1
            elif not (text[e] in " -"): break
        if k == 4:
            a, b = trim_bounds(text, sp.start, e)
            while b > a and text[b - 1] in " -": b -= 1
            if b > a: out.append(Span(a, b, sp.type, sp.source, sp.score, sp.label, sp.why + ["last 4 digits kept visible"], sp.sources))
        else: out.append(sp)
    return out

# ---------------------------------------------------------------- the whole post-processing chain
def close_leaks(text: str, spans: list[Span], o: Options, allow: frozenset) -> list[Span]:
    """Zero-leak invariant: after every filter has run, any value that is still being redacted must be redacted at
    ALL of its occurrences. (A propagated occurrence can be lost when it was merged into a longer finding that a
    precision filter then dropped.) Uncovered occurrences are added back; nothing is removed."""
    for _ in range(2):
        vals: list[str] = []; types: dict[str, Span] = {}
        for sp in spans:
            v = text[sp.start:sp.end]
            if len(v) >= 3 and v not in types: types[v] = sp; vals.append(v)
        if not vals: return spans
        starts = [sp.start for sp in spans]; extra = []
        for a, b, k in occurrences_many(text, vals):
            i = bisect_right(starts, a) - 1
            if i >= 0 and spans[i].end >= b: continue
            src = types[vals[k]]
            extra.append(Span(a, b, src.type, "propagated", None, src.label, ["same value as another finding"], ["propagated"]))
        extra = outside_placeholders(text, extra)
        if not extra: return spans
        spans = merge_spans(text, list(spans) + extra)
    return spans

PLACEHOLDER = re.compile(r"\[[A-Z_]+_[0-9a-f]+\]", re.ASCII)

def outside_placeholders(text: str, spans: list[Span]) -> list[Span]:
    """Drop findings that sit inside a placeholder the document already contains ("[NAME_1]" from an earlier
    redaction). Redacting inside one would corrupt it and collide with the placeholders we generate."""
    if "[" not in text: return spans
    toks = [m.span() for m in PLACEHOLDER.finditer(text)]
    if not toks: return spans
    starts = [a for a, _ in toks]; out = []
    for sp in spans:
        i = bisect_right(starts, sp.start) - 1
        if i >= 0 and sp.end <= toks[i][1] and sp.source not in ("manual", "custom"): continue
        out.append(sp)
    return out

def finalize(text: str, raw: list[Span], o: Options | None = None) -> list[Span]:
    o = o or Options()
    allow = frozenset(norm_term(t) for t in o.allow_terms if norm_term(t))
    kept = []
    for sp in raw:
        s, e = trim_bounds(text, sp.start, sp.end)
        if e <= s or not above_threshold(sp, o): continue
        if sp.source not in ("manual", "custom"): s, e = snap_digits(text, s, e)
        kept.append(Span(s, e, sp.type, sp.source, sp.score, sp.label, list(sp.why), list(sp.sources)))
    kept = drop_unsupported(outside_placeholders(text, kept), o)
    merged = [sp for sp in merge_spans(text, kept) if passes_filters(text, sp, o, allow)]
    out = [sp for sp in outside_placeholders(text, propagate_spans(text, merged)) if passes_filters(text, sp, o, allow)]
    out = close_leaks(text, out, o, allow)
    out = apply_terms(text, out, o.custom_terms, o.allow_terms)
    if o.keep_last4: out = keep_last4(text, out)
    res = []
    for sp in out:
        s, e = trim_bounds(text, sp.start, sp.end)
        if e > s: sp.start, sp.end = s, e; res.append(sp)
    return res

def spans_json(spans: list[Span]) -> list[dict]:
    return [asdict(s) for s in spans]
