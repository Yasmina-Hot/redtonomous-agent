import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Redtonomous — Autonomous Agent UI",
  description: "Red-themed web UI for the Redtonomous autonomous coding agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="cyberpunk" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-[var(--bg)] text-[var(--text)]">
        {children}
      </body>
    </html>
  );
}
