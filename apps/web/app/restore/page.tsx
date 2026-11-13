"use client";
import { useState } from "react";
import { restore } from "../../lib/redact";
import { openVault, type SealedVault } from "../../lib/vault";

export default function RestorePage() {
  const [text, setText] = useState("");
  const [sealed, setSealed] = useState<SealedVault | null>(null);
  const [password, setPassword] = useState("");
  const [out, setOut] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setErr(null);
    try { setOut(restore(text, await openVault(sealed!, password))); }
    catch { setErr("Could not unlock the key — check the password and key file."); }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Restore original values</h1>
        <p className="text-sm muted">Paste text that contains placeholders like [NAME_1] (for example, an AI summary of your redacted file) and unlock your restore key. This happens in your browser.</p>
      </div>
      <section className="card space-y-4 p-5">
        <textarea className="input mono h-48" placeholder="Text with placeholders…" value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex flex-wrap items-center gap-3">
          <label className="btn cursor-pointer">
            {sealed ? "Key loaded ✓" : "Choose restore key"}
            <input type="file" accept=".json" className="hidden"
              onChange={async (e) => { const f = e.target.files?.[0]; if (f) setSealed(JSON.parse(await f.text())); }} />
          </label>
          <input type="password" className="input w-56" placeholder="Key password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button className="btn btn-primary" disabled={!text || !sealed || !password} onClick={run}>Restore</button>
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
      </section>
      {out !== null && (
        <section className="card p-5">
          <pre className="mono whitespace-pre-wrap text-sm">{out}</pre>
        </section>
      )}
    </div>
  );
}
