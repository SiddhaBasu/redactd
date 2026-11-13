import Link from "next/link";

const points: [string, string][] = [
  ["Built for financial text", "Account, card, routing, IBAN and SWIFT numbers with checksum validation, masked partials like ****4471, plus names, addresses and the context around them."],
  ["You review every finding", "Each finding shows its category, which detector found it, its confidence and why. Step through with the keyboard, fix in bulk, undo anything."],
  ["Reversible when you want it", "Swap values for placeholders like [NAME_1], process the text anywhere, then restore the originals with a password-encrypted key only you hold."],
  ["Checked output", "Every redacted value is searched for again before download. If one survived anywhere, the download is blocked and you are told."],
  ["Your choice of where it runs", "On our servers: in memory, never stored, never logged. Or entirely in your browser after a one-time model download."],
  ["No hosted AI in the loop", "Documents are never sent to a third-party language model. Detection is rules plus small open-weight models under Apache-2.0 / MIT licences."],
];

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="max-w-2xl space-y-5 pt-4">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">Redact financial documents without losing control of them.</h1>
        <p className="text-base muted sm:text-lg">
          redactd finds personal and sensitive identifiers in bank emails, loan notes, statements, SWIFT and FIX messages, insurance policies and support tickets,
          lets you review every finding, and exports a clean copy.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/redact" className="btn btn-primary">Start redacting</Link>
          <Link href="/restore" className="btn">Restore a document</Link>
        </div>
      </section>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="What redactd does">
        {points.map(([t, d]) => (
          <div key={t} className="card p-4">
            <h2 className="font-semibold">{t}</h2>
            <p className="mt-1 text-sm muted">{d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
