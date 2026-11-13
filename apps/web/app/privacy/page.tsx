import Link from "next/link";

export const metadata = { title: "Data policy — redactd" };

const rows: [string, string, string][] = [
  ["Your document text", "Sent over HTTPS, held in memory while it is scanned, then discarded. Never written to disk, a database or a log.", "Never leaves the browser tab."],
  ["Findings (positions and categories)", "Returned to your browser, then discarded. Large files: held in memory for at most 10 minutes, deleted the moment your browser collects them.", "Stay in the tab."],
  ["Policy, custom terms, allow-list", "Not sent. Applied in your browser.", "Saved in this browser's local storage."],
  ["Review decisions and redacted output", "Not sent. Produced in your browser.", "Produced in your browser."],
  ["Restore key and its password", "Not sent. Encrypted in your browser (PBKDF2-SHA256, AES-256-GCM).", "Same."],
  ["Usage counts", "Size of the request, number of findings per category, timing, and a salted hash of your IP address or API key.", "Nothing is recorded."],
];

export default function Privacy() {
  return (
    <article className="max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Data policy</h1>
        <p className="mt-1 text-sm muted">What happens to your data, in plain language. The short version: we cannot show you your documents later, because we do not keep them.</p>
      </header>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Where your data goes</h2>
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">What each processing mode does with each kind of data</caption>
            <thead><tr className="border-b" style={{ borderColor: "var(--border)" }}><th scope="col" className="p-3">Data</th><th scope="col" className="p-3">On redactd servers</th><th scope="col" className="p-3">On this device only</th></tr></thead>
            <tbody>
              {rows.map(([a, b, c]) => (
                <tr key={a} className="border-b align-top last:border-0" style={{ borderColor: "var(--border)" }}><th scope="row" className="p-3 font-medium">{a}</th><td className="p-3 muted">{b}</td><td className="p-3 muted">{c}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-2 text-sm">
        <h2 className="text-lg font-semibold">What we never do</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>We never send your documents to a hosted AI model such as Claude or GPT. Detection uses pattern rules and small open-weight models that we run ourselves, or that run in your browser.</li>
          <li>We never store document text, detected values or restore keys.</li>
          <li>We never write content to logs, error messages, traces or analytics. Our logging code rejects any field that is not on a fixed list of metadata.</li>
          <li>We never use your documents to train or tune models. Training and testing use public synthetic datasets only.</li>
        </ul>
      </section>

      <section className="space-y-2 text-sm">
        <h2 className="text-lg font-semibold">Limits you should know about</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Automatic detection is not perfect. Always review the findings; use search-and-redact and custom terms for anything specific to you.</li>
          <li>Placeholders such as [NAME_1] are reversible by anyone who holds both the restore key file and its password. Keep them apart from the redacted file.</li>
          <li>If you lose the restore key or forget its password, nobody can recover the original values.</li>
          <li>Word, PDF and Outlook files are converted to text on the server. Email attachments are listed by name; their content is read only if you ask.</li>
        </ul>
      </section>
      <p><Link href="/redact" className="btn btn-primary">Back to redacting</Link></p>
    </article>
  );
}
