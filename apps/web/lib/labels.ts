import type { PiiType } from "./types";

export const TYPE_INFO: Record<PiiType, { label: string; tier: "direct" | "indirect"; color: string }> = {
  NAME: { label: "Names", tier: "direct", color: "bg-rose-200 dark:bg-rose-900/60" },
  CONTACT: { label: "Contact", tier: "direct", color: "bg-orange-200 dark:bg-orange-900/60" },
  ADDRESS: { label: "Addresses & places", tier: "direct", color: "bg-amber-200 dark:bg-amber-900/60" },
  GOV_ID: { label: "Government IDs", tier: "direct", color: "bg-red-300 dark:bg-red-900/70" },
  FIN_ID: { label: "Financial IDs", tier: "direct", color: "bg-fuchsia-200 dark:bg-fuchsia-900/60" },
  SECRET: { label: "Secrets", tier: "direct", color: "bg-purple-300 dark:bg-purple-900/70" },
  NETWORK: { label: "Network & device", tier: "direct", color: "bg-sky-200 dark:bg-sky-900/60" },
  DATE: { label: "Dates & times", tier: "indirect", color: "bg-lime-200 dark:bg-lime-900/60" },
  ORG: { label: "Organisations", tier: "indirect", color: "bg-teal-200 dark:bg-teal-900/60" },
  DEMOGRAPHIC: { label: "Demographics", tier: "indirect", color: "bg-indigo-200 dark:bg-indigo-900/60" },
};

/** Fine-grained model labels (Nemotron/OpenMed schema) -> coarse types. Mirrors bench/coarse.py. */
const GROUPS: Record<PiiType, string[]> = {
  NAME: ["name", "first_name", "last_name", "user_name"],
  CONTACT: ["email", "phone_number", "fax_number", "url"],
  ADDRESS: ["street_address", "postcode", "city", "county", "state", "country", "coordinate", "local_latlng"],
  GOV_ID: ["ssn", "passport_number", "driver_license_number", "certificate_license_number", "tax_id",
    "medical_record_number", "health_plan_beneficiary_number", "biometric_identifier", "license_plate", "vehicle_identifier"],
  FIN_ID: ["account_number", "credit_debit_card", "credit_card_number", "credit_card_security_code", "cvv",
    "bank_routing_number", "iban", "bban", "swift_bic", "swift_bic_code", "account_pin", "pin",
    "customer_id", "employee_id", "unique_id"],
  SECRET: ["password", "api_key", "http_cookie"],
  NETWORK: ["ipv4", "ipv6", "mac_address", "device_identifier"],
  DATE: ["date", "time", "date_time", "date_of_birth"],
  ORG: ["company", "company_name"],
  DEMOGRAPHIC: ["occupation", "employment_status", "education_level", "age", "gender", "race_ethnicity",
    "religious_belief", "political_view", "sexuality", "language", "blood_type"],
};
export const FINE_TO_COARSE: Record<string, PiiType> = Object.fromEntries(
  Object.entries(GROUPS).flatMap(([g, ls]) => ls.map((l) => [l, g as PiiType])),
);

/** GLiNER zero-shot labels -> coarse types (same list the benchmark used, plus finance org labels). */
export const GLINER_LABELS: Record<string, PiiType> = {
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
};
