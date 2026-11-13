"use client";
// The workspace: add a document -> scan -> review every finding -> export a redacted copy (+ optional restore key).
// Detection returns raw findings (from the API or the on-device worker); the policy is always applied here in the
// browser by lib/redact.ts finalize(), so presets, custom terms and the allow-list never leave the device and can
// be changed after a scan without sending the document again.
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { TYPE_INFO, TYPES } from "../../lib/labels";
import { finalize, leakCheck, render, replacementsFor } from "../../lib/redact";
import { sealVault, passwordStrength } from "../../lib/vault";
import { detectOnServer, extractOnServer, serverHealth } from "../../lib/api";
import { DEFAULT_POLICY, loadPolicy, optionsFor, presetById, savePolicy, styleFor, type UserPolicy } from "../../lib/presets";
import { emptyReview, rejectedKeys, reviewReducer, searchSpans, valueOf } from "../../lib/review";
import { baseName, buildReport, redactedName, reportMarkdown } from "../../lib/report";
import { SAMPLE_NAME, SAMPLE_TEXT } from "../../lib/sample";
import { RULES_VERSION } from "../../lib/rules";
import type { DetectMode, OutputStyle, PiiType, ReviewSpan, Span, WorkerResponse } from "../../lib/types";
import { Viewer, type ViewerHandle } from "../../components/Viewer";
import { Sidebar } from "../../components/Sidebar";
import { PolicyPanel } from "../../components/PolicyPanel";
import { DataPanel, type Where } from "../../components/DataPanel";
import { ShortcutOverlay } from "../../components/Shortcuts";
import { Progress, Segmented, Steps } from "../../components/ui";

const MAX_BYTES = 1_000_000;
const MODES: { id: DetectMode; name: string; note: string }[] = [
  { id: "rules", name: "Fast", note: "Pattern rules with checksums. Structured identifiers only." },
  { id: "standard", name: "Standard", note: "Rules plus a compact model: names, places, context." },
  { id: "thorough", name: "Thorough", note: "Adds a second model for the best recall. Recommended." },
];
const BINARY = /\.(docx|pdf|msg)$/i, EMAIL = /\.eml$/i;
const DEVICE_MODEL_MB = Number(process.env.NEXT_PUBLIC_DEVICE_MODEL_MB || 370);

