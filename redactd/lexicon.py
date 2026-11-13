"""Word lists and calibrated numbers used by redactd/post.py. Exported to the browser with the rule spec.

Everything here was written from general knowledge or tuned on DEV sets only (eval_gretel_fin, eval_nemotron_fin,
dev_nemotron_fin_structured). Never add an entry because of something seen in a held-out document.
"""

# Public institutions, regulators, exchanges, payment networks and standards bodies. Applied ONLY to ORG spans
# (normalised: lower-case, leading "the " and trailing punctuation removed). Naming one of these does not identify
# a customer; commercial banks, insurers and companies are NOT on this list and are still redacted.
ORG_ALLOWLIST = sorted({
    # US regulators and government
    "sec", "securities and exchange commission", "u.s. securities and exchange commission", "us securities and exchange commission",
    "finra", "financial industry regulatory authority", "cftc", "commodity futures trading commission", "occ",
    "office of the comptroller of the currency", "fdic", "federal deposit insurance corporation", "cfpb",
    "consumer financial protection bureau", "fincen", "financial crimes enforcement network", "ofac",
    "office of foreign assets control", "federal reserve", "federal reserve board", "federal reserve system", "federal reserve bank",
    "fed", "irs", "internal revenue service", "ftc", "federal trade commission", "doj", "department of justice", "dol",
    "department of labor", "hud", "treasury", "u.s. treasury", "us treasury", "department of the treasury",
    "u.s. department of the treasury", "united states department of the treasury", "social security administration", "ssa",
    "medicare", "medicaid", "epa", "environmental protection agency", "fda", "osha", "nist", "dmv", "congress", "senate", "supreme court",
    "ncua", "national credit union administration", "sipc", "pcaob", "fhfa", "fannie mae", "freddie mac", "ginnie mae",
    # UK / EU / international regulators and bodies
    "fca", "financial conduct authority", "pra", "prudential regulation authority", "hmrc", "hm revenue and customs",
    "hm revenue & customs", "her majesty's revenue and customs", "his majesty's revenue and customs", "hm treasury",
    "companies house", "bank of england", "ico", "information commissioner's office", "financial ombudsman service", "fscs",
    "nhs", "dvla", "parliament", "ecb", "european central bank", "eba", "european banking authority", "esma", "eiopa",
    "european commission", "european union", "eu", "bafin", "finma", "mas", "monetary authority of singapore", "asic", "apra",
    "rbi", "reserve bank of india", "sebi", "hkma", "bis", "bank for international settlements", "imf",
    "international monetary fund", "world bank", "oecd", "fatf", "financial action task force", "iosco", "fsb",
    "financial stability board", "basel committee", "basel committee on banking supervision", "united nations", "un", "wto", "who",
    "international chamber of commerce", "icc",
    # trade associations and standards bodies
    "isda", "international swaps and derivatives association", "icma", "lma", "loan market association", "sifma", "lsta",
    "american bankers association", "nacha", "swift", "s.w.i.f.t.", "iso", "international organization for standardization",
    "iasb", "fasb", "ifrs foundation", "aicpa", "ansi", "ieee", "w3c", "pci security standards council", "emvco",
    "xbrl international", "fix trading community", "un/cefact", "gs1",
    # exchanges, clearing and payment systems
    "nyse", "new york stock exchange", "nasdaq", "lse", "london stock exchange", "cme", "cme group", "chicago mercantile exchange",
    "cboe", "ice", "intercontinental exchange", "euronext", "tokyo stock exchange", "hong kong stock exchange", "hkex", "sgx",
    "asx", "tsx", "lme", "dtcc", "dtc", "euroclear", "clearstream", "lch", "chaps", "bacs", "fedwire", "chips", "sepa", "target2",
    "ach", "faster payments",
    # card networks
    "visa", "mastercard", "american express", "amex", "discover", "unionpay", "jcb", "diners club",
})

# Generic public-body shapes, matched against the normalised span (full match, case-insensitive).
PUBLIC_BODY_PATTERN = (
    r"(?:(?:u\.?s\.?|united states|uk|federal|national|state|european|international|royal) )?"
    r"(?:department|ministry|bureau|office|commission|agency|administration|authority|court|council|parliament|government|treasury)"
    r"(?: (?:of|for|on) [a-z0-9 ,.&'-]{2,60})?"
    r"|[a-z .&'-]{2,40} (?:stock exchange|securities and exchange commission|revenue service|tax authority|monetary authority|"
    r"supervisory authority|regulatory authority|regulatory authorities)")

