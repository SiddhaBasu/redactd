"""Pattern rules with validators. Pure Python, no ML.

This module is the single source of truth for the rule set. `python -m redactd.rules --export` writes
apps/web/lib/rules.generated.json, which the browser engine (apps/web/lib/rules.ts) executes. CI fails if the
generated file is stale, and tests/test_rule_parity.py asserts both engines return identical spans.

Portability contract (so Python `re` and JS `RegExp` agree character for character):
  * patterns are compiled with re.ASCII here; JS has ASCII \\w \\d \\b natively and rules.ts rewrites \\s to the
    ASCII whitespace set
  * both engines match against text + "\\n", so "end of text" is written as \\n
  * no inline flags, no `$`/`^`, no \\Z, no \\S inside a character class, no possessive/atomic groups, no named groups, no \\p{..}
  * flags are only "" or "i"; at most one capture group, whose span is the finding
  * every quantifier over a group is bounded, to keep matching linear in practice (see tests/test_redos.py)
"""
from __future__ import annotations
import json, os, re, sys

# ---------------------------------------------------------------- validators (mirrored in rules.ts)
def luhn(v: str) -> bool:
    d = [int(c) for c in v if c.isascii() and c.isdigit()]
    if not 13 <= len(d) <= 19: return False
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2: x = x * 2 - 9 if x > 4 else x * 2
        s += x
    return s % 10 == 0

def aba(v: str) -> bool:
    if len(v) != 9 or not (v.isascii() and v.isdigit()): return False
    d = [int(c) for c in v]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0

def iban_ok(v: str) -> bool:
    s = re.sub(r"[ \-]", "", v).upper()
    if not 15 <= len(s) <= 34 or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", s): return False
    r = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1

def has_digit(v: str) -> bool:
    return any(c.isascii() and c.isdigit() for c in v)

def org_shape(v: str) -> bool:
    """Two or more words, or a single all-caps token (ACME BANK is caught by the caps alternative)."""
    return len([w for w in re.split(r"[ \t\n\r\f\v]+", v) if w]) >= 2 or (v.upper() == v and v.lower() != v)

IBAN_COUNTRIES = frozenset("AD AE AL AT AZ BA BE BG BH BR BY CH CR CY CZ DE DK DO EE EG ES FI FO FR GB GE GI GL GR GT HR HU IE IL IQ IS IT JO KW KZ LB LC LI LT LU LV "
                           "MC MD ME MK MR MT MU NL NO PK PL PS PT QA RO RS SA SC SE SI SK SM ST SV TL TN TR UA VA VG XK".split())

def iban_prefix(v: str):
    """IBAN written with odd spacing, hyphens, a line break or in lower case. The pattern over-matches into the
    following words, so return the length of the longest prefix (cut where a group ends) that passes mod-97."""
    if v[:2].upper() not in IBAN_COUNTRIES: return False
    n = len(v)
    for end in range(n, 14, -1):
        if end < n and (v[end] not in " -\n" or v[end - 1] in " -\n"): continue     # only cut at the end of a group
        p = v[:end]
        if p.upper() != p and p.lower() != p: continue                              # all upper or all lower, never mixed
        if iban_ok(p.replace("\n", "")): return end
    return False

def digit_count(lo: int, hi: int):
    return lambda v: lo <= sum(1 for c in v if "0" <= c <= "9") <= hi

def masked_iban(v: str) -> bool:
    return any(c in "*\u2022" for c in v) and has_digit(v)

def coords(v: str) -> bool:
    """Two decimals in latitude/longitude range. Needs 6+ decimal places somewhere, a hemisphere letter, or a sign:
    plain 4-5 decimal pairs are usually FX rates."""
    nums = re.findall(r"[-+]?\d{1,3}\.\d+", v)
    if len(nums) != 2 or abs(float(nums[0])) > 90 or abs(float(nums[1])) > 180: return False
    return any(len(x.split(".")[1]) >= 6 for x in nums) or any(c in "NSEW" for c in v) or "-" in v