function download(name: string, data: string, type = "text/plain;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const typing = (t: EventTarget | null) => t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));

export default function RedactPage() {
  // ---- document + settings
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("document.txt");
  const [mode, setMode] = useState<DetectMode>("thorough");
  const [where, setWhere] = useState<Where>("server");
  const [policy, setPolicyState] = useState<UserPolicy>(DEFAULT_POLICY);
  const [serverUp, setServerUp] = useState<boolean | null>(null);
  const [online, setOnline] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [attach, setAttach] = useState<{ file: File; count: number } | null>(null);
  // ---- scan
  const [progress, setProgress] = useState<{ stage: string; pct: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scan, setScan] = useState<{ raw: Span[]; ms: number; versions: Record<string, string>; where: Where; mode: DetectMode } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const worker = useRef<Worker | null>(null);
  // ---- review
  const [review, dispatch] = useReducer(reviewReducer, emptyReview);
  const [hidden, setHidden] = useState<Set<PiiType>>(new Set());
  const [below, setBelow] = useState(0.7);
  const [filterOn, setFilterOn] = useState(false);
  const [view, setView] = useState<"review" | "diff">("review");
  const [addType, setAddType] = useState<PiiType>("NAME");
  const [search, setSearch] = useState<string | null>(null);
  const [help, setHelp] = useState(false);
  const [announce, setAnnounce] = useState("");
  // ---- output
  const [styleOverride, setStyleOverride] = useState<OutputStyle | null>(null);
  const [password, setPassword] = useState("");
  const [leaks, setLeaks] = useState<string[] | null>([]);
  const [copied, setCopied] = useState(false);
  const viewer = useRef<ViewerHandle>(null), searchBox = useRef<HTMLInputElement>(null), exportRef = useRef<HTMLElement>(null);

  const style = styleOverride ?? styleFor(policy);
  const scanned = scan !== null && review.text === text;
  const spans = scanned ? review.spans : [];

  useEffect(() => { setPolicyState(loadPolicy()); }, []);
  useEffect(() => {
    const ping = () => serverHealth().then((h) => setServerUp(!!h));
    ping(); setOnline(navigator.onLine);
    const on = () => { setOnline(true); ping(); }, off = () => setOnline(false);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); worker.current?.terminate(); abort.current?.abort(); };
  }, []);

  // ---- applying the policy to raw findings (also after a preset / terms change, keeping the user's decisions)
  const apply = useCallback((raw: Span[], doc: string, pol: UserPolicy, keep?: { rejected: Set<string>; manual: Span[] }) => {
    const fin = finalize(doc, raw, optionsFor(pol));
    dispatch({ type: "load", text: doc, spans: fin, rejected: keep?.rejected });
    if (keep?.manual.length) dispatch({ type: "add", spans: keep.manual });
  }, []);
  const setPolicy = useCallback((p: UserPolicy) => {
    setPolicyState(p); savePolicy(p); setStyleOverride(null);
    if (scan && review.text === text) apply(scan.raw, text, p, { rejected: rejectedKeys(review), manual: review.spans.filter((s) => s.source === "manual") });
  }, [scan, review, text, apply]);

  // ---- loading a document
  const resetDoc = (t: string, name: string) => { setText(t); setFileName(name); setScan(null); setError(null); setAttach(null); setView("review"); };
  async function onFile(f: File, includeAttachments = false) {
    setError(null);
    try {
      if (BINARY.test(f.name) || (EMAIL.test(f.name) && where === "server")) {
        if (where !== "server") throw new Error(`${f.name.split(".").pop()?.toUpperCase()} files are converted to text on the server. Switch to “On redactd servers”, or save the file as text first.`);
        if (f.size > 10_000_000) throw new Error("This file is larger than 10 MB.");
        setProgress({ stage: "Extracting text", pct: 30 });
        const r = await extractOnServer(f, includeAttachments);
        setProgress(null);
        if (r.text.length > MAX_BYTES) throw new Error(`The extracted text is ${(r.text.length / 1e6).toFixed(2)} MB; the limit is 1 MB.`);
        resetDoc(r.text, f.name);
        if (r.attachments > 0 && !r.attachments_included) setAttach({ file: f, count: r.attachments });
        return;
      }
      if (f.size > MAX_BYTES) throw new Error(`This file is ${(f.size / 1e6).toFixed(2)} MB; the limit is 1 MB.`);
      const t = await f.text();
      if (t.slice(0, 4000).includes(String.fromCharCode(0))) throw new Error("This looks like a binary file. Supported: text, CSV, JSON, XML, EML, and DOCX / PDF / MSG via the server.");
      resetDoc(t, f.name);
    } catch (e) { setProgress(null); setError(e instanceof Error ? e.message : String(e)); }
  }

  // ---- scanning
  async function runScan() {
    setError(null); setScan(null); setLeaks([]);
    const doc = text, t0 = performance.now(), opts = optionsFor(policy);
    const done = (raw: Span[], versions: Record<string, string>) => {
      setScan({ raw, ms: performance.now() - t0, versions: { ...versions, "rules (browser)": RULES_VERSION }, where, mode });
      apply(raw, doc, policy); setProgress(null);
      setAnnounce("Scan complete. Review the findings."); setTimeout(() => viewer.current?.focus(), 50);
    };
    setProgress({ stage: where === "server" ? "Sending" : "Starting", pct: 1 });
    if (where === "server") {
      abort.current = new AbortController();
      try {
        const r = await detectOnServer(doc, mode, opts, (stage, pct) => setProgress({ stage, pct }), abort.current.signal);
        done(r.spans, r.versions ?? {});
      } catch (e) {
        setProgress(null);
        if ((e as Error).name !== "AbortError") setError(navigator.onLine ? (e instanceof TypeError ? "Could not reach the redactd server. Check your connection, or switch to on-device processing." : (e as Error).message) : "You are offline. Switch to on-device processing or reconnect.");
      }
      return;
    }
    worker.current ??= new Worker(new URL("../../workers/detect.worker.ts", import.meta.url), { type: "module" });
    worker.current.onmessage = (e: MessageEvent<WorkerResponse>) => {
      const m = e.data;
      if (m.kind === "progress") setProgress({ stage: m.stage, pct: m.pct });
      else if (m.kind === "error") { setError(`On-device detection failed: ${m.message}`); setProgress(null); }
      else done(m.spans, m.versions ?? {});
    };
    worker.current.onerror = () => { setError("On-device detection could not start in this browser."); setProgress(null); };
    worker.current.postMessage({ kind: "detect", text: doc, mode, sensitivity: opts.sensitivity });
  }
  function cancel() { abort.current?.abort(); worker.current?.terminate(); worker.current = null; setProgress(null); }

  // ---- derived output
  const accepted = useMemo(() => spans.filter((s) => s.accepted), [spans]);
  const result = useMemo(() => (scanned ? render(text, accepted, style) : null), [scanned, accepted, text, style]);
  const replacements = useMemo(() => (scanned ? replacementsFor(text, spans, style) : []), [scanned, text, spans, style]);
  const sameCount = useMemo(() => { const m = new Map<string, number>(); for (const s of spans) { const v = text.slice(s.start, s.end); m.set(v, (m.get(v) ?? 0) + 1); } return m; }, [spans, text]);

  // leak check: every redacted value is searched for again in the output.
  useEffect(() => {
    if (!result) { setLeaks([]); return; }
    let cancelled = false; setLeaks(null);
    // regions of the output the user chose to keep (rejected findings) are intentional, not leaks
    const kept: [number, number][] = []; let delta = 0, k = 0;
    const acc = accepted;
    for (const s of spans) {
      if (s.accepted) { const m = result.marks[k++]; if (m) delta = m[1] - s.end; }
      else kept.push([s.start + delta, s.end + delta]);
    }
    // one pass over the output for all values (lib/redact.ts occurrencesMany); deferred so typing and clicks stay instant
    const h = setTimeout(() => { if (!cancelled) setLeaks(leakCheck(result.output, acc.map((s) => text.slice(s.start, s.end)), kept)); }, 120);
    return () => { cancelled = true; clearTimeout(h); };
  }, [result, accepted, spans, text]);

  // ---- review actions
  const dimFn = useMemo(() => (filterOn ? (s: ReviewSpan) => !(s.score !== null && s.score !== undefined && s.score < below && !(s.sources ?? []).includes("rules")) : undefined), [filterOn, below]);
  const among = useMemo(() => (dimFn ? (s: ReviewSpan) => !dimFn(s) : undefined), [dimFn]);
  const focused = review.focus >= 0 ? spans[review.focus] : undefined;
  const addSelection = () => {
    const sel = viewer.current?.selection();
    if (!sel) { setAnnounce("Select some text in the document first."); return; }
    dispatch({ type: "add", spans: [{ ...sel, type: addType, source: "manual", score: null, label: "manual", why: ["added by you"], sources: ["manual"] }] });
    window.getSelection()?.removeAllRanges(); setAnnounce(`Added as ${TYPE_INFO[addType].short}.`);
  };
  const doSearch = () => {
    const found = searchSpans(text, search ?? "", addType);
    if (found.length) { dispatch({ type: "add", spans: found }); setAnnounce(`${found.length} match${found.length === 1 ? "" : "es"} redacted as ${TYPE_INFO[addType].short}.`); setSearch(null); viewer.current?.focus(); }
    else setAnnounce("No matches.");
  };

  // ---- keyboard-first review (task D2)
  useEffect(() => {
    if (!scanned) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (typing(e.target)) { if (e.key === "Escape") { (e.target as HTMLElement).blur(); setSearch(null); viewer.current?.focus(); } return; }
      if (document.querySelector("[role=dialog]")) return;
      const k = e.key, f = review.focus;
      const act = (fn: () => void) => { e.preventDefault(); fn(); };
      if (k === "j" || k === "ArrowDown") act(() => dispatch({ type: "move", dir: 1, among }));
      else if (k === "k" || k === "ArrowUp") act(() => dispatch({ type: "move", dir: -1, among }));
      else if (k === "n") act(() => dispatch({ type: "move", dir: 1, among: (s) => s.score !== null && s.score !== undefined && s.score < below && !(s.sources ?? []).includes("rules") }));
      else if (k === "x" && f >= 0) act(() => dispatch({ type: "toggle", id: f }));
      else if (k === "X" && f >= 0) act(() => dispatch({ type: "toggleValue", id: f }));
      else if (k === "a" && focused) act(() => { dispatch({ type: "setType", piiType: focused.type, accepted: true }); setAnnounce(`All ${TYPE_INFO[focused.type].label} will be redacted.`); });
      else if (k === "A" && focused) act(() => { dispatch({ type: "setType", piiType: focused.type, accepted: false }); setAnnounce(`All ${TYPE_INFO[focused.type].label} kept.`); });
      else if (k === "u") act(() => { dispatch({ type: "undo" }); setAnnounce("Undone."); });
      else if (k === "U") act(() => { dispatch({ type: "redo" }); setAnnounce("Redone."); });
      else if (k === "/") act(() => { setSearch(""); setTimeout(() => searchBox.current?.focus(), 0); });
      else if (k === "?") act(() => setHelp(true));
      else if (k === "d") act(() => setView((v) => (v === "diff" ? "review" : "diff")));
      else if (k === "e") act(() => { exportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); exportRef.current?.querySelector<HTMLElement>("button")?.focus(); });
      else if (/^[1-9]$/.test(k) && f >= 0 && TYPES[+k - 1]) act(() => dispatch({ type: "retype", id: f, piiType: TYPES[+k - 1] }));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [scanned, review.focus, focused, among, below]);

  // ---- export
  const versions = scan?.versions ?? {};
  const report = () => buildReport({ chars: text.length, fileName, where: scan?.where ?? where, mode: scan?.mode ?? mode, ms: scan?.ms ?? null, versions, presetName: presetById(policy.presetId).name,
    style, options: optionsFor(policy), spans, leaks: leaks?.length ?? 0 });
  const strength = passwordStrength(password);
  async function downloadKey() {
    if (!result || strength.score < 1) return;
    download(`${baseName(fileName)}.redactd-key.json`, JSON.stringify(await sealVault(result.vault, password)), "application/json");
    setAnnounce("Restore key downloaded. Keep it and its password safe.");
  }
  async function copyOut() {
    if (!result) return;
    try { await navigator.clipboard.writeText(result.output); setCopied(true); setAnnounce("Redacted text copied."); setTimeout(() => setCopied(false), 2000); }
    catch { setError("Copying was blocked by the browser. Use Download instead."); }
  }
  const leakFail = !!leaks?.length;
  const step: 1 | 2 | 3 = !scanned ? 1 : leaks !== null && !leakFail && accepted.length > 0 && review.past.length > 0 ? 3 : 2;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Redact a document</h1>
          <p className="text-sm muted">Text, CSV, JSON, XML, EML, DOCX and text PDFs up to 1 MB.</p>
        </div>
        <div className="sm:ml-auto"><Steps current={step} /></div>
      </div>
      <p className="sr-only" role="status" aria-live="polite">{announce}</p>

      {/* ------------------------------------------------ 1. input */}
      <section className="card space-y-5 p-4 sm:p-5" aria-labelledby="h-input">
        <h2 id="h-input" className="sr-only">Add a document</h2>
        <div onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f); }}
          className="rounded-lg border-2 border-dashed p-3 sm:p-4" style={{ borderColor: dragging ? "var(--accent)" : "var(--border-strong)", background: dragging ? "var(--accent-soft)" : undefined }}>
          <div className="flex flex-wrap items-center gap-3">
            <label className="btn cursor-pointer">
              Choose file
              <input type="file" className="sr-only" accept=".txt,.md,.csv,.tsv,.json,.jsonl,.log,.eml,.xml,.yaml,.yml,.html,.docx,.pdf,.msg,text/*"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
            </label>
            <span className="text-sm muted">or drop a file here, or paste below</span>
            {!text && <button type="button" className="btn btn-sm sm:ml-auto" onClick={() => resetDoc(SAMPLE_TEXT, SAMPLE_NAME)}>Try the sample document</button>}
            {text && <span className="text-sm sm:ml-auto"><span className="font-medium">{fileName}</span> <span className="muted">· {text.length.toLocaleString("en")} characters</span>{" "}
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => resetDoc("", "document.txt")}>Clear</button></span>}
          </div>
          {text.length > 100_000
            ? <pre className="mono mt-3 max-h-40 overflow-hidden rounded p-2 text-xs muted" style={{ background: "var(--surface-2)" }} aria-label="Start of the document">{text.slice(0, 1500)}…</pre>
            : <>
                <label htmlFor="doc" className="sr-only">Document text</label>
                <textarea id="doc" className="input mono mt-3 h-40" placeholder="Paste a statement, email, loan note, SWIFT message, ticket…" value={text} spellCheck={false}
                  onChange={(e) => { setText(e.target.value.slice(0, MAX_BYTES)); setScan(null); }} />
              </>}
          {!text && <p className="mt-2 text-xs muted">New here? The sample is a fictional wire-recall email with names, an IBAN, a card number and an SSN. Nothing is uploaded until you press Scan.</p>}
        </div>
        {attach && (
          <div className="alert alert-info flex flex-wrap items-center gap-3" role="status">
            <span>This email has {attach.count} attachment{attach.count === 1 ? "" : "s"}. Only the file name{attach.count === 1 ? " is" : "s are"} included so far.</span>
            <button type="button" className="btn btn-sm" onClick={() => onFile(attach.file, true)}>Also read attachment contents</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAttach(null)}>No thanks</button>
          </div>
        )}

        <fieldset>
          <legend className="label">Detection</legend>
          <div role="radiogroup" aria-label="Detection mode" className="grid gap-2 sm:grid-cols-3">
            {MODES.map((m) => (
              <button key={m.id} type="button" role="radio" aria-checked={mode === m.id} className="choice" onClick={() => setMode(m.id)}>
                <div className="text-sm font-semibold">{m.name}</div><div className="text-xs muted">{m.note}</div>
              </button>
            ))}
          </div>
        </fieldset>
        <DataPanel where={where} onChange={setWhere} serverUp={serverUp} online={online} modelMb={DEVICE_MODEL_MB} />
        <PolicyPanel policy={policy} onChange={setPolicy} />

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm" htmlFor="sens">
            Sensitivity
            <input id="sens" type="range" min={0.2} max={0.9} step={0.05} value={+(1 - policy.sensitivity).toFixed(2)} onChange={(e) => setPolicyState({ ...policy, sensitivity: +(1 - +e.target.value).toFixed(2) })}
              aria-valuetext={policy.sensitivity <= 0.3 ? "catch more" : policy.sensitivity >= 0.6 ? "fewer flags" : "balanced"} />
            <span className="muted text-xs">{policy.sensitivity <= 0.3 ? "catch more" : policy.sensitivity >= 0.6 ? "fewer flags" : "balanced"}</span>
          </label>
          <button type="button" className="btn btn-primary ml-auto" disabled={!text.trim() || !!progress} onClick={runScan}>{progress ? "Scanning…" : scanned ? "Scan again" : "Scan for sensitive data"}</button>
        </div>
        {progress && <Progress pct={progress.pct} stage={progress.stage} onCancel={cancel} />}
        {error && <p className="alert alert-danger" role="alert">{error}</p>}
      </section>

      {/* ------------------------------------------------ 2. review */}
      {scanned && (
        <section aria-labelledby="h-review" className="space-y-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <h2 id="h-review" className="text-lg font-semibold">Review</h2>
            <span className="text-sm muted" data-testid="summary">{accepted.length} of {spans.length} findings will be redacted{scan ? ` · scanned in ${(scan.ms / 1000).toFixed(1)} s` : ""}</span>
            <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
              <Segmented label="View" value={view} onChange={setView} options={[{ id: "review", label: "Review" }, { id: "diff", label: "Side by side" }]} />
              <button type="button" className="btn btn-sm" onClick={() => dispatch({ type: "undo" })} disabled={!review.past.length} aria-label="Undo">Undo</button>
              <button type="button" className="btn btn-sm" onClick={() => dispatch({ type: "redo" })} disabled={!review.future.length} aria-label="Redo">Redo</button>
              <button type="button" className="btn btn-sm" onClick={() => setHelp(true)} aria-label="Keyboard shortcuts">? Shortcuts</button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <label htmlFor="addtype" className="muted">Add as</label>
            <select id="addtype" className="input w-auto" value={addType} onChange={(e) => setAddType(e.target.value as PiiType)}>
              {TYPES.map((t) => <option key={t} value={t}>{TYPE_INFO[t].label}</option>)}
            </select>
            <button type="button" className="btn btn-sm" onClick={addSelection}>Redact selection</button>
            {search === null
              ? <button type="button" className="btn btn-sm" onClick={() => { setSearch(""); setTimeout(() => searchBox.current?.focus(), 0); }}>Search and redact <span className="kbd">/</span></button>
              : <form className="flex flex-1 items-center gap-2" style={{ minWidth: 220 }} onSubmit={(e) => { e.preventDefault(); doSearch(); }}>
                  <label htmlFor="search" className="sr-only">Search the document and redact every match</label>
                  <input id="search" ref={searchBox} className="input" placeholder="Text to redact everywhere…" value={search} onChange={(e) => setSearch(e.target.value)} />
                  <button type="submit" className="btn btn-sm btn-primary" disabled={search.trim().length < 2}>Redact {search.trim().length >= 2 ? searchSpans(text, search, addType).length : 0} matches</button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSearch(null)}>Close</button>
                </form>}
          </div>
          {view === "diff" && <div className="grid grid-cols-2 text-xs font-semibold muted"><div className="px-3">Original</div><div className="px-3">Redacted output</div></div>}
          <div className="grid grid-cols-[minmax(0,1fr)] gap-3 lg:grid-cols-[minmax(0,1fr)_300px]">
            <Viewer ref={viewer} text={text} spans={spans} focus={review.focus} mode={view} replacements={replacements} hidden={hidden} dim={dimFn}
              onFocus={(id) => dispatch({ type: "focus", id })} onToggle={(id) => dispatch({ type: "toggle", id })} onToggleValue={(id) => dispatch({ type: "toggleValue", id })}
              onRetype={(id, t) => dispatch({ type: "retype", id, piiType: t })} onRemove={(id) => dispatch({ type: "remove", id })}
              sameValueCount={(id) => (spans[id] ? sameCount.get(valueOf({ text }, spans[id])) ?? 1 : 1)} />
            <div className="flex max-h-[640px] min-h-[280px] min-w-0 flex-col lg:h-[min(62vh,640px)]">
              <Sidebar text={text} spans={spans} focus={review.focus} hidden={hidden} below={below} filterOn={filterOn} onBelow={setBelow} onFilter={setFilterOn}
                onFocus={(id) => { dispatch({ type: "focus", id }); viewer.current?.scrollToSpan(id); }}
                onType={(t, on) => dispatch({ type: "setType", piiType: t, accepted: on })} onAll={(on) => dispatch({ type: "setAll", accepted: on })}
                onHide={(t) => setHidden((h) => { const n = new Set(h); if (n.has(t)) n.delete(t); else n.add(t); return n; })}
                onValue={(v, on) => dispatch({ type: "setValue", value: v, accepted: on })} />
            </div>
          </div>
          <p className="text-xs muted">Click a highlight to inspect it, click again (or press <span className="kbd">x</span>) to keep or redact it. <span className="kbd">j</span>/<span className="kbd">k</span> move between findings, <span className="kbd">/</span> searches, <span className="kbd">u</span> undoes, <span className="kbd">?</span> lists every shortcut.</p>
        </section>
      )}

      {/* ------------------------------------------------ 3. export */}
      {scanned && result && (
        <section ref={exportRef} className="card space-y-4 p-4 sm:p-5" aria-labelledby="h-export">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="h-export" className="text-lg font-semibold">Export</h2>
            <Segmented label="Output style" value={style} onChange={(s) => setStyleOverride(s)}
              options={[{ id: "placeholder", label: "Reversible [NAME_1]" }, { id: "label", label: "Labels [NAME]" }, { id: "block", label: "Blocks ████" }]} />
            <span className={`badge sm:ml-auto ${leaks === null ? "" : leakFail ? "badge-danger" : "badge-ok"}`} role="status" data-testid="leak-badge">
              {leaks === null ? "Checking output…" : leakFail ? `${leaks.length} redacted value${leaks.length === 1 ? "" : "s"} still present` : "Leak check passed"}
            </span>
          </div>
          {leakFail && <p className="alert alert-danger" role="alert">A value you are redacting still appears elsewhere in the output. Use “Search and redact” for it, or keep every occurrence, before downloading.</p>}
          <pre className="mono max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg border p-3 text-[13px] leading-6" style={{ borderColor: "var(--border)", background: "var(--surface)" }} tabIndex={0} aria-label="Redacted output preview" data-testid="output">
            {result.output.length > 20_000 ? result.output.slice(0, 20_000) + "\n… (preview shortened; the download is complete)" : result.output}
          </pre>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn btn-primary" disabled={leakFail || leaks === null} onClick={() => download(redactedName(fileName), result.output)}>Download redacted file</button>
            <button type="button" className="btn" disabled={leakFail || leaks === null} onClick={copyOut}>{copied ? "Copied ✓" : "Copy"}</button>
            <button type="button" className="btn" onClick={() => download(`${baseName(fileName)}.redaction-report.md`, reportMarkdown(report()), "text/markdown;charset=utf-8")}>Download report</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => download(`${baseName(fileName)}.redaction-report.json`, JSON.stringify(report(), null, 2), "application/json")}>report as JSON</button>
            <span className="text-xs muted">Saved as <span className="mono">{redactedName(fileName)}</span>. The report has counts only, never values.</span>
          </div>
          {style === "placeholder" && (
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
              <h3 className="text-sm font-semibold">Restore key <span className="font-normal muted">(optional)</span></h3>
              <p className="mt-1 text-xs muted">Lets you put the original values back later, for example into an AI summary of the redacted text. It is encrypted in this browser with your password. We never see the key or the password.</p>
              <div className="mt-3 flex flex-wrap items-start gap-3">
                <div className="w-full sm:w-72">
                  <label htmlFor="pw" className="sr-only">Password for the restore key</label>
                  <input id="pw" type="password" className="input" placeholder="Password (8+ characters)" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="pw-hint" />
                  <div className="mt-1 flex gap-1" aria-hidden="true">{[1, 2, 3, 4].map((i) => <span key={i} className="h-1 flex-1 rounded" style={{ background: password && strength.score >= i ? (strength.score >= 3 ? "var(--accent)" : "var(--t-date-bd)") : "var(--border)" }} />)}</div>
                  <p id="pw-hint" className="mt-1 text-xs muted" role="status">{password ? `${strength.label}. ${strength.hint}` : "Choose a password you will not lose."}</p>
                </div>
                <button type="button" className="btn" disabled={strength.score < 1 || leakFail} onClick={downloadKey}>Download restore key</button>
              </div>
              <p className="alert alert-warn mt-3 text-xs">If you lose the key file or forget its password, the original values cannot be recovered by anyone, including us.</p>
            </div>
          )}
        </section>
      )}

      {help && <ShortcutOverlay onClose={() => setHelp(false)} />}
    </div>
  );
}
