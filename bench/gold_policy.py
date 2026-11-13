"""Documented exclusion policy for gold spans that are not personal data (reported alongside raw scores).
Excluded: (1) template placeholders ([X], ___), (2) all-lowercase generic phrases ('sales department'),
(3) roles/defined terms in contracts, (4) public bodies, regulators, standards and trade associations."""
import re
PUBLIC = re.compile(r"^(?:The\s)?(?:ISDA|UTRRF|HMRC|Her Majesty's Revenue and Customs|International Chamber of Commerce|"
                    r"(?:UNITED STATES|U\.S\.) DEPARTMENT OF THE TREASURY|Environmental Protection Agency.*|National Highway Traffic Safety Administration.*|"
                    r"Society of Automotive Engineers.*|U\.S\. Energy Information Administration|Data Privacy Framework|Regulatory Authorities|"
                    r"British Museum|Credit Support Provider|Complainant|Respondent|Dispute Resolution Committee.*|"
                    r"Community Engagement Initiatives|US-based [Tt]ech [Cc]ompanies|Telecommunications companies|Nonprofit Organization)$")
ORG_LABELS = {"company", "company_name"}
def excluded(text, label):
    t = text.strip()
    if re.search(r"^\[.*\]$|_{3,}", t):          # template placeholder, any label
        return True
    if label in ORG_LABELS:                         # only organisation labels get the generic/public-body exclusions
        return bool(re.fullmatch(r"[a-z][a-z \-]+", t)) or bool(PUBLIC.match(t))
    return False
