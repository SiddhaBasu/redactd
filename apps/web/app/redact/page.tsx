"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { TYPE_INFO } from "../../lib/labels";
import { leakCheck, mergeSpans, propagate, render } from "../../lib/redact";
import { sealVault } from "../../lib/vault";
import type { DetectMode, OutputStyle, PiiType, ReviewSpan, Span, WorkerResponse } from "../../lib/types";

const MAX_BYTES = 1_000_000;
const MODES: { id: DetectMode; name: string; note: string }[] = [
  { id: "rules", name: "Fast", note: "Pattern rules only · instant · structured IDs" },
  { id: "standard", name: "Standard", note: "+ OpenMed model · ~170 MB one-time download" },
  { id: "thorough", name: "Thorough", note: "+ GLiNER-PII · ~370 MB total · best recall" },
];

function download(name: string, data: string, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([data], { type }));
  Object.assign(document.createElement("a"), { href: url, download: name }).click();
  URL.revokeObjectURL(url);
}

export default function RedactPage() {
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("document.txt");
  const [mode, setMode] = useState<DetectMode>("thorough");
  const [sensitivity, setSensitivity] = useState(0.35);
  const [spans, setSpans] = useState<ReviewSpan[] | null>(null);
  const [progress, setProgress] = useState<{ stage: string; pct: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [style, setStyle] = useState<OutputStyle>("placeholder");
  const [hidden, setHidden] = useState<Set<PiiType>>(new Set());
  const [password, setPassword] = useState("");
  const [addType, setAddType] = useState<PiiType>("NAME");
  const worker = useRef<Worker | null>(null);
  const viewer = useRef<HTMLDivElement>(null);

  useEffect(() => () => worker.current?.terminate(), []);

  function scan() {
    setError(null); setSpans(null); setElapsed(null);
    worker.current ??= new Worker(new URL("../../workers/detect.worker.ts", import.meta.url), { type: "module" });
    worker.current.onmessage = (e: MessageEvent<WorkerResponse>) => {
      const m = e.data;
      if (m.kind === "progress") setProgress({ stage: m.stage, pct: m.pct });
      else if (m.kind === "error") { setError(m.message); setProgress(null); }
      else {
        const all = propagate(text, mergeSpans(m.spans as Span[]));
        setSpans(all.map((s, id) => ({ ...s, id, accepted: true })));
        setElapsed(m.ms); setProgress(null);
      }
    };
    worker.current.postMessage({ kind: "detect", text, mode, sensitivity });
  }

  async function onFile(f: File) {
    if (f.size > MAX_BYTES) { setError(`File is ${(f.size / 1e6).toFixed(2)} MB; the limit is 1 MB.`); return; }
    setText(await f.text()); setFileName(f.name); setSpans(null);
  }

  function addSelection() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !viewer.current || !spans) return;
    const r = sel.getRangeAt(0);
    const pre = document.createRange();
    pre.selectNodeContents(viewer.current);
    pre.setEnd(r.startContainer, r.startOffset);
    const start = pre.toString().length, end = start + r.toString().length;
    if (end <= start || text.slice(start, end) !== r.toString()) return;
    const next = propagate(text, mergeSpans([...spans.filter((s) => s.accepted), { start, end, type: addType, source: "manual" }]));
    setSpans(next.map((s, id) => ({ ...s, id, accepted: true })));
    sel.removeAllRanges();
  }

  const accepted = useMemo(() => (spans ?? []).filter((s) => s.accepted), [spans]);
  const result = useMemo(() => (spans ? render(text, accepted, style) : null), [spans, accepted, text, style]);
  const leaks = useMemo(
    () => (result ? leakCheck(result.output, accepted.map((s) => text.slice(s.start, s.end))) : []),
    [result, accepted, text],
  );
  const counts = useMemo(() => {
    const c: Partial<Record<PiiType, { n: number; on: number }>> = {};
    for (const s of spans ?? []) { const x = (c[s.type] ??= { n: 0, on: 0 }); x.n++; if (s.accepted) x.on++; }
    return c;
  }, [spans]);

  const toggleType = (t: PiiType, on: boolean) => setSpans((ss) => ss && ss.map((s) => (s.type === t ? { ...s, accepted: on } : s)));
  const toggleSpan = (id: number) => setSpans((ss) => ss && ss.map((s) => (s.id === id ? { ...s, accepted: !s.accepted } : s)));

  const segments = useMemo(() => {
    if (!spans) return null;
    const out: React.ReactNode[] = [];
    let last = 0;
    for (const s of spans) {
      if (s.start > last) out.push(text.slice(last, s.start));
      const info = TYPE_INFO[s.type];
      const show = !hidden.has(s.type);
      out.push(
        <button key={s.id} type="button" onClick={() => toggleSpan(s.id)}
          title={`${info.label} · ${s.source}${s.score ? ` · ${(s.score * 100).toFixed(0)}%` : ""} — click to ${s.accepted ? "keep" : "redact"}`}
          className={`rounded px-0.5 ${show ? info.color : ""} ${s.accepted ? "" : "line-through opacity-50"}`}>
          {text.slice(s.start, s.end)}
        </button>,
      );
      last = s.end;
    }
    out.push(text.slice(last));
    return out;
  }, [spans, text, hidden]);

  async function downloadKey() {
    if (!result || password.length < 8) return;
    const sealed = await sealVault(result.vault, password);
    download(fileName.replace(/\.[^.]+$/, "") + ".redactd-key.json", JSON.stringify(sealed), "application/json");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Redact a document</h1>
        <p className="text-sm muted">Text files up to 1 MB. Detection runs in this tab — nothing is uploaded.</p>
      </div>

      {/* 1. Input */}
      <section className="card space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <label className="btn cursor-pointer">
            Choose file
            <input type="file" className="hidden" accept=".txt,.md,.csv,.json,.log,.eml,.xml,text/*"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          </label>
          <span className="text-sm muted">or paste below · {text.length.toLocaleString()} characters</span>
        </div>
        <textarea className="input mono h-48" placeholder="Paste a statement, email, loan note, ticket…" value={text}
          onChange={(e) => { setText(e.target.value.slice(0, MAX_BYTES)); setSpans(null); }} />
        <div className="grid gap-3 sm:grid-cols-3">
          {MODES.map((m) => (
            <button key={m.id} type="button" onClick={() => setMode(m.id)}
              className={`card p-3 text-left text-sm ${mode === m.id ? "ring-2 ring-teal-600" : ""}`}>
              <div className="font-medium">{m.name}</div>
              <div className="text-xs muted">{m.note}</div>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            Sensitivity
            <input type="range" min={0.2} max={0.9} step={0.05} value={+(1 - sensitivity).toFixed(2)}
              onChange={(e) => setSensitivity(+(1 - +e.target.value).toFixed(2))} />
            <span className="muted text-xs">{sensitivity <= 0.3 ? "catch more" : sensitivity >= 0.6 ? "fewer flags" : "balanced"}</span>
          </label>
          <button className="btn btn-primary ml-auto" disabled={!text || !!progress} onClick={scan}>
            {progress ? "Scanning…" : "Scan for sensitive data"}
          </button>
        </div>
        {progress && (
          <div>
            <div className="h-2 w-full overflow-hidden rounded bg-stone-200 dark:bg-stone-800">
              <div className="h-full bg-teal-600 transition-all" style={{ width: `${progress.pct}%` }} />
            </div>
            <p className="mt-1 text-xs muted">{progress.stage}</p>
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </section>

      {/* 2. Review */}
      {spans && (
        <section className="grid gap-4 lg:grid-cols-[1fr_260px]">
          <div className="card p-5">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">Review</span>
              <span className="muted">{accepted.length} of {spans.length} findings will be redacted · {elapsed && `${(elapsed / 1000).toFixed(1)} s`}</span>
              <span className="ml-auto flex items-center gap-2">
                <select className="input w-auto py-1" value={addType} onChange={(e) => setAddType(e.target.value as PiiType)}>
                  {Object.entries(TYPE_INFO).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
                <button className="btn py-1" onClick={addSelection}>Redact selection</button>
              </span>
            </div>
            <div ref={viewer} className="mono max-h-[60vh] overflow-auto whitespace-pre-wrap break-words text-sm leading-6">{segments}</div>
            <p className="mt-3 text-xs muted">Click a highlight to keep that text. Select any text and press “Redact selection” to add it.</p>
          </div>
          <aside className="card h-fit space-y-2 p-4 text-sm">
            <div className="font-medium">Categories</div>
            {(Object.keys(TYPE_INFO) as PiiType[]).filter((t) => counts[t]).map((t) => (
              <div key={t} className="flex items-center gap-2">
                <input type="checkbox" checked={counts[t]!.on === counts[t]!.n}
                  onChange={(e) => toggleType(t, e.target.checked)} />
                <span className={`h-3 w-3 rounded ${TYPE_INFO[t].color}`} />
                <span className="flex-1">{TYPE_INFO[t].label}</span>
                <span className="muted text-xs">{counts[t]!.on}/{counts[t]!.n}</span>
                <button className="text-xs muted underline" onClick={() => setHidden((h) => {
                  const n = new Set(h); n.has(t) ? n.delete(t) : n.add(t); return n; })}>
                  {hidden.has(t) ? "show" : "hide"}
                </button>
              </div>
            ))}
            <p className="pt-2 text-xs muted">Direct identifiers name a person or account on their own. Dates, organisations and demographics can identify someone in combination.</p>
          </aside>
        </section>
      )}

      {/* 3. Output */}
      {result && (
        <section className="card space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="font-medium">Output</span>
            {(["placeholder", "label", "block"] as OutputStyle[]).map((s) => (
              <label key={s} className="flex items-center gap-1">
                <input type="radio" checked={style === s} onChange={() => setStyle(s)} />
                {s === "placeholder" ? "Reversible [NAME_1]" : s === "label" ? "Labels [NAME]" : "Blocks ████"}
              </label>
            ))}
            <span className={`ml-auto rounded px-2 py-0.5 text-xs ${leaks.length ? "bg-red-100 text-red-700" : "bg-teal-100 text-teal-800"}`}>
              {leaks.length ? `${leaks.length} value(s) still present` : "Leak check passed"}
            </span>
          </div>
          <pre className="mono max-h-72 overflow-auto whitespace-pre-wrap rounded border p-3 text-sm" style={{ borderColor: "var(--border)" }}>{result.output}</pre>
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn btn-primary" disabled={leaks.length > 0}
              onClick={() => download(fileName.replace(/(\.[^.]+)?$/, ".redacted$1"), result.output)}>
              Download redacted file
            </button>
            {style === "placeholder" && (
              <>
                <input type="password" className="input w-56" placeholder="Password for restore key (8+ chars)"
                  value={password} onChange={(e) => setPassword(e.target.value)} />
                <button className="btn" disabled={password.length < 8} onClick={downloadKey}>Download restore key</button>
                <span className="text-xs muted">Encrypted in your browser. We never see it.</span>
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
