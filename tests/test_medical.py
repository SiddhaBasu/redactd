"""Medical identifier rules and the domain plumbing (models not needed)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd import rules
from redactd.domains import DOMAINS, extra_labels
from redactd.coarse import TYPES

def found(text):
    return {(text[s:e], t, rid) for s, e, t, rid in rules.detect_detailed(text)}

def test_checksums():
    assert rules.npi_ok("1234567893") and not rules.npi_ok("1234567894")
    assert rules.dea_ok("AS1234563") and not rules.dea_ok("AS1234564")
    assert rules.nhs_ok("943 476 5919") and not rules.nhs_ok("943 476 5918")

def test_rules_find_health_identifiers_and_skip_bad_checksums():
    t = ("MRN: 00123456. Member ID: XKD448812901. NPI 1234567893 (bad NPI 1234567894). DEA AS1234563. "
         "NHS number 943 476 5919 (bad NHS number 943 476 5918). Blood type: O positive; blood group AB-.")
    f = found(t)
    for v, ty in [("00123456", "GOV_ID"), ("XKD448812901", "GOV_ID"), ("1234567893", "GOV_ID"), ("AS1234563", "GOV_ID"),
                  ("943 476 5919", "GOV_ID"), ("O positive", "HEALTH"), ("AB-", "HEALTH")]:
        assert any(x[0] == v and x[1] == ty for x in f), (v, ty)
    assert not any(x[0] in ("1234567894", "943 476 5918") and x[2] in ("npi", "nhs") for x in f)

def test_domains_only_add_labels():
    assert extra_labels("general") == {} and extra_labels(None) == {} and extra_labels("nope") == {}
    med = extra_labels("medical")
    assert med and set(med.values()) <= set(TYPES) and "HEALTH" in med.values()
    assert all(d["name"] and d["description"] for d in DOMAINS.values())
