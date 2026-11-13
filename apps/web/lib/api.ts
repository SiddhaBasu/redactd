// Client for the redactd API. Detection runs on the backend; review, rendering and key encryption stay in the browser.
import type { DetectMode, Span } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const SYNC_LIMIT = 200_000;

type DetectResult = { spans: Span[]; timings: Record<string, number> };

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Server error ${r.status}`);
  return r.json();
}

export async function detectOnServer(text: string, mode: DetectMode, sensitivity: number,
  onProgress: (stage: string, pct: number) => void): Promise<DetectResult> {
  if (text.length <= SYNC_LIMIT) {
    onProgress("Scanning on server", 40);
    return post<DetectResult>("/v1/detect", { text, mode, sensitivity });
  }
  // Large documents: async job + polling
  const { job_id } = await post<{ job_id: string }>("/v1/jobs", { text, mode, sensitivity });
  for (let i = 0; ; i++) {
    await new Promise((r) => setTimeout(r, Math.min(500 + i * 250, 3000)));
    const r = await fetch(`${API_URL}/v1/jobs/${job_id}`);
    if (!r.ok) throw new Error("Job expired or not found");
    const j = await r.json();
    if (j.status === "done") return j.result;
    if (j.status === "error") throw new Error(j.error || "Detection failed");
    onProgress(`Large document: ${j.status} on server`, Math.min(95, 20 + i * 3));
  }
}

export async function serverHealth(): Promise<{ status: string; ready_modes: string[] } | null> {
  try { const r = await fetch(`${API_URL}/health`); return r.ok ? r.json() : null; } catch { return null; }
}
