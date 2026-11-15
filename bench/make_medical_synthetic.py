"""Synthetic medical documents with labels by construction (templates + seeded values; no LLM).

    python bench/make_medical_synthetic.py  -> data/eval/eval_medical_synthetic.jsonl

Covers what Nemotron's health documents do not label: conditions, medications, and US/UK identifier formats
(NPI, DEA, NHS number, Medicare MBI) plus MRNs, member IDs and blood types written in words. The Medical domain's
rules and labels were written with these cases in mind, so this is a REGRESSION suite, not a held-out set.
"""
import json, os, random, sys
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.dirname(__file__))
from taxonomy import tier
sys.path.insert(0, ROOT)
from redactd.rules import luhn

FIRST = ["Maria", "Kwabena", "Ingrid", "Tomás", "Aisha", "Henrik", "Mei", "Oluwaseun", "Priscilla", "Dmitri", "Fatima", "Graham"]
LAST = ["Delgado", "Mensah", "Halvorsen", "Ibáñez", "Rahman", "Lindgren", "Zhou", "Adeyemi", "Whitcombe", "Sokolov", "Haddad", "Pryce"]
DOCS = [("Amit", "Shah"), ("Rebecca", "Thornton"), ("Luis", "Ortega"), ("Hannah", "Kowalski"), ("Samuel", "Achebe")]
CONDITIONS = ["type 2 diabetes", "hypertension", "chronic obstructive pulmonary disease", "atrial fibrillation", "major depressive disorder",
              "rheumatoid arthritis", "asthma", "chronic kidney disease stage 3", "hypothyroidism", "migraine with aura", "HIV", "epilepsy"]
MEDS = ["metformin 500 mg", "lisinopril 10 mg", "atorvastatin 40 mg", "apixaban 5 mg", "sertraline 50 mg", "methotrexate 15 mg",
        "salbutamol inhaler", "levothyroxine 75 mcg", "sumatriptan 50 mg", "levetiracetam 500 mg", "tenofovir/emtricitabine", "insulin glargine"]
CLINICS = ["Riverside Family Clinic", "St. Brigid's Hospital", "Northfield Health Centre", "Lakeshore Medical Group", "Cedar Valley Hospital"]
BLOOD = ["O positive", "A negative", "AB+", "B-", "O neg", "A pos"]

class Doc:
    def __init__(self): self.parts, self.spans, self.n = [], [], 0
    def t(self, s): self.parts.append(s); self.n += len(s); return self
    def e(self, s, label):
        self.spans.append({"start": self.n, "end": self.n + len(s), "label": label, "tier": tier(label)}); return self.t(s)
    @property
    def text(self): return "".join(self.parts)

class G:
    def __init__(self): self.r = random.Random(4242)
    def pick(self, xs): return self.r.choice(xs)
    def digits(self, n): return "".join(self.r.choice("0123456789") for _ in range(n))
    def npi(self):
        while True:
            d = str(self.r.randint(1, 2)) + self.digits(8)
            for c in "0123456789":
                if luhn("80840" + d + c): return d + c
    def dea(self, last):
        L = self.r.choice("ABFGM") + last[0].upper(); d = [int(c) for c in self.digits(6)]
        return L + "".join(map(str, d)) + str((d[0] + d[2] + d[4] + 2 * (d[1] + d[3] + d[5])) % 10)
    def nhs(self):
        while True:
            d = [int(c) for c in self.digits(9)]; c = 11 - sum(x * w for x, w in zip(d, range(10, 1, -1))) % 11
            if c == 10: continue
            s = "".join(map(str, d)) + str(0 if c == 11 else c); return f"{s[:3]} {s[3:6]} {s[6:]}"
    def mbi(self): return f"{self.r.randint(1, 9)}{self.pick('ACDEFGHJKM')}{self.pick('ACDEFGHJKM')}{self.r.randint(0, 9)}-{self.pick('ACDEFGHJKM')}{self.pick('ACDEFGHJKM')}{self.r.randint(0, 9)}-{self.pick('ACDEFGHJKM')}{self.pick('ACDEFGHJKM')}{self.r.randint(10, 99)}"
    def dob(self): return f"{self.r.randint(1, 12):02d}/{self.r.randint(1, 28):02d}/{self.r.randint(1938, 2004)}"

