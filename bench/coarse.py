"""Coarse entity types used for training our own model and for placeholder names."""
GROUPS = {
    "NAME": ["name", "first_name", "last_name", "user_name"],
    "CONTACT": ["email", "phone_number", "fax_number", "url"],
    "ADDRESS": ["street_address", "postcode", "city", "county", "state", "country", "coordinate", "local_latlng"],
    "GOV_ID": ["ssn", "passport_number", "driver_license_number", "certificate_license_number", "tax_id",
               "medical_record_number", "health_plan_beneficiary_number", "biometric_identifier",
               "license_plate", "vehicle_identifier"],
    "FIN_ID": ["account_number", "credit_debit_card", "credit_card_number", "credit_card_security_code", "cvv",
               "bank_routing_number", "iban", "bban", "swift_bic", "swift_bic_code", "account_pin", "pin",
               "customer_id", "employee_id", "unique_id"],
    "SECRET": ["password", "api_key", "http_cookie"],
    "NETWORK": ["ipv4", "ipv6", "mac_address", "device_identifier"],
    "DATE": ["date", "time", "date_time", "date_of_birth"],
    "ORG": ["company", "company_name"],
    "DEMOGRAPHIC": ["occupation", "employment_status", "education_level", "age", "gender", "race_ethnicity",
                    "religious_belief", "political_view", "sexuality", "language", "blood_type"],
}
TYPES = list(GROUPS)
COARSE = {l: g for g, ls in GROUPS.items() for l in ls}
