"use client";
import { Dialog, Kbd } from "./ui";

export const SHORTCUTS: [string[], string][] = [
  [["j", "↓"], "Next finding"],
  [["k", "↑"], "Previous finding"],
  [["n"], "Next finding that needs review (low confidence)"],
  [["x"], "Toggle: redact or keep the focused finding"],
  [["Shift", "x"], "Toggle every occurrence of this exact value"],
  [["a"], "Redact all findings of the focused finding's type"],
  [["Shift", "a"], "Keep all findings of that type"],
  [["1", "…", "9"], "Change the focused finding's category"],
  [["/"], "Search the document and redact every match"],
  [["u"], "Undo"],
  [["Shift", "u"], "Redo"],
  [["d"], "Toggle the side-by-side diff"],
  [["e"], "Jump to export"],
  [["?"], "Show this list"],
  [["Esc"], "Close a dialog, or leave the search box"],
];

export function ShortcutOverlay({ onClose }: { onClose: () => void }) {
  return (
    <Dialog title="Keyboard shortcuts" onClose={onClose} wide>
      <p className="mb-3 text-sm muted">The whole review works without a mouse. Shortcuts are active whenever you are not typing in a field.</p>
      <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
        {SHORTCUTS.map(([keys, what]) => (
          <div key={what} className="flex items-start gap-3">
            <dt className="flex w-24 flex-none flex-wrap gap-1">{keys.map((k) => (k === "…" ? <span key={k}>…</span> : <Kbd key={k}>{k}</Kbd>))}</dt>
            <dd>{what}</dd>
          </div>
        ))}
      </dl>
    </Dialog>
  );
}
