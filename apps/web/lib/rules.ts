// Pattern rules with validators. TypeScript port of bench/regex_rules.py (keep in sync).
import type { PiiType, Span } from "./types";

export function luhn(s: string): boolean {
  const d = s.replace(/\D/g, "");
  if (d.length < 13 || d.length > 19) return false;
  let sum = 0;
  for (let i = 0; i < d.length; i++) {
    let x = +d[d.length - 1 - i];
    if (i % 2) { x *= 2; if (x > 9) x -= 9; }
    sum += x;
  }
  return sum % 10 === 0;
}

export function aba(s: string): boolean {
  if (!/^\d{9}$/.test(s)) return false;
  const d = [...s].map(Number);
  return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 === 0;
}

export function ibanOk(s: string): boolean {
  const c = s.replace(/\s/g, "").toUpperCase();
  if (c.length < 15 || c.length > 34) return false;
  const r = c.slice(4) + c.slice(0, 4);
  let rem = 0;
  for (const ch of r) {
    const v = parseInt(ch, 36);
    if (Number.isNaN(v)) return false;
    for (const digit of String(v)) rem = (rem * 10 + +digit) % 97;
  }
  return rem === 1;
}

const MONTH = "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)";
const ORG_SUFFIX =
  "Bank|Bancorp|Banking|Credit Union|Savings|Trust|Insurance(?: Company)?|Assurance|Capital|Partners|Holdings?|Group|Fund|Funds|Investments?|Securities|Financial|Finance|Asset Management|Advisors|Inc\\.?|Incorporated|LLC|L\\.L\\.C\\.|Ltd\\.?|Limited|PLC|plc|Corp\\.?|Corporation|Co\\.|Company|GmbH|AG|S\\.A\\.|N\\.V\\.|LLP|LP|Institute|University|College|Hospital|Clinic|Physical Therapy|Healthcare";

type Rule = { type: PiiType; re: RegExp; group?: number; validate?: (s: string) => boolean; filter?: (s: string) => boolean };

const RULES: Rule[] = [
  { type: "CONTACT", re: /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g },
  { type: "CONTACT", re: /\bhttps?:\/\/[^\s<>"')]+|\bwww\.[^\s<>"')]+/g },
  { type: "NETWORK", re: /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g },
  { type: "NETWORK", re: /\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b/g },
  { type: "NETWORK", re: /\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b/g },
  { type: "FIN_ID", re: /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b/g, validate: ibanOk },
  { type: "FIN_ID", re: /\b(?:\d[ -]?){12,18}\d\b/g, validate: luhn },
  { type: "FIN_ID", re: /\b\d{9}\b/g, validate: aba },
  { type: "FIN_ID", re: /\b[A-Z]{4}(?:US|GB|DE|FR|CH|IT|ES|NL|CA|AU|JP|SG|HK|IN|BE|IE|LU|SE|NO|DK|AT|PL|BR|MX|CN)[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b/g },
  { type: "FIN_ID", re: /(?:acct|account|a\/c|iban|card|routing|aba|customer|member|policy|loan|client)\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{5,})/gi, group: 1, validate: (v) => /\d/.test(v) },
  { type: "GOV_ID", re: /\b\d{3}-\d{2}-\d{4}\b/g },
  { type: "GOV_ID", re: /(?:ssn|social security(?: number)?|passport(?: no\.?| number)?|driver'?s? licen[cs]e(?: no\.?| number)?|tax id|tin|ein)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,})/gi, group: 1, validate: (v) => /\d/.test(v) },
  { type: "CONTACT", re: /(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?:\s?(?:x|ext\.?)\s?\d{1,5})?(?!\w)/g },
  { type: "CONTACT", re: /(?<!\w)\+\d{1,3}(?:[ .-]?\d{2,4}){2,5}(?!\w)/g },
  { type: "DATE", re: /\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b/g },
  { type: "DATE", re: /\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b/g },
  { type: "DATE", re: new RegExp(`\\b${MONTH}\\.? \\d{1,2}(?:st|nd|rd|th)?,? \\d{4}\\b|\\b\\d{1,2}(?:st|nd|rd|th)? ${MONTH}\\.?,? \\d{4}\\b`, "g") },
  { type: "ADDRESS", re: /\b\d{1,6}\s+(?:[A-Z][a-z]+\.?\s){1,4}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Way|Pl|Place|Ter|Terrace|Pkwy|Parkway|Cir|Circle|Hwy|Highway|Sq|Square)\b\.?(?:,?\s(?:Apt|Suite|Unit|#)\s?\w+)?/g },
  { type: "SECRET", re: /\b(?:sk|pk|rk|ghp|gho|xox[bap]|AKIA)[-_A-Za-z0-9]{12,}\b|\b[A-Za-z0-9_-]{32,}\b/g },
  { type: "SECRET", re: /(?:password|passwd|pwd|pin|cvv|cvc)\s*[:=]\s*(\S+)/gi, group: 1 },
  { type: "NAME", re: /\b(?:Mr|Ms|Mrs|Dr|Mx)\.?\s([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)/g, group: 1 },
  {
    type: "ORG",
    re: new RegExp(
      `\\b(?:The\\s)?(?:Bank|Banco|Banque|Caisse) (?:of|de|du|des|di) (?:the )?[A-Z]\\w*(?:\\s[A-Z]\\w*){0,3}|` +
      `\\b(?:The\\s)?(?:[A-Z][\\w&'.-]*\\s(?:(?:of|the|and|&|for|de)\\s)*){0,5}(?:${ORG_SUFFIX})\\b(?:\\s(?:of|de)\\s(?:the\\s)?[A-Z]\\w*(?:\\s[A-Z]\\w*){0,2})?(?:,?\\s(?:Inc\\.?|Ltd\\.?|LLC|N\\.A\\.|PLC))?` +
      `|\\b[A-Z][A-Z&.' -]{2,40}\\b(?:BANK|INSURANCE COMPANY|LTD\\.?|LLC|INC\\.?|CORP\\.?|PLC)\\b`, "g"),
    filter: (s) => s.trim().split(/\s+/).length >= 2 || s === s.toUpperCase(),
  },
];

export function detectRules(text: string): Span[] {
  const out: Span[] = [];
  for (const r of RULES) {
    r.re.lastIndex = 0;
    for (const m of text.matchAll(r.re)) {
      const g = r.group ?? 0;
      const val = m[g];
      if (val === undefined) continue;
      const start = m.index! + (g ? m[0].indexOf(val) : 0);
      if (r.validate && !r.validate(val)) continue;
      if (r.filter && !r.filter(val)) continue;
      out.push({ start, end: start + val.length, type: r.type, source: "rules" });
    }
  }
  return out;
}
