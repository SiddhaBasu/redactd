"""Shared type maps (mirrors apps/web/lib/labels.ts and bench/coarse.py)."""
from .coarse import COARSE as FINE_TO_COARSE, TYPES  # noqa: F401

DIRECT_TYPES = {"NAME", "CONTACT", "ADDRESS", "GOV_ID", "FIN_ID", "SECRET", "NETWORK"}
GLINER_LABELS = {
    "person name": "NAME", "username": "NAME",
    "email address": "CONTACT", "phone number": "CONTACT", "url": "CONTACT",
    "street address": "ADDRESS", "city": "ADDRESS", "state": "ADDRESS", "country": "ADDRESS", "postal code": "ADDRESS",
    "social security number": "GOV_ID", "passport number": "GOV_ID", "driver license number": "GOV_ID", "tax id": "GOV_ID",
    "bank account number": "FIN_ID", "credit card number": "FIN_ID", "routing number": "FIN_ID", "iban": "FIN_ID",
    "swift code": "FIN_ID", "customer id": "FIN_ID", "employee id": "FIN_ID",
    "password": "SECRET", "api key": "SECRET", "ip address": "NETWORK",
    "date": "DATE", "date of birth": "DATE",
    "company name": "ORG", "bank": "ORG", "insurance company": "ORG",
    "occupation": "DEMOGRAPHIC", "age": "DEMOGRAPHIC", "gender": "DEMOGRAPHIC", "race or ethnicity": "DEMOGRAPHIC",
    "employment status": "DEMOGRAPHIC",
}