# DATE spans that are reporting periods, not personal dates (full match, case-insensitive).
NONPERSONAL_DATE_PATTERN = (
    r"(?:fy|fiscal year|financial year|tax year|calendar year|plan year|policy year)[ -]?'?\d{2,4}(?:[/-]\d{2,4})?"
    r"|(?:q[1-4]|h[12]|[1-4]q|[12]h)[ -]?(?:fy[ -]?)?'?\d{2,4}"
    r"|(?:first|second|third|fourth) quarter(?: of)?(?: (?:fy[ -]?)?\d{4})?"
    r"|(?:q[1-4]|h[12])"
    r"|(?:annual(?:ly)?|quarterly|monthly|weekly|daily|year[- ]end|month[- ]end|quarter[- ]end|ytd|year[- ]to[- ]date)")

# Tokens never propagated as "part of a name" even when a model returns them inside a NAME span.
NAME_PART_STOP = sorted({
    "the", "and", "of", "for", "mr", "mrs", "ms", "dr", "mx", "miss", "sir", "madam", "prof", "jr", "sr", "ii", "iii", "iv",
    "van", "von", "de", "la", "le", "del", "der", "den", "bin", "ibn", "al", "el", "st", "dear", "hi", "hello", "from", "to", "cc",
    "re", "attn", "account", "customer", "client", "bank", "name", "inc", "ltd", "llc", "plc", "corp", "co", "company", "group",
    "team", "department", "manager", "officer", "director", "agent", "user", "holder", "beneficiary", "applicant", "borrower",
    "lender", "insured", "policyholder", "sender", "recipient", "signature", "signed", "regards", "sincerely", "thanks",
    "n/a", "none", "unknown", "not", "with", "this", "that", "your", "our",
})

# Names that are also everyday words. Their capitalised form is still propagated (recall first), but they are not
# propagated in ALL CAPS ("BILL TO:") or matched inside login handles.
COMMON_WORD_NAMES = sorted({
    "bill", "hope", "rose", "mark", "will", "art", "faith", "joy", "may", "april", "june", "august", "penny", "rich", "frank",
    "chase", "summer", "dawn", "violet", "jack", "bob", "pat", "sandy", "rusty", "christian", "chance", "ivy", "olive", "paris",
    "jordan", "chad", "georgia", "austin", "sterling", "cash", "lane", "banks", "price", "bond", "grace", "miles", "major",
    "victor", "earnest", "daisy", "stone", "rivers", "woods", "field", "cross", "hill", "sharp", "marsh", "day", "king", "bishop",
    "young", "white", "black", "brown", "green", "gray", "grey", "long", "short", "small", "little", "wise", "noble", "baker",
    "cook", "carter", "mason", "porter", "turner", "walker", "fisher", "hunter", "taylor", "love", "best", "good", "strong",
    "power", "sales", "branch", "credit", "trust", "cash", "angel", "iris", "amber", "crystal", "ruby", "pearl", "holly", "heather",
    "robin", "drew", "gene", "dean", "earl", "duke", "baron", "page", "reed", "wood", "west", "east", "north", "south", "china",
    "india", "chile", "america", "france", "holland", "ireland", "england", "wales", "savings", "money", "sterling", "check",
})

# Per-source, per-type minimum model score. Calibrated on the dev sets by bench/calibrate.py: for each (source, type)
# the highest threshold that keeps that type's dev recall at >= 99% of its unthresholded value. A threshold is kept
# only if it buys >= 0.3 points of precision on some dev set: the rest gave nothing and would only add recall risk
# on unseen documents. Net effect is small (about +1 point): GLiNER's low-score findings are what carry recall.
THRESHOLDS: dict = {"gliner": {"FIN_ID": 0.25, "GOV_ID": 0.5}}

