import Link from "next/link";

const points = [
  ["Private by design", "Detection runs in your browser with small open-source models. Your file is never uploaded."],
  ["Built for financial text", "Account, card, routing, IBAN and SWIFT numbers, plus names, addresses and the context around them."],
  ["Reversible", "Swap values for placeholders like [NAME_1], process the text anywhere, then restore originals with your password-protected key."],
  ["Checked output", "Every redacted value is searched for again before download. If anything slipped through, you're told."],
];

export default function Home() {
  return (
    <div className="space-y-12">
      <section className="max-w-2xl space-y-5 pt-6">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Redact sensitive data without sending it anywhere.</h1>
        <p className="text-lg muted">
          redactd finds personal and financial identifiers in text files up to 1 MB, lets you review every finding,
          and produces a clean copy — all on your device.
        </p>
        <div className="flex gap-3">
          <Link href="/redact" className="btn btn-primary">Start redacting</Link>
          <Link href="/restore" className="btn">Restore a document</Link>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-2">
        {points.map(([t, d]) => (
          <div key={t} className="card p-5">
            <h2 className="font-medium">{t}</h2>
            <p className="mt-1 text-sm muted">{d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
