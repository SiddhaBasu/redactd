"use client";
import { useState } from "react";
import { restore } from "../../lib/redact";
import { isSealedVault, openVault, type SealedVault } from "../../lib/vault";

export default function RestorePage() {
  const [text, setText] = useState("");
  const [sealed, setSealed] = useState<{ key: SealedVault; name: string } | null>(null);
  const [password, setPassword] = useState("");
  const [out, setOut] = useState<{ text: string; restored: number; unknown: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);

  async function loadKey(f: File) {
    setErr(null);
    try {
      const j = JSON.parse(await f.text());
      if (!isSealedVault(j)) throw new Error();
      setSealed({ key: j, name: f.name });
    } catch { setSealed(null); setErr("That file is not a redactd restore key. Choose the .redactd-key.json file you downloaded with the redacted document."); }
  }
  async function loadDoc(f: File) { if (f.size > 5_000_000) { setErr("That file is too large."); return; } setText(await f.text()); setOut(null); }
  function onDrop(e: React.DragEvent) {
    e.preventDefault(); setDragging(false);
    for (const f of Array.from(e.dataTransfer.files)) { if (/\.json$/i.test(f.name)) loadKey(f); else loadDoc(f); }
  }
  async function run() {
    setErr(null); setBusy(true);
    try {
      const vault = await openVault(sealed!.key, password);
      const found = text.match(/\[[A-Z_]+_[0-9a-f]+\]/g) ?? [];
      setOut({ text: restore(text, vault), restored: found.filter((p) => p in vault).length, unknown: new Set(found.filter((p) => !(p in vault))).size });
    } catch { setErr("Could not unlock the key. Check the password, and that this is the key for this document."); setOut(null); }
    setBusy(false);
  }
  function save() {
    const url = URL.createObjectURL(new Blob([out!.text], { type: "text/plain;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "restored.txt" });
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Restore original values</h1>
        <p className="text-sm muted">Put the originals back into any text that still contains placeholders like [NAME_1]: the redacted file itself, or something written from it. Everything on this page happens in your browser.</p>
      </div>
      <section className="card space-y-4 p-4 sm:p-5" onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}
        style={dragging ? { borderColor: "var(--accent)", background: "var(--accent-soft)" } : undefined} aria-label="Restore">
        <ol className="space-y-4">
          <li>
            <div className="mb-1 flex flex-wrap items-center gap-3">
              <label htmlFor="rtext" className="text-sm font-semibold">1. Text with placeholders</label>
              <label className="btn btn-sm cursor-pointer">Open file<input type="file" className="sr-only" accept=".txt,.md,.csv,.json,.xml,.log,text/*" onChange={(e) => { const f = e.target.files?.[0]; if (f) loadDoc(f); e.target.value = ""; }} /></label>
            </div>
            <textarea id="rtext" className="input mono h-44" placeholder="Paste text here, or drop a file anywhere on this card…" value={text} spellCheck={false} onChange={(e) => { setText(e.target.value); setOut(null); }} />
          </li>
          <li>
            <div className="text-sm font-semibold">2. Restore key</div>
            <div className="mt-1 flex flex-wrap items-center gap-3 rounded-lg border-2 border-dashed p-3" style={{ borderColor: sealed ? "var(--accent)" : "var(--border-strong)" }}>
              <label className="btn cursor-pointer">{sealed ? "Choose a different key" : "Choose key file"}<input type="file" accept=".json,application/json" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) loadKey(f); e.target.value = ""; }} /></label>
              <span className="text-sm" role="status" data-testid="key-status">{sealed ? <><span className="badge badge-ok">Key loaded</span> <span className="mono text-xs">{sealed.name}</span>{sealed.key.entries ? <span className="muted"> · {sealed.key.entries} values</span> : null}</> : <span className="muted">or drop the .redactd-key.json file here</span>}</span>
            </div>
          </li>
          <li>
            <label htmlFor="rpw" className="text-sm font-semibold">3. Key password</label>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <input id="rpw" type="password" className="input w-full sm:w-72" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && text && sealed && password) run(); }} />
              <button type="button" className="btn btn-primary" disabled={!text || !sealed || !password || busy} onClick={run}>{busy ? "Unlocking…" : "Restore"}</button>
            </div>
          </li>
        </ol>
        {err && <p className="alert alert-danger" role="alert">{err}</p>}
        <p className="alert alert-warn text-xs">A lost key or a forgotten password cannot be recovered: the key is encrypted with your password and we never receive either.</p>
      </section>
      {out !== null && (
        <section className="card space-y-3 p-4 sm:p-5" aria-labelledby="h-restored">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="h-restored" className="text-lg font-semibold">Restored text</h2>
            <span className="badge badge-ok" role="status">{out.restored} placeholder{out.restored === 1 ? "" : "s"} restored</span>
            {out.unknown > 0 && <span className="badge badge-warn">{out.unknown} not in this key</span>}
            <span className="ml-auto flex gap-2">
              <button type="button" className="btn btn-sm" onClick={async () => { await navigator.clipboard.writeText(out.text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>{copied ? "Copied ✓" : "Copy"}</button>
              <button type="button" className="btn btn-sm" onClick={save}>Download</button>
            </span>
          </div>
          <pre className="mono max-h-[60vh] overflow-auto whitespace-pre-wrap break-words text-[13px] leading-6" tabIndex={0} aria-label="Restored text" data-testid="restored">{out.text}</pre>
        </section>
      )}
    </div>
  );
}