def discharge(g):
    d = Doc(); f, l = g.pick(FIRST), g.pick(LAST); df, dl = g.pick(DOCS)
    d.t("DISCHARGE SUMMARY\nPatient: ").e(f"{f} {l}", "name").t("   MRN: ").e(g.digits(8), "medical_record_number").t("   DOB: ").e(g.dob(), "date_of_birth")
    d.t("\nAdmitted with an exacerbation of ").e(g.pick(CONDITIONS), "medical_condition").t("; history of ").e(g.pick(CONDITIONS), "medical_condition")
    d.t(".\nDischarge medications: ").e(g.pick(MEDS), "medication").t(" daily and ").e(g.pick(MEDS), "medication").t(" as needed.\nAttending: Dr. ").e(f"{df} {dl}", "name")
    d.t(", NPI ").e(g.npi(), "certificate_license_number").t(", ").e(g.pick(CLINICS), "company_name").t(".\n")
    return d
def prescription(g):
    d = Doc(); f, l = g.pick(FIRST), g.pick(LAST); df, dl = g.pick(DOCS)
    d.t("Rx for ").e(f"{f} {l}", "name").t(" (DOB ").e(g.dob(), "date_of_birth").t(")\n").e(g.pick(MEDS), "medication").t(", 30 tablets, 2 refills, for ").e(g.pick(CONDITIONS), "medical_condition")
    d.t(".\nPrescriber: ").e(f"{df} {dl}", "name").t(", MD  DEA ").e(g.dea(dl), "certificate_license_number").t("  NPI: ").e(g.npi(), "certificate_license_number").t("\n")
    return d
def nhs_letter(g):
    d = Doc(); f, l = g.pick(FIRST), g.pick(LAST)
    d.t("Dear Dr ").e(g.pick(DOCS)[1], "last_name").t(",\nRe: ").e(f"{f} {l}", "name").t(", NHS number ").e(g.nhs(), "national_id").t("\nThank you for referring this patient with suspected ")
    d.e(g.pick(CONDITIONS), "medical_condition").t(". Blood group ").e(g.pick(BLOOD), "blood_type").t(". Please continue ").e(g.pick(MEDS), "medication").t(".\n")
    return d
def insurance(g):
    d = Doc(); f, l = g.pick(FIRST), g.pick(LAST)
    d.t("Claim for ").e(f"{f} {l}", "name").t("\nMember ID: ").e("W" + g.digits(9), "health_plan_beneficiary_number").t("   Group #: ").e(g.digits(6), "health_plan_beneficiary_number")
    d.t("\nMedicare number ").e(g.mbi(), "health_plan_beneficiary_number").t("\nDiagnosis: ").e(g.pick(CONDITIONS), "medical_condition").t("; treated at ").e(g.pick(CLINICS), "company_name").t(".\n")
    return d
def nurse_note(g):
    d = Doc(); f = g.pick(FIRST)
    d.t("08:40 pt ").e(f.lower(), "first_name").t(" c/o chest tightness, known ").e(g.pick(CONDITIONS), "medical_condition").t(", gave ").e(g.pick(MEDS), "medication")
    d.t(" per protocol. chart no. ").e("C-" + g.digits(6), "medical_record_number").t(". blood type ").e(g.pick(BLOOD), "blood_type").t(". family aware.\n")
    return d
def lab(g):
    d = Doc(); f, l = g.pick(FIRST), g.pick(LAST)
    d.t('{"patient": {"name": "').e(f"{f} {l}", "name").t('", "mrn": "').e(g.digits(7), "medical_record_number").t('", "dob": "').e(g.dob(), "date_of_birth")
    d.t('"}, "panel": "HbA1c", "result": "8.1 %", "indication": "').e(g.pick(CONDITIONS), "medical_condition").t('", "current_meds": ["').e(g.pick(MEDS), "medication").t('"]}')
    return d
TEMPLATES = [discharge, prescription, nhs_letter, insurance, nurse_note, lab]

if __name__ == "__main__":
    g, rows = G(), []
    for fn in TEMPLATES:
        for k in range(10):
            d = fn(g)
            for s in d.spans: assert d.text[s["start"]:s["end"]] and s["tier"], (fn.__name__, s)
            rows.append({"id": f"medsyn-{fn.__name__}-{k}", "source": "synthetic_medical", "domain": "medical", "fmt": "synthetic",
                         "doc_type": fn.__name__, "text": d.text, "spans": d.spans})
    with open(f"{ROOT}/data/eval/eval_medical_synthetic.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "docs", sum(len(r["spans"]) for r in rows), "spans")
