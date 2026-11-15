"""Document-type ("domain") bundles. A domain only ever ADDS detection on top of the general detectors: choosing the
wrong domain must never hide an identifier the general pipeline would have found.

  gliner: extra zero-shot GLiNER labels -> coarse type. In Thorough they are added to GLiNER's label list; in Standard
          (which normally runs no GLiNER) GLiNER runs with ONLY these labels.

Domain-specific pattern rules (NPI, DEA, NHS numbers, MRN keywords, blood type ...) are always on in redactd/rules.py,
because they are precise; only the model labels are gated by the chosen domain. Mirrored to the browser through
apps/web/lib/rules.generated.json.
"""
DOMAINS: dict = {
    "general": {"name": "General", "description": "Any document.", "gliner": {}},
    "medical": {
        "name": "Medical",
        "description": "Clinical notes, lab reports, prescriptions, insurance claims: also finds conditions, medications and health IDs.",
        "gliner": {
            "medical record number": "GOV_ID", "health insurance id": "GOV_ID", "medical license number": "GOV_ID",
            "medical condition": "HEALTH", "medication": "HEALTH",
            # no "blood type": the blood_type rule covers it, and GLiNER's blood-type label fired on lab values
            # ("180", "14.0 g/dL") on the medical dev set without finding anything the rule missed
        },
    },
}
DEFAULT_DOMAIN = "general"

def extra_labels(domain: str | None) -> dict:
    return dict(DOMAINS.get(domain or DEFAULT_DOMAIN, DOMAINS[DEFAULT_DOMAIN])["gliner"])
