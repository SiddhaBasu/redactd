// Password-protected placeholder map (the "restore key"). AES-GCM with a PBKDF2-derived key, all in the browser.
import type { Vault } from "./redact";

const enc = new TextEncoder(), dec = new TextDecoder();
const b64 = (b: ArrayBuffer | Uint8Array) => btoa(String.fromCharCode(...new Uint8Array(b as ArrayBuffer)));
const unb64 = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0)) as Uint8Array<ArrayBuffer>;

async function deriveKey(password: string, salt: Uint8Array<ArrayBuffer>) {
  const base = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations: 310_000, hash: "SHA-256" }, base,
    { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export interface SealedVault { v: 1; kdf: "PBKDF2-SHA256-310k"; salt: string; iv: string; data: string }

export async function sealVault(vault: Vault, password: string): Promise<SealedVault> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt);
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(JSON.stringify(vault)));
  return { v: 1, kdf: "PBKDF2-SHA256-310k", salt: b64(salt), iv: b64(iv), data: b64(ct) };
}

export async function openVault(sealed: SealedVault, password: string): Promise<Vault> {
  const key = await deriveKey(password, unb64(sealed.salt));
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(sealed.iv) }, key, unb64(sealed.data));
  return JSON.parse(dec.decode(pt));
}