# Minimum score for a model finding that NOTHING else supports (no rule and no other model overlaps it), keyed by
# source and the model's own fine label. 1.01 means "never on its own". Calibrated on the dev sets by
# `bench/calibrate.py solo` under the same recall constraints as THRESHOLDS. GLiNER run with 35 labels at a low
# threshold produces many lone guesses ("occupation": "Corporate Governance Guidelines"); when OpenMed or a rule
# agrees the finding is kept regardless of this table.
SOLO_THRESHOLDS: dict = {"gliner": {"api key": 0.4, "bank": 0.25, "insurance company": 0.3, "street address": 1.01, "url": 0.4}}

# Rule ids that match already-masked partial identifiers (used by the "keep last 4 digits" setting).
MASKED_RULE_IDS = ["masked_card", "masked_last4", "masked_iban", "masked_ssn"]

# Where to insert a virtual space before running a model (B4): digit->Capitalised word, letters->long digit run,
# long digit run->upper-case code. Deliberately narrow so IBANs, postcodes and ordinals ("4th", "NW1 6XE") stay whole.
GLUE_PATTERN = r"(?<=\d)(?=[A-Z][a-z])|(?<=[a-z]{2})(?=\d{4})|(?<=\d{4})(?=[A-Z]{3})"

# Generic words that are never personal data on their own: pronouns, contract roles and defined terms, field labels.
# A finding whose whole (normalised) text is one of these is dropped unless the user added it. Built from general
# knowledge plus the most frequent false positives on the DEV sets.
GENERIC_TERMS = sorted({
    # pronouns and determiners
    "i", "we", "you", "he", "she", "they", "it", "me", "us", "him", "her", "them", "my", "our", "your", "his", "their", "its", "ours", "yours",
    "this", "that", "these", "those", "who", "whom", "which", "all", "any", "each", "other", "others", "one", "none", "n/a", "na", "nan", "null", "tbd",
    # roles and parties (contract defined terms)
    "company", "companies", "company name", "holding company", "parent company", "insurance company", "bank", "banks", "fund", "funds", "trust", "group",
    "firm", "institution", "organization", "organisation", "entity", "entities", "corporation", "partnership", "business", "department", "branch",
    "borrower", "borrowers", "lender", "lenders", "customer", "customers", "client", "clients", "employee", "employees", "employer", "employers",
    "contractor", "contractors", "consultant", "consultants", "agent", "agents", "policyholder", "policyholders", "insured", "insured party", "insurer",
    "shareholder", "shareholders", "service provider", "supplier", "suppliers", "vendor", "vendors", "buyer", "seller", "purchaser", "landlord", "tenant",
    "lessor", "lessee", "licensor", "licensee", "trustee", "trustees", "beneficiary", "beneficiaries", "guarantor", "party", "parties", "counterparty",
    "investor", "investors", "member", "members", "user", "users", "holder",
    "account holder", "cardholder", "participant", "participants", "recipient", "sender", "payer", "payee", "debtor", "creditor", "owner", "manager",
    "management", "director", "directors", "officer", "officers", "staff", "team", "individual", "individuals", "person", "persons", "people",
    "representative", "authorized person", "authorised person", "administrator", "plan administrator", "committee", "board", "board of directors",
    # documents and defined terms
    "agreement", "contract", "policy", "policies", "plan", "program", "programme", "guidelines", "code of conduct", "terms", "conditions", "schedule",
    "document", "statement", "report", "notice", "form", "application", "certificate", "prospectus", "regulations", "regulation", "rules", "law", "laws",
    "audit", "compliance", "bonds", "shares", "securities", "loan", "mortgage", "premium", "claim", "claims", "transaction", "transactions", "payment",
    "payments", "data", "information", "services", "service", "products", "product", "system", "systems", "software", "website", "site", "portal",
    # field labels
    "name", "first name", "last name", "full name", "email", "e-mail", "email address", "phone", "phone number", "telephone", "fax", "address",
    "street address", "city", "state", "country", "zip", "zip code", "postcode", "postal code", "date", "time", "effective date", "date of birth", "dob",
    "expiration date", "collection date", "account", "account number", "routing number", "card number", "password", "username", "user name", "login",
    "pin", "id", "ssn", "tax", "tax id", "message", "subject", "signature", "title", "position", "occupation", "gender", "age", "nationality", "status",
    "amount", "balance", "total", "currency", "reference", "description", "notes", "comments", "utf-8", "true", "false", "yes", "no",
})

