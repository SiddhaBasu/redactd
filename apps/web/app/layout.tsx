import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "redactd — private redaction",
  description: "Redact personal and financial data in your browser. Your document never leaves your device.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b" style={{ borderColor: "var(--border)" }}>
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm">
            <Link href="/" className="text-base font-semibold tracking-tight">redactd</Link>
            <Link href="/redact" className="muted hover:underline">Redact</Link>
            <Link href="/restore" className="muted hover:underline">Restore</Link>
            <span className="ml-auto hidden text-xs muted sm:block">Runs locally · nothing is uploaded</span>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
