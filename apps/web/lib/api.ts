// Client for the redactd API (server mode). Text is sent over HTTPS, processed in memory and never stored.
// Custom terms and allow-list terms are NOT sent: they are applied in the browser (lib/redact.ts applyTerms).
import { convertOffsets } from "./redact.ts";
import type { DetectMode, Options, Span } from "./types.ts";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const SYNC_LIMIT = 200_000;

export interface Health { status: string; ready_modes: string[]; versions?: Record<string, string>; sync_limit_chars?: number }
export async function serverHealth(signal?: AbortSignal): Promise<Health | null> {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: signal ?? AbortSignal.timeout(4000), cache: "no-store" });
    return r.ok ? ((await r.json()) as Health) : null;
  } catch { return null; }
}

export interface DetectResult { spans: Span[]; timings: Record<string, number>; versions?: Record<string, string> }
type Progress = (stage: string, pct: number) => void;

/** The server returns raw (unmerged) findings; lib/redact.ts finalize() applies the policy in the browser. So the
 *  request carries only the text, the mode and the sensitivity: no custom terms, no allow-list, no preset. */
function body(text: string, mode: DetectMode, o: Options) {
  return JSON.stringify({ text, mode, sensitivity: o.sensitivity, raw: true });
}
async function fail(r: Response): Promise<never> {
  let detail = `${r.status}`;
  try { const j = await r.json(); if (typeof j.detail === "string") detail = j.detail; } catch { /* no body */ }
  if (r.status === 429) throw new Error("Too many requests. Wait a minute and try again, or switch to on-device processing.");
  if (r.status === 413) throw new Error("This document is too large for the server.");
  throw new Error(`The server could not process this document (${detail}).`);
}

export async function detectOnServer(text: string, mode: DetectMode, o: Options, onProgress?: Progress, signal?: AbortSignal): Promise<DetectResult> {
  const headers = { "Content-Type": "application/json" };
  let res: DetectResult;
  if (text.length <= SYNC_LIMIT / 4) {
    onProgress?.("Scanning on the server", 30);
    const r = await fetch(`${API_BASE}/v1/detect`, { method: "POST", headers, body: body(text, mode, o), signal });
    if (!r.ok) await fail(r);
    res = (await r.json()) as DetectResult;
  } else {
    onProgress?.("Uploading", 2);
    const r = await fetch(`${API_BASE}/v1/jobs`, { method: "POST", headers, body: body(text, mode, o), signal });
    if (!r.ok) await fail(r);
    const { job_id } = (await r.json()) as { job_id: string };
    await followJob(job_id, onProgress, signal);
    const g = await fetch(`${API_BASE}/v1/jobs/${job_id}`, { signal, cache: "no-store" });
    if (!g.ok) await fail(g);
    const j = (await g.json()) as { status: string; result?: DetectResult; error?: string };
    if (j.status !== "done" || !j.result) throw new Error("The server could not process this document.");
    res = j.result;
  }
  onProgress?.("Preparing review", 99);
  return { ...res, spans: convertOffsets(text, res.spans, "utf16") };
}

/** Follow job progress over server-sent events; resolves when the job is finished (result is then fetched once). */
function followJob(id: string, onProgress?: Progress, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const es = new EventSource(`${API_BASE}/v1/jobs/${id}/events`);
    const stop = () => es.close();
    signal?.addEventListener("abort", () => { stop(); reject(new DOMException("aborted", "AbortError")); });
    es.addEventListener("progress", (e) => { const d = JSON.parse((e as MessageEvent).data); onProgress?.(d.stage, d.pct); });
    es.addEventListener("done", () => { stop(); resolve(); });
    es.addEventListener("failed", () => { stop(); reject(new Error("The server could not process this document.")); });
    es.onerror = () => { if (es.readyState === EventSource.CLOSED) { stop(); resolve(); } };  // fall through to the result fetch
  });
}

export interface Extracted { text: string; format: string; attachments: number; attachments_included: boolean; chars: number }
/** Convert .docx / .pdf / .eml / .msg to text on the server (in memory; nothing is stored). */
export async function extractOnServer(file: File, includeAttachments = false, signal?: AbortSignal): Promise<Extracted> {
  const fd = new FormData();
  fd.append("file", file, file.name); fd.append("include_attachments", includeAttachments ? "true" : "false");
  const r = await fetch(`${API_BASE}/v1/extract`, { method: "POST", body: fd, signal });
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json()).detail ?? ""; } catch { /* no body */ }
    throw new Error(r.status === 415 ? `This file could not be read${detail ? `: ${detail}` : ""}.` : r.status === 413 ? "This file is too large." : "The server could not read this file.");
  }
  return (await r.json()) as Extracted;
}
