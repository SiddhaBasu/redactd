// Display metadata for the coarse types, plus label maps generated from redactd/coarse.py and redactd/types.py.
import { SPEC } from "./rules.ts";
import type { PiiType } from "./types.ts";

export const FINE_TO_COARSE: Record<string, PiiType> = Object.fromEntries(
  Object.entries(SPEC.groups as Record<string, string[]>).flatMap(([g, ls]) => ls.map((l) => [l, g as PiiType])));
export const GLINER_LABELS = SPEC.gliner_labels as Record<string, PiiType>;
export const DIRECT_TYPES = new Set<string>(SPEC.direct_types);

export interface TypeInfo { label: string; short: string; tier: "direct" | "indirect"; /** token name: CSS vars --t-<token>-bg / -fg / -bd */ token: string; description: string }
export const TYPE_INFO: Record<PiiType, TypeInfo> = {
  NAME: { label: "Names", short: "Name", tier: "direct", token: "name", description: "People and usernames" },
  CONTACT: { label: "Contact", short: "Contact", tier: "direct", token: "contact", description: "Email, phone, URL" },
  ADDRESS: { label: "Addresses", short: "Address", tier: "direct", token: "address", description: "Street, city, postcode, country" },
  GOV_ID: { label: "Government IDs", short: "Gov ID", tier: "direct", token: "gov", description: "SSN, passport, licence, tax ID" },
  FIN_ID: { label: "Financial IDs", short: "Fin ID", tier: "direct", token: "fin", description: "Account, card, routing, IBAN, SWIFT, customer IDs" },
  SECRET: { label: "Secrets", short: "Secret", tier: "direct", token: "secret", description: "Passwords, PINs, API keys" },
  NETWORK: { label: "Network", short: "Network", tier: "direct", token: "network", description: "IP, MAC, device IDs" },
  DATE: { label: "Dates", short: "Date", tier: "indirect", token: "date", description: "Dates and times" },
  ORG: { label: "Organisations", short: "Org", tier: "indirect", token: "org", description: "Companies, banks, insurers" },
  DEMOGRAPHIC: { label: "Demographics", short: "Demo", tier: "indirect", token: "demo", description: "Age, gender, occupation and similar" },
  CUSTOM: { label: "Custom terms", short: "Custom", tier: "direct", token: "custom", description: "Terms you added" },
};
export const TYPES = Object.keys(TYPE_INFO) as PiiType[];
export const SOURCE_NAMES: Record<string, string> = {
  rules: "Pattern rules", openmed: "OpenMed model", gliner: "GLiNER-PII model", distilled: "redactd-small model",
  propagated: "Repeat of another finding", manual: "Added by you", custom: "Your custom terms",
};
