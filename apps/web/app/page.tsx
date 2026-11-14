import Link from "next/link";

const points: [string, string][] = [
  ["Any kind of document", "Emails, contracts, clinical notes, bank statements, HR files, support tickets, chat logs, CSV and JSON exports. Tell it what the document is and it looks for that domain's identifiers too."],
  ["You review every finding", "Each finding shows its category, which detector found it, how confident it is and why. Step through with the keyboard, fix in bulk, undo anything."],
  ["Reversible when you want it", "Swap values for placeholders like [NAME_1], use the text anywhere, then put the originals back with a password-encrypted key only you hold."],
  ["Checked output", "Every redacted value is searched for again before download. If one survived anywhere, the download is blocked and you are told."],
  ["Your choice of where it runs", "On our server: in memory, never stored, never logged. Or entirely in your browser after a one-time model download."],
  ["No hosted AI in the loop", "Documents are never sent to a third-party language model. Detection is pattern rules plus small open-weight models we run ourselves."],
];

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="max-w-2xl space-y-5 pt-4">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">Remove personal data from any document, privately.</h1>
        <p className="text-base muted sm:text-lg">
          redactd finds names, contact details, ID numbers, account and card numbers, health information and the context around them,
          lets you check every finding, and gives you a clean copy.
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
