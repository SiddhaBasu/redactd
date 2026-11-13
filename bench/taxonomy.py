"""Map dataset-specific labels to DIRECT vs INDIRECT identifiers.

DIRECT  = identifies a person/account on its own (name, SSN, account number, email...).
INDIRECT = quasi-identifier: identifying only in combination (city, occupation, age, gender, company, dates...).
Labels not listed are ignored (not scored).
"""
DIRECT = {
    # names
    "name", "first_name", "last_name", "user_name",
    # contact
    "email", "phone_number", "fax_number", "street_address", "url",
    # government / personal ids
    "ssn", "passport_number", "driver_license_number", "certificate_license_number", "tax_id",
    "medical_record_number", "health_plan_beneficiary_number", "biometric_identifier", "national_id",
    "date_of_birth", "license_plate", "vehicle_identifier",
    # financial ids
    "account_number", "credit_debit_card", "credit_card_number", "credit_card_security_code", "cvv",
    "bank_routing_number", "iban", "bban", "swift_bic", "swift_bic_code", "account_pin", "pin",
    "customer_id", "employee_id", "unique_id",
    # digital
    "password", "api_key", "ipv4", "ipv6", "mac_address", "device_identifier", "http_cookie",
    "coordinate", "local_latlng",
}
INDIRECT = {
    "city", "state", "county", "country", "postcode",
    "occupation", "employment_status", "education_level", "age", "gender", "race_ethnicity",
    "religious_belief", "political_view", "sexuality", "language", "blood_type",
    "company", "company_name", "date", "time", "date_time",
}

def tier(label: str):
    if label in DIRECT:
        return "direct"
    if label in INDIRECT:
        return "indirect"
    return None
