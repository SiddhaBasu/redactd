"use client";
// Policies and custom terms (task D4). Terms are stored in this browser only and applied on the device.
import { useState } from "react";
import { PRESETS, parseTerms, type UserPolicy } from "../lib/presets";
import { Switch } from "./ui";

export function PolicyPanel({ policy, onChange, compact }: { policy: UserPolicy; onChange: (p: UserPolicy) => void; compact?: boolean }) {
  const [custom, setCustom] = useState(policy.customTerms.join("\n")), [allow, setAllow] = useState(policy.allowTerms.join("\n"));
  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="label">Policy</legend>
        <div role="radiogroup" aria-label="Policy preset" className={`grid gap-2 ${compact ? "" : "sm:grid-cols-2 lg:grid-cols-4"}`}>
          {PRESETS.map((p) => (
            <button key={p.id} type="button" role="radio" aria-checked={policy.presetId === p.id} className="choice" onClick={() => onChange({ ...policy, presetId: p.id })}>
              <div className="text-sm font-semibold">{p.name}</div>
              <div className="text-xs muted">{p.summary}</div>
            </button>
          ))}
        </div>
      </fieldset>
      <Switch checked={policy.keepLast4} onChange={(v) => onChange({ ...policy, keepLast4: v })} label="Keep last 4 digits"
        hint="Leaves the last four digits of long account and card numbers visible, and leaves already-masked numbers like ****4471 alone." />
      <details className="rounded-lg border p-3" style={{ borderColor: "var(--border)" }} open={!compact && (policy.customTerms.length > 0 || policy.allowTerms.length > 0)}>
        <summary className="cursor-pointer text-sm font-semibold">Custom terms and allow-list{policy.customTerms.length + policy.allowTerms.length ? ` (${policy.customTerms.length + policy.allowTerms.length})` : ""}</summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="custom-terms">Always redact</label>
            <textarea id="custom-terms" className="input mono h-24" placeholder={"Project Falcon\ninternal code names…"} value={custom}
              onChange={(e) => { setCustom(e.target.value); onChange({ ...policy, customTerms: parseTerms(e.target.value) }); }} />
          </div>
          <div>
            <label className="label" htmlFor="allow-terms">Never redact</label>
            <textarea id="allow-terms" className="input mono h-24" placeholder={"Your own company name\npublic product names…"} value={allow}
              onChange={(e) => { setAllow(e.target.value); onChange({ ...policy, allowTerms: parseTerms(e.target.value) }); }} />
          </div>
        </div>
        <p className="mt-2 text-xs muted">One term per line. Saved in this browser only and applied on your device: these lists are never sent to our servers or written to logs.</p>
      </details>
    </div>
  );
}
