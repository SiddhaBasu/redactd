// Strict Content-Security-Policy with a per-request nonce (task E1).
//  * scripts: only our own, started by Next's nonce'd bootstrap ('strict-dynamic'); no inline scripts, no eval.
//    'wasm-unsafe-eval' is required to compile the ONNX Runtime WebAssembly module (it does not allow JS eval).
//  * connect: this origin, the API origin and the model CDN only. blob: is for verified model bytes handed to
//    the runtime inside the worker.
//  * no framing, no plugins, no form posts elsewhere.
import { NextResponse, type NextRequest } from "next/server";

const origin = (u: string | undefined) => { try { return u ? new URL(u).origin : ""; } catch { return ""; } };
const API = origin(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");
const MODELS = origin(process.env.NEXT_PUBLIC_MODEL_BASE);
const DEV = process.env.NODE_ENV !== "production";

export function buildCsp(nonce: string): string {
  const connect = ["'self'", API, MODELS, "blob:", ...(DEV ? ["ws:"] : [])].filter(Boolean).join(" ");
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' 'wasm-unsafe-eval'${DEV ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",          // React sets element styles (virtualised row positions); no user HTML is ever rendered
    "img-src 'self' data: blob:", "font-src 'self'",
    `connect-src ${connect}`,
    "worker-src 'self' blob:", "child-src 'self' blob:",
    "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'", "manifest-src 'self'",
    ...(DEV ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

export function middleware(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce);
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce); headers.set("content-security-policy", csp);      // Next reads the nonce from this request header
  const res = NextResponse.next({ request: { headers } });
  res.headers.set("Content-Security-Policy", csp);
  return res;
}
export const config = { matcher: [{ source: "/((?!_next/static|_next/image|ort/|ort-gliner/|models/|favicon.ico).*)", missing: [{ type: "header", key: "next-router-prefetch" }, { type: "header", key: "purpose", value: "prefetch" }] }] };
