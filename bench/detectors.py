"""Uniform detector wrappers: each returns list of (start, end, coarse_type)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(__file__), "..")
from coarse import COARSE
import regex_rules

def regex():
    return regex_rules.detect

def presidio():
    from presidio_analyzer import AnalyzerEngine
    eng = AnalyzerEngine()  # spaCy en_core_web_lg + built-in recognizers
    M = {"PERSON": "NAME", "EMAIL_ADDRESS": "CONTACT", "PHONE_NUMBER": "CONTACT", "URL": "CONTACT",
         "LOCATION": "ADDRESS", "DATE_TIME": "DATE", "NRP": "DEMOGRAPHIC", "CREDIT_CARD": "FIN_ID",
         "IBAN_CODE": "FIN_ID", "US_BANK_NUMBER": "FIN_ID", "US_SSN": "GOV_ID", "US_PASSPORT": "GOV_ID",
         "US_DRIVER_LICENSE": "GOV_ID", "US_ITIN": "GOV_ID", "IP_ADDRESS": "NETWORK", "CRYPTO": "FIN_ID",
         "MEDICAL_LICENSE": "GOV_ID", "ORGANIZATION": "ORG"}
    def f(text):
        return [(r.start, r.end, M.get(r.entity_type, "OTHER")) for r in eng.analyze(text=text, language="en", score_threshold=0.0)]
    return f

GLINER_LABELS = {
    "person name": "NAME", "first name": "NAME", "last name": "NAME", "username": "NAME",
    "email address": "CONTACT", "phone number": "CONTACT", "fax number": "CONTACT", "url": "CONTACT",
    "street address": "ADDRESS", "city": "ADDRESS", "state": "ADDRESS", "country": "ADDRESS", "postal code": "ADDRESS",
    "social security number": "GOV_ID", "passport number": "GOV_ID", "driver license number": "GOV_ID", "tax id": "GOV_ID",
    "medical record number": "GOV_ID", "license plate": "GOV_ID",
    "bank account number": "FIN_ID", "credit card number": "FIN_ID", "cvv": "FIN_ID", "routing number": "FIN_ID",
    "iban": "FIN_ID", "swift code": "FIN_ID", "customer id": "FIN_ID", "employee id": "FIN_ID", "pin": "FIN_ID",
    "password": "SECRET", "api key": "SECRET", "ip address": "NETWORK", "mac address": "NETWORK", "device id": "NETWORK",
    "date": "DATE", "date of birth": "DATE", "time": "DATE",
    "company name": "ORG", "occupation": "DEMOGRAPHIC", "age": "DEMOGRAPHIC", "gender": "DEMOGRAPHIC",
    "race or ethnicity": "DEMOGRAPHIC", "religion": "DEMOGRAPHIC", "political affiliation": "DEMOGRAPHIC",
    "employment status": "DEMOGRAPHIC", "education level": "DEMOGRAPHIC", "sexual orientation": "DEMOGRAPHIC",
    "blood type": "DEMOGRAPHIC", "language": "DEMOGRAPHIC",
}

def gliner(name="knowledgator/gliner-pii-base-v1.0", threshold=0.3):
    from gliner import GLiNER
    m = GLiNER.from_pretrained(name)
    labels = list(GLINER_LABELS)
    def f(text):
        out = []
        # chunk on ~1500 chars at whitespace (GLiNER has a ~384-word window)
        for off, chunk in chunks(text, 1500):
            for e in m.predict_entities(chunk, labels, threshold=threshold):
                out.append((off + e["start"], off + e["end"], GLINER_LABELS[e["label"]]))
        return out
    return f

def chunks(text, n):
    i = 0
    while i < len(text):
        j = min(len(text), i + n)
        if j < len(text):
            k = text.rfind(" ", i + n // 2, j)
            j = k if k > 0 else j
        yield i, text[i:j]
        i = j

def hf_tokclass(path):
    from transformers import pipeline
    p = pipeline("token-classification", model=path, aggregation_strategy="simple", device=-1)
    def f(text):
        out = []
        for off, chunk in chunks(text, 1500):
            for e in p(chunk):
                g = e["entity_group"]
                out.append((off + e["start"], off + e["end"], COARSE.get(g, g)))
        return out
    return f

def openmed(size="Base-184M"):
    return hf_tokclass(f"OpenMed/OpenMed-PII-SuperClinical-{size}-v1")

def deberta_ours():
    return hf_tokclass(f"{ROOT}/models/deberta-v3-small-pii-fin")

def union(*fs):
    def f(text):
        return [p for g in fs for p in g(text)]
    return f


def org_rules():
    return regex_rules.detect_org

GLINER_ORG = ["bank", "financial institution", "insurance company", "company", "organization", "investment fund", "brokerage firm"]
def gliner_org(name="knowledgator/gliner-pii-base-v1.0", threshold=0.2):
    from gliner import GLiNER
    m = GLiNER.from_pretrained(name)
    def f(text):
        return [(off + e["start"], off + e["end"], "ORG") for off, ch in chunks(text, 1500)
                for e in m.predict_entities(ch, GLINER_ORG, threshold=threshold)]
    return f

_GLUE = re.compile(r"(?<=\d)(?=[A-Za-z])|(?<=[a-z])(?=\d)")
def split_glued(f):
    """Insert spaces where digits touch letters (SWIFT/FIX fields), run detector, map offsets back."""
    def g(text):
        cuts = [m.start() for m in _GLUE.finditer(text)]
        if not cuts: return f(text)
        new, mp, last = [], [], 0
        for c in cuts:
            new.append(text[last:c]); mp += range(last, c); new.append(" "); mp.append(c); last = c
        new.append(text[last:]); mp += range(last, len(text)); mp.append(len(text))
        return [(mp[s], mp[e - 1] + 1 if e > 0 else 0, t) for s, e, t in f("".join(new)) if e > s]
    return g
