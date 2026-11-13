import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { ThemeToggle } from "../components/ui";

export const metadata: Metadata = {
  title: "redactd — private redaction for financial documents",
  description: "Find and redact personal and financial identifiers in statements, emails, SWIFT messages and tickets. Review every finding. Optionally reversible.",
};
// Pages are rendered per request so Next can stamp the CSP nonce (middleware.ts) on its bootstrap scripts.
export const dynamic = "force-dynamic";
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 btn">Skip to content</a>
        <header className="border-b" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
          <nav aria-label="Main" className="mx-auto flex max-w-6xl items-center gap-1 px-3 py-2 text-sm sm:gap-4 sm:px-4">
            <Link href="/" className="mr-2 text-base font-semibold tracking-tight">redactd</Link>
            <Link href="/redact" className="rounded px-2 py-1 hover:underline">Redact</Link>
            <Link href="/restore" className="rounded px-2 py-1 hover:underline">Restore</Link>
            <Link href="/privacy" className="rounded px-2 py-1 hover:underline">Data policy</Link>
            <span className="ml-auto"><ThemeToggle /></span>
          </nav>
        </header>
        <main id="main" className="mx-auto max-w-6xl px-3 py-6 sm:px-4 sm:py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-3 pb-8 text-xs muted sm:px-4">
          No hosted AI model ever sees your documents. Detection uses pattern rules and small open-weight models that run on our servers or in your browser.
        </footer>
      </body>
    </html>
  );
}
