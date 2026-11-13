// Password-encrypted restore key. Everything happens in the browser with WebCrypto; the password and the vault
// never leave the device. Format v1: PBKDF2-SHA256 (600k iterations) -> AES-256-GCM.
export interface SealedVault { v: 1; kdf: "PBKDF2-SHA256"; iter: number; salt: string; iv: string; ct: string; created?: string; entries?: number }

const b64 = (b: Uint8Array) => { let s = ""; for (const x of b) s += String.fromCharCode(x); return btoa(s); };
const unb64 = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
export const KDF_ITERATIONS = 600_000;

async function key(password: string, salt: Uint8Array, iter: number) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations: iter }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function sealVault(vault: Record<string, string>, password: string, iter = KDF_ITERATIONS): Promise<SealedVault> {
  const salt = crypto.getRandomValues(new Uint8Array(16)), iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await key(password, salt, iter), new TextEncoder().encode(JSON.stringify(vault)));
  return { v: 1, kdf: "PBKDF2-SHA256", iter, salt: b64(salt), iv: b64(iv), ct: b64(new Uint8Array(ct)), created: new Date().toISOString(), entries: Object.keys(vault).length };
}

export function isSealedVault(x: unknown): x is SealedVault {
  const o = x as SealedVault;
  return !!o && o.v === 1 && o.kdf === "PBKDF2-SHA256" && typeof o.iter === "number" && [o.salt, o.iv, o.ct].every((s) => typeof s === "string");
}

/** Throws if the password is wrong or the file was modified (AES-GCM authenticates the contents). */
export async function openVault(sealed: SealedVault, password: string): Promise<Record<string, string>> {
  if (!isSealedVault(sealed)) throw new Error("not a redactd restore key");
  if (sealed.iter < 1 || sealed.iter > 5_000_000) throw new Error("unsupported key parameters");
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(sealed.iv) as BufferSource }, await key(password, unb64(sealed.salt), sealed.iter), unb64(sealed.ct) as BufferSource);
  return JSON.parse(new TextDecoder().decode(pt));
}

/** Rough password strength, 0-4, with a hint. Length matters most for an offline-attackable file. */
export function passwordStrength(pw: string): { score: 0 | 1 | 2 | 3 | 4; label: string; hint: string } {
  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((r) => r.test(pw)).length;
  const unique = new Set(pw).size;
  let bits = pw.length * Math.log2(Math.max(2, [0, 26, 36, 62, 80][classes] || 26));
  if (unique <= Math.max(2, pw.length / 3)) bits *= 0.5;
  if (/^(?:password|passw0rd|qwerty|letmein|12345678|11111111|iloveyou|admin123|welcome1?)/i.test(pw)) bits = Math.min(bits, 12);
  const score = (pw.length < 8 ? 0 : bits < 45 ? 1 : bits < 60 ? 2 : bits < 80 ? 3 : 4) as 0 | 1 | 2 | 3 | 4;
  return { score, label: ["Too short", "Weak", "Fair", "Good", "Strong"][score],
    hint: score >= 3 ? "Hard to guess. Store it somewhere safe: it cannot be recovered." : pw.length < 8 ? "Use at least 8 characters." : "Longer is stronger: try four or more unrelated words." };
}
