"use client";
import { useEffect, useState } from "react";
import { ExternalLink, Settings, History } from "lucide-react";
import { TabsWorkspace } from "@/components/TabsWorkspace";

export default function RdxPage() {
  const [theme, setTheme] = useState("cyberpunk");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return (
    <div className="flex flex-col h-screen">
      {/* Top navbar */}
      <header className="flex items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2 shrink-0">
        <a
          href="http://localhost:3000"
          className="flex items-center gap-2 text-[var(--accent)] font-bold text-sm hover:opacity-80 transition-opacity"
          title="Open Chat UI"
        >
          <span className="text-lg">⚡</span>
          <span className="hidden sm:inline tracking-wider">REDTONOMOUS</span>
        </a>

        <div className="h-4 w-px bg-[var(--border)]" />

        <a
          href="http://localhost:3000"
          className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] border border-[var(--border)] rounded px-1.5 py-0.5 hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors flex items-center gap-1"
        >
          CHAT <ExternalLink size={8} />
        </a>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--accent)] border border-[var(--accent)]/30 bg-[var(--accent-muted)] rounded px-1.5 py-0.5">
          RDX
        </span>

        <div className="flex-1" />

        {/* Theme selector */}
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-xs text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] cursor-pointer"
        >
          <option value="cyberpunk">Cyberpunk Dark Red</option>
          <option value="professional">Professional Dark</option>
          <option value="bold">Bold Red + Black</option>
          <option value="warm">Warm Dark</option>
        </select>

        <button className="h-7 w-7 flex items-center justify-center rounded border border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors">
          <Settings size={13} />
        </button>
      </header>

      {/* Main workspace */}
      <main className="flex-1 overflow-hidden">
        <TabsWorkspace />
      </main>

      {/* Status bar */}
      <footer className="flex items-center gap-4 border-t border-[var(--border)] bg-[var(--surface-2)] px-4 py-1.5 shrink-0">
        <span className="text-[10px] text-[var(--text-dim)]">RDX Red Testing Platform</span>
        <div className="flex-1" />
        <a href="http://localhost:8000/health" target="_blank" rel="noreferrer" className="text-[9px] text-[var(--text-dim)] hover:text-[var(--accent)] transition-colors">
          API :8000
        </a>
      </footer>
    </div>
  );
}