_SCHEMA_URL = re.compile(r"(?:https?://)?(?:www\.)?(?:w3\.org|xbrl\.org|fpml\.org|iso20022\.org|iso\.org|purl\.org|xmlsoap\.org|"
                         r"schemas\.[a-z0-9.-]+|xmlns\.[a-z0-9.-]+|openxmlformats\.org|json-schema\.org|ietf\.org)(?:[/:?#]|\n)", re.ASCII | re.IGNORECASE)
def personal_url(v: str) -> bool:
    """XML namespace and schema URLs (w3.org, xbrl.org, fpml.org ...) are boilerplate, not contact details."""
    return _SCHEMA_URL.match(v + "\n") is None

def mixed_alnum(v: str) -> bool:
    """A long token is only key-like if it mixes letters and digits (32 digits in a row is a record, not a key)."""
    return has_digit(v) and any(("a" <= c <= "z") or ("A" <= c <= "Z") for c in v)

VALIDATORS = {"coords": coords, "personal_url": personal_url, "mixed_alnum": mixed_alnum, "luhn": luhn, "aba": aba, "iban": iban_ok, "iban_prefix": iban_prefix, "has_digit": has_digit, "org_shape": org_shape,
              "masked_iban": masked_iban, "digits_8_15": digit_count(8, 15), "digits_9_15": digit_count(9, 15), "digits_9_11": digit_count(9, 11)}

# ---------------------------------------------------------------- rule table
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
ORG_SUFFIX = (r"Bank|Bancorp|Banking|Credit Union|Savings|Trust|Insurance(?: Company)?|Assurance|Capital|Partners|"
              r"Holdings?|Group|Fund|Funds|Investments?|Securities|Financial|Finance|Asset Management|Advisors|"
              r"Inc\.?|Incorporated|LLC|L\.L\.C\.|Ltd\.?|Limited|PLC|plc|Corp\.?|Corporation|Co\.|Company|GmbH|AG|S\.A\.|N\.V\.|LLP|LP|"
              r"Institute|University|College|Hospital|Clinic|Physical Therapy|Healthcare")

# USPS street suffix names (the common ones) plus UK/EU forms.
STREET_SUFFIX = ("St|Street|Streets|Ave|Avenue|Rd|Road|Roads|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Way|Ways|Pl|Place|Ter|Terrace|Pkwy|Parkway|"
                 "Cir|Circle|Hwy|Highway|Sq|Square|Squares|Alley|Bridge|Brook|Bypass|Canyon|Causeway|Center|Centre|Cliff|Cliffs|Close|Common|Corner|"
                 "Cove|Creek|Crescent|Crest|Crossing|Crossroad|Curve|Dale|Divide|Estate|Estates|Expressway|Extension|Falls|Ferry|Field|Fields|Flat|"
                 "Flats|Ford|Forest|Forge|Forges|Fork|Forks|Fort|Freeway|Garden|Gardens|Gateway|Glen|Green|Grove|Harbor|Harbour|Haven|Heights|Hill|"
                 "Hills|Hollow|Inlet|Island|Islands|Isle|Junction|Key|Keys|Knoll|Knolls|Lake|Lakes|Landing|Light|Lights|Lodge|Loop|Mall|Manor|Manors|"
                 "Meadow|Meadows|Mews|Mill|Mills|Mission|Motorway|Mount|Mountain|Neck|Orchard|Oval|Overpass|Park|Parks|Pass|Passage|Path|Pike|Pine|"
                 "Pines|Plain|Plains|Plaza|Point|Points|Port|Ports|Prairie|Ramp|Ranch|Rapids|Rest|Ridge|Ridges|Rise|River|Route|Row|Run|Shoal|Shoals|"
                 "Shore|Shores|Skyway|Spring|Springs|Spur|Spurs|Station|Stravenue|Stream|Summit|Throughway|Trace|Track|Trafficway|Trail|Tunnel|"
                 "Turnpike|Underpass|Union|Unions|Valley|Valleys|Via|Viaduct|View|Views|Village|Villages|Ville|Vista|Walk|Walks|Wall|Well|Wells")
