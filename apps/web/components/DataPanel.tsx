"use client";
// "Where is my data processed" (task D6): the server/device switch with a plain-language explanation of each.
import Link from "next/link";

export type Where = "server" | "device";
export function DataPanel({ where, onChange, serverUp, online, modelMb }: { where: Where; onChange: (w: Where) => void; serverUp: boolean | null; online: boolean; modelMb: number }) {
  const opts: { id: Where; title: string; lines: string[] }[] = [
    { id: "server", title: "On redactd servers", lines: ["Fastest, nothing to download.", "Sent over HTTPS, processed in memory, then discarded. Never stored, never logged, never used for training, never shown to a hosted AI model."] },
    { id: "device", title: "On this device only", lines: [modelMb ? `One-time model download (about ${modelMb} MB for this mode), then works offline.` : "No download needed for Fast mode. Works offline.", "The document never leaves this browser tab."] },
  ];
  return (
    <fieldset>
      <legend className="label">Where is my data processed?</legend>
      <div role="radiogroup" aria-label="Where to process the document" className="grid gap-2 sm:grid-cols-2">
        {opts.map((o) => (
          <button key={o.id} type="button" role="radio" aria-checked={where === o.id} className="choice" onClick={() => onChange(o.id)}>
            <div className="text-sm font-semibold">{o.title}</div>
            {o.lines.map((l) => <div key={l} className="text-xs muted">{l}</div>)}
          </button>
        ))}
      </div>
      {!online && <p className="alert alert-warn mt-2" role="status">You are offline. On-device processing still works if the model was downloaded before; server processing does not.</p>}
      {online && where === "server" && serverUp === false && (
        <p className="alert alert-warn mt-2" role="status">The redactd server is not reachable right now. <button type="button" className="link" onClick={() => onChange("device")}>Switch to on-device processing</button>.</p>
      )}
      <p className="mt-2 text-xs muted">
        In both modes your policy, custom terms, review decisions, the redacted output and the restore key are produced in this browser. We keep only usage counts (size, number of findings, timing).{" "}
        <Link href="/privacy" className="link">Read the data policy</Link>
      </p>
    </fieldset>
  );
}
