"""Documented exclusion policy for gold spans that are not personal data. Scores are always reported on raw labels
AND on policy-adjusted labels, side by side.

A gold span is excluded when it is:
  1. a template placeholder ("[Recipient Name]", "______")                                   — any label
  2. a generic term: pronoun, contract role or field label ("Borrower", "Company", "Occupation") — any label
  3. for organisation labels only: an all-lower-case generic phrase ("sales department"), or a public body,
     regulator, exchange, standards body or card network (ISDA, HMRC, SEC, Visa …)
  4. for date/time labels only: a reporting period rather than a personal date ("Q3 2025", "FY2024")

Items 2-4 reuse the word lists the product itself ships (redactd/lexicon.py), because they encode the same product
decision: those strings are deliberately NOT redacted. That makes the policy-adjusted number a measure of "did we
redact what we mean to redact". It cannot show whether the decision itself is right, which is why the raw-label
number is always printed next to it. LEGACY_PUBLIC is the previous maintainer's list, kept unchanged.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd.post import is_public_body, is_nonpersonal_date, norm_term
from redactd import lexicon as lex

LEGACY_PUBLIC = re.compile(r"^(?:The\s)?(?:ISDA|UTRRF|HMRC|Her Majesty's Revenue and Customs|International Chamber of Commerce|"
                    r"(?:UNITED STATES|U\.S\.) DEPARTMENT OF THE TREASURY|Environmental Protection Agency.*|National Highway Traffic Safety Administration.*|"
                    r"Society of Automotive Engineers.*|U\.S\. Energy Information Administration|Data Privacy Framework|Regulatory Authorities|"
                    r"British Museum|Credit Support Provider|Complainant|Respondent|Dispute Resolution Committee.*|"
                    r"Community Engagement Initiatives|US-based [Tt]ech [Cc]ompanies|Telecommunications companies|Nonprofit Organization)$")
ORG_LABELS = {"company", "company_name"}
DATE_LABELS = {"date", "time", "date_time"}
_GENERIC = frozenset(lex.GENERIC_TERMS)
_ABBREV = re.compile(r"\s*\([A-Z&. ]{2,10}\)$")     # "Federal Trade Commission (FTC)" -> "Federal Trade Commission"

def excluded(text, label):
    t = text.strip()
    if re.search(r"^\[.*\]$|_{3,}", t):          # template placeholder, any label
        return True
    if norm_term(t) in _GENERIC:
        return True
    if label in ORG_LABELS:                         # only organisation labels get the generic/public-body exclusions
        return bool(re.fullmatch(r"[a-z][a-z \-]+", t)) or bool(LEGACY_PUBLIC.match(t)) or is_public_body(t) or is_public_body(_ABBREV.sub("", t))
    if label in DATE_LABELS:
        return is_nonpersonal_date(t)
    return False