# What may follow a street on the same line: up to four ", City" / ", ST 12345" / ", 12345" / ", SW1A 2DZ" / ", M5G 1M6" parts.
ADDR_TAIL = (r"(?:, ?(?:\d{5}(?:-\d{4})?|[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}|[A-Z]\d[A-Z] ?\d[A-Z]\d|"
             r"[A-Z]{2,3}(?: (?:\d{5}(?:-\d{4})?|[A-Z]\d[A-Z] ?\d[A-Z]\d))?|"
             r"[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+){0,2}(?: \d{5}(?:-\d{4})?)?)\b){0,4}")

# A word inside an organisation name: initials ("J.P."), "St.", or a capitalised word whose dots are internal only,
# so a name never runs across a sentence end ("... Responsibilities. The Company").
ORG_TOKEN = r"(?:(?:[A-Z]\.){1,4}(?=\s)|(?:St|Mt|Ft)\.(?=\s)|[A-Z](?:[\w&'-]|\.(?=\w)){0,40})"
# Capitalised sentence openers and headings that are not the first word of a name.
ORG_NOT_FIRST = (r"(?!(?:To|In|For|Of|On|At|By|From|With|And|Or|As|If|Dear|Re|Subject|Introducing|Exclusion|Between|Under|Per|Our|Your|This|That|"
                 r"These|Any|All|Each|No|Not|Please|See|Section|Article|Schedule|Exhibit|Appendix|Whereas|When|Where|While|After|Before|Position)\s)")

def R(id, type, pattern, why, flags="", validator=None):
    return {"id": id, "type": type, "pattern": pattern, "flags": flags, "validator": validator, "why": why}

