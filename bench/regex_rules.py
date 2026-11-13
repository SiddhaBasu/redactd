"""Pattern rules with validators (the 'rules alone' baseline). Pure-Python, no ML."""
import re

def luhn(d):
    d = [int(c) for c in d if c.isdigit()]
    if not 13 <= len(d) <= 19: return False
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2: x = x * 2 - 9 if x > 4 else x * 2
        s += x
    return s % 10 == 0

def aba(d):
    d = [int(c) for c in d]
    return len(d) == 9 and (3*(d[0]+d[3]+d[6]) + 7*(d[1]+d[4]+d[7]) + (d[2]+d[5]+d[8])) % 10 == 0

def iban_ok(s):
    s = s.replace(" ", "").upper()
    if not 15 <= len(s) <= 34: return False
    r = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1

MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
RULES = [
    ("CONTACT", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", None),
    ("CONTACT", r"\bhttps?://[^\s<>\"')]+|\bwww\.[^\s<>\"')]+", None),
    ("NETWORK", r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b", None),
    ("NETWORK", r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:(?:[0-9a-fA-F]{1,4}:?){0,6}[0-9a-fA-F]{0,4}\b", None),
    ("NETWORK", r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", None),
    ("FIN_ID", r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b", iban_ok),
    ("FIN_ID", r"\b(?:\d[ -]?){12,18}\d\b", luhn),
    ("FIN_ID", r"\b\d{9}\b", aba),
    ("FIN_ID", r"\b[A-Z]{4}(?:US|GB|DE|FR|CH|IT|ES|NL|CA|AU|JP|SG|HK|IN|BE|IE|LU|SE|NO|DK|AT|PL|BR|MX|CN)[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", None),  # SWIFT/BIC
    ("FIN_ID", r"(?i)(?:acct|account|a/c|iban|card|routing|aba|customer|member|policy|loan|client)\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{5,})", lambda v: any(c.isdigit() for c in v)),
    ("GOV_ID", r"\b\d{3}-\d{2}-\d{4}\b", None),
    ("GOV_ID", r"(?i)(?:ssn|social security(?: number)?|passport(?: no\.?| number)?|driver'?s? licen[cs]e(?: no\.?| number)?|tax id|tin|ein)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,})", lambda v: any(c.isdigit() for c in v)),
    ("CONTACT", r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?:\s?(?:x|ext\.?)\s?\d{1,5})?(?!\w)", None),
    ("CONTACT", r"(?<!\w)\+\d{1,3}(?:[ .-]?\d{2,4}){2,5}(?!\w)", None),
    ("DATE", r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b", None),
    ("DATE", r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b", None),
    ("DATE", rf"\b{MONTH}\.? \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}\b|\b\d{{1,2}}(?:st|nd|rd|th)? {MONTH}\.?,? \d{{4}}\b", None),
    ("DATE", r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:[AaPp]\.?[Mm]\.?)?\b", None),
    ("ADDRESS", r"\b\d{1,6}\s+(?:[A-Z][a-z]+\.?\s){1,4}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Way|Pl|Place|Ter|Terrace|Pkwy|Parkway|Cir|Circle|Hwy|Highway|Sq|Square)\b\.?(?:,?\s(?:Apt|Suite|Unit|#)\s?\w+)?", None),
    ("ADDRESS", r"\b\d{5}(?:-\d{4})?\b(?=\s*(?:$|[,.\n]))", None),
    ("SECRET", r"\b(?:sk|pk|rk|ghp|gho|xox[bap]|AKIA)[-_A-Za-z0-9]{12,}\b|\b[A-Za-z0-9_\-]{32,}\b", None),
    ("SECRET", r"(?i)(?:password|passwd|pwd|pin|cvv|cvc)\s*[:=]\s*(\S+)", None),
    ("NAME", r"\b(?:Mr|Ms|Mrs|Dr|Mx)\.?\s([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", None),
]
COMPILED = [(t, re.compile(p), v) for t, p, v in RULES]

def detect(text):
    out = []
    for t, rx, val in COMPILED:
        for m in rx.finditer(text):
            g = 1 if rx.groups else 0
            s, e = m.span(g)
            if s < 0 or (val and not val(m.group(g))): continue
            out.append((s, e, t))
    return out

# --- Organisation rules (financial institutions, companies) ---
ORG_SUFFIX = (r"Bank|Bancorp|Banking|Credit Union|Savings|Trust|Insurance(?: Company)?|Assurance|Capital|Partners|"
              r"Holdings?|Group|Fund|Funds|Investments?|Securities|Financial|Finance|Asset Management|Advisors|"
              r"Inc\.?|Incorporated|LLC|L\.L\.C\.|Ltd\.?|Limited|PLC|plc|Corp\.?|Corporation|Co\.|Company|GmbH|AG|S\.A\.|N\.V\.|LLP|LP|"
              r"Institute|University|College|Hospital|Clinic|Physical Therapy|Healthcare")
ORG_RX = re.compile(
    rf"\b(?:The\s)?(?:Bank|Banco|Banque|Caisse) (?:of|de|du|des|di) (?:the )?[A-Z][\w]*(?:\s[A-Z][\w]*){{0,3}}"
    rf"|\b(?:The\s)?(?:[A-Z][\w&'.-]*\s(?:(?:of|the|and|&|for|de)\s)*){{0,5}}(?:{ORG_SUFFIX})\b(?:\s(?:of|de)\s(?:the\s)?[A-Z]\w*(?:\s[A-Z]\w*){{0,2}})?(?:,?\s(?:Inc\.?|Ltd\.?|LLC|N\.A\.|PLC))?"
    rf"|\b[A-Z][A-Z&.' -]{{2,40}}\b(?:BANK|INSURANCE COMPANY|LTD\.?|LLC|INC\.?|CORP\.?|PLC)\b")

def detect_org(text):
    return [(m.start(), m.end(), "ORG") for m in ORG_RX.finditer(text) if len(m.group().split()) >= 2 or m.group().isupper()]