RULES = [
    R("email", "CONTACT", r"(?<![\w.+-])[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}", "email address pattern"),
    R("url", "CONTACT", r"\bhttps?://[^\s<>\"')]+|\bwww\.[^\s<>\"')]+", "URL pattern", validator="personal_url"),
    R("ipv4", "NETWORK", r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b", "IPv4 address pattern"),
    R("ipv6", "NETWORK", r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:(?:[0-9a-fA-F]{1,4}:?){0,6}[0-9a-fA-F]{0,4}\b", "IPv6 address pattern"),
    R("mac", "NETWORK", r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", "MAC address pattern"),
    R("iban", "FIN_ID", r"\b[A-Za-z]{2}\d{2}(?:(?:[ \-]{1,2}|\n)?[A-Za-z0-9]{1,8}){2,16}", "IBAN with valid mod-97 checksum", validator="iban_prefix"),
    # --- masked / partial identifiers (B3). masked_ssn must precede masked_card: equal-length ties go to the first rule.
    R("masked_ssn", "GOV_ID", r"(?<![\w*#\u2022])[*xX#\u2022]{3}-[*xX#\u2022]{2}-\d{4}\b", "masked social security number (last 4 visible)"),
    R("masked_iban", "FIN_ID", r"\b[A-Z]{2}\d{2}(?:[ \-]?[A-Z0-9*\u2022]{4}){2,7}(?:[ \-]?[A-Z0-9]{1,4})?(?![\w*])", "partially masked IBAN", validator="masked_iban"),
    R("masked_card", "FIN_ID", r"(?<![\w*#\u2022])[*xX#\u2022]{2,19}(?:[ \-][*xX#\u2022]{2,6}){0,4}[ \-]?\d{4}\b", "masked card or account number (last 4 visible)"),
    R("masked_last4", "FIN_ID", r"(?<!year )(?<!period )(?<!quarter )(?<!month )(?<!week )(?<!term )(?:ending(?: in| with)?|ends in|last (?:four|4)(?: digits)?(?: of [a-z ]{1,30}?)?(?: are| is)?)[: ]\s?#?(\d{4})\b(?![.,]\d)",
      "last four digits after 'ending' / 'last four'", flags="i"),
    R("card", "FIN_ID", r"\b(?:\d[ -]?){12,18}\d\b", "card number with valid Luhn checksum", validator="luhn"),
    R("aba", "FIN_ID", r"\b\d{9}\b", "US routing number with valid ABA checksum", validator="aba"),
    R("bic", "FIN_ID", r"\b[A-Z]{4}(?:US|GB|DE|FR|CH|IT|ES|NL|CA|AU|JP|SG|HK|IN|BE|IE|LU|SE|NO|DK|AT|PL|BR|MX|CN)[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", "SWIFT/BIC code pattern"),
    R("fin_keyword", "FIN_ID", r"\b(?:acct|account|a/c|iban|card|routing|aba|customer|member|policy|loan|client)\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{5,})", "identifier after an account/customer keyword", flags="i", validator="has_digit"),
    R("ssn", "GOV_ID", r"\b\d{3}-\d{2}-\d{4}\b", "US social security number pattern"),
    R("gov_keyword", "GOV_ID", r"\b(?:ssn|social security(?: number)?|passport(?: no\.?| number)?|driver'?s? licen[cs]e(?: no\.?| number)?|tax id|tin|ein)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,})", "identifier after an SSN/passport/licence keyword", flags="i", validator="has_digit"),
    R("phone_us", "CONTACT", r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?:\s?(?:x|ext\.?)\s?\d{1,5})?(?!\w)", "phone number pattern"),
    R("phone_intl", "CONTACT", r"(?<![\w+])\+\d{1,3}(?:[ .\-]?\(?\d{1,5}\)?){2,6}(?!\w)", "international phone number pattern", validator="digits_8_15"),
    R("phone_00", "CONTACT", r"(?<![\w.,])00\d{1,3}(?:[ .\-]\d{2,5}){2,5}(?!\w)", "international phone number pattern (00 prefix)", validator="digits_9_15"),
    R("phone_trunk", "CONTACT", r"(?<![\w.,])\(?0\d{1,4}\)?[ \-]\d{3,4}(?:[ \-]?\d{3,6})?(?!\w)(?![.,]\d)", "phone number with trunk prefix (UK/EU/AU style)", validator="digits_9_11"),
    R("date_iso", "DATE", r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b", "ISO date pattern"),
    R("date_numeric", "DATE", r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", "numeric date pattern"),
    R("date_long", "DATE", rf"\b{MONTH}\.? \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}\b|\b\d{{1,2}}(?:st|nd|rd|th)? {MONTH}\.?,? \d{{4}}\b", "written date pattern"),
    R("time", "DATE", r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:[AaPp]\.?[Mm]\.?)?\b", "time of day pattern"),
    R("street", "ADDRESS", rf"\b\d{{1,6}}[A-Za-z]?,?\s+(?:[A-Z][a-z]+\.?\s){{1,4}}(?:{STREET_SUFFIX})\b\.?(?:,?\s(?:Apt|Suite|Ste|Unit|Floor|Fl|#)\.?\s?#?\w+)?{ADDR_TAIL}",
      "street address pattern (with city / state / postcode that follow)"),
    R("coordinates", "ADDRESS", r"(?<![\w.])[-+]?\d{1,3}\.\d{4,}\s?[NSEW]?(?:,\s?|\s)[-+]?\d{1,3}\.\d{4,}(?:\s?[NSEW]\b)?(?![\w.]*\d)", "latitude / longitude pair", validator="coords"),
    R("uk_postcode", "ADDRESS", r"\b[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}\b", "UK postcode pattern"),
    R("zip", "ADDRESS", r"\b\d{5}(?:-\d{4})?\b(?=\s*[,.\n])", "US ZIP code pattern"),
    R("api_key", "SECRET", r"\b(?:sk|pk|rk|ghp|gho|xox[bap]|AKIA)[-_A-Za-z0-9]{12,}\b|\b[A-Za-z0-9_\-]{32,}\b", "API key / long token pattern", validator="mixed_alnum"),
    R("secret_keyword", "SECRET", r"\b(?:password|passwd|pwd|pin|cvv|cvc)\s*[:=]\s*(\S+)", "value after a password/PIN keyword", flags="i"),
    # --- field-aware rules for structured financial messages (B4)
    R("swift_party_account", "FIN_ID", r":(?:50[AFK]|59[AF]?|5[2-8][AD]):/([A-Z0-9]{5,34})\b", "account in a SWIFT party field (:50K:, :59: …)"),
    R("swift_party_name", "NAME", r":(?:50[FK]|59F?):(?:/[^\n]{1,40}\n)?([^\n:/][^\n]{1,34})", "name line of a SWIFT ordering customer / beneficiary field"),
    R("swift_party_address", "ADDRESS", r":(?:50[FK]|59F?):(?:/[^\n]{1,40}\n)?[^\n:/][^\n]{1,34}\n((?:(?!:\d\d[A-Z]?:|-\})[^\n]{1,35}(?:\n(?=[^:\-\n]))?){1,3})", "address lines of a SWIFT party field"),
    R("swift_account_id", "FIN_ID", r":25P?:([A-Z0-9/]{5,35})", "account identification in SWIFT field :25:"),
    R("swift_remit_party", "NAME", r"/(?:ORDP|BENM|BENE|NAME)/([^/\n]{2,35})", "party name in a SWIFT remittance sub-field (/ORDP/, /BENM/)"),
    R("fix_account", "FIN_ID", r"(?<![0-9A-Za-z])1=([^|\x01\n]{3,40})", "FIX tag 1 (Account)"),
    R("fix_party_name", "NAME", r"(?<![0-9])448=([A-Za-z][A-Za-z.'-]{0,30}(?: [A-Za-z.'-]{1,30}){1,4})(?=[|\x01\n])", "FIX tag 448 (PartyID) holding a name"),
    R("fix_party_id", "FIN_ID", r"(?<![0-9])448=([A-Za-z0-9_-]{0,30}\d[A-Za-z0-9_-]{0,30})", "FIX tag 448 (PartyID)"),
    R("kv_identifier", "FIN_ID", r"\b(?:account|acct|iban|routing|card|customer|member|policy|loan|client)[_ ]?(?:number|num|no|id)?[\"']?\s?[:=]\s?[\"']?([A-Za-z0-9][A-Za-z0-9\-]{4,40})", "value of an account / customer key (JSON, CSV, key=value)", flags="i", validator="has_digit"),
    R("iso20022_name", "NAME", r"<(?:Nm|Name)>([^<\n]{2,70})</", "ISO 20022 <Nm> element"),
    R("iso20022_address", "ADDRESS", r"<(?:StrtNm|TwnNm|AdrLine|PstCd|BldgNb)>([^<\n]{1,70})</", "ISO 20022 postal address element"),
    R("title_name", "NAME", r"\b(?:Mr|Ms|Mrs|Dr|Mx)\.?\s([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", "name after a title (Mr, Ms, Dr…)"),
    # --- organisations. Alternation order matters: "Bank of X" must come before the generic "... Bank" suffix rule.
    R("org", "ORG",
      rf"\b(?:The\s)?(?:Bank|Banco|Banque|Caisse) (?:of|de|du|des|di) (?:the )?[A-Z][\w]*(?:\s[A-Z][\w]*){{0,3}}"
      rf"|(?<![\w.&'-]){ORG_NOT_FIRST}(?:The\s)?(?:{ORG_TOKEN}\s(?:(?:of|and|&|for|de)\s)?){{0,5}}(?:{ORG_SUFFIX})\b(?:\s(?:of|de)\s(?:the\s)?[A-Z]\w*(?:\s[A-Z]\w*){{0,2}})?(?:,?\s(?:Inc\.?|Ltd\.?|LLC|N\.A\.|PLC))?"
      rf"|\b[A-Z][A-Z&.' -]{{2,40}}\b(?:BANK|INSURANCE COMPANY|LTD\.?|LLC|INC\.?|CORP\.?|PLC)\b",
      "organisation name pattern (bank / company suffix)", validator="org_shape"),
]
WHY = {r["id"]: r["why"] for r in RULES}
RULES_VERSION = __import__("hashlib").sha256(json.dumps(RULES, sort_keys=True).encode()).hexdigest()[:12]

def _compile(r):
    rx = re.compile(r["pattern"], re.ASCII | (re.IGNORECASE if "i" in r["flags"] else 0))
    assert rx.groups <= 1, r["id"]
    return r["id"], r["type"], rx, VALIDATORS.get(r["validator"]) if r["validator"] else None

COMPILED = [_compile(r) for r in RULES]
REFINERS = frozenset(r["id"] for r in RULES if r["validator"] in ("iban_prefix",))   # validators that return a length

def detect_detailed(text: str):
    """All rule matches as (start, end, type, rule_id), in rule-table order."""
    out = []; n = len(text); src = text + "\n"   # sentinel newline: patterns use \n for end of text (no `$`)
    for rid, t, rx, val in COMPILED:
        g = 1 if rx.groups else 0; pos = 0; refiner = rid in REFINERS
        while pos <= n:
            m = rx.search(src, pos)
            if not m: break
            pos = max(m.end(), m.start() + 1)
            s, e = m.span(g)
            if s < 0: continue
            e = min(e, n)
            if e <= s: continue
            if val:
                ok = val(src[s:e])          # False = reject, True = keep, int = keep only that many characters
                if not ok:
                    if refiner: pos = m.start() + 1    # the pattern over-matches; a real value may start inside it
                    continue
                if ok is not True: e = s + ok; pos = max(e, m.start() + 1)
            out.append((s, e, t, rid))
    return out

def detect(text: str):
    """Non-organisation rules as (start, end, type). Kept for the bench detectors."""
    return [(s, e, t) for s, e, t, rid in detect_detailed(text) if t != "ORG"]

def detect_org(text: str):
    return [(s, e, t) for s, e, t, rid in detect_detailed(text) if t == "ORG"]

# ---------------------------------------------------------------- export for the browser engine
SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "apps", "web", "lib", "rules.generated.json")

def spec() -> dict:
    from . import lexicon as lex
    from .coarse import GROUPS
    from .types import GLINER_LABELS, DIRECT_TYPES
    return {"_comment": "GENERATED by `python -m redactd.rules --export` from redactd/{rules,lexicon,coarse,types}.py. Do not edit.",
            "version": RULES_VERSION, "rules": RULES, "refiners": sorted(REFINERS), "schema_url_pattern": _SCHEMA_URL.pattern, "iban_countries": sorted(IBAN_COUNTRIES),
            "lexicon": {"org_allowlist": lex.ORG_ALLOWLIST, "public_body_pattern": lex.PUBLIC_BODY_PATTERN,
                        "nonpersonal_date_pattern": lex.NONPERSONAL_DATE_PATTERN, "name_part_stop": lex.NAME_PART_STOP,
                        "common_word_names": lex.COMMON_WORD_NAMES, "thresholds": lex.THRESHOLDS, "solo_thresholds": lex.SOLO_THRESHOLDS,
                        "masked_rule_ids": lex.MASKED_RULE_IDS, "glue_pattern": lex.GLUE_PATTERN,
                        "generic_terms": lex.GENERIC_TERMS},
            "groups": GROUPS, "gliner_labels": GLINER_LABELS, "direct_types": sorted(DIRECT_TYPES)}

def spec_text() -> str:
    return json.dumps(spec(), indent=1, ensure_ascii=True) + "\n"

if __name__ == "__main__":
    if "--export" in sys.argv:
        with open(SPEC_PATH, "w") as f: f.write(spec_text())
        print("wrote", os.path.normpath(SPEC_PATH))
    elif "--check" in sys.argv:
        if open(SPEC_PATH).read() != spec_text():
            raise SystemExit("apps/web/lib/rules.generated.json is stale: run `python -m redactd.rules --export`")
        print("rules.generated.json is up to date")
