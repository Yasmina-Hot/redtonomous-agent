"use client";
import { useState, useCallback, useEffect } from "react";
import { ExternalLink, LayoutTemplate, Terminal, LayoutDashboard, Layers } from "lucide-react";
import { ChatPanel } from "@/components/ChatPanel";
import { Canvas } from "@/components/Canvas";
import { ModelSelector } from "@/components/ModelSelector";
import { SettingsPanel } from "@/components/SettingsPanel";
import { SessionHistory } from "@/components/SessionHistory";
import { TokenMeter } from "@/components/TokenMeter";
import { CommandPalette } from "@/components/CommandPalette";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import type { LayoutMode, StreamEvent } from "@/lib/types";

const LAYOUT_ICONS: Record<LayoutMode, React.ReactNode> = {
  split:     <LayoutTemplate size={13} />,
  terminal:  <Terminal size={13} />,
  dashboard: <LayoutDashboard size={13} />,
  float:     <Layers size={13} />,
};
const LAYOUT_LABELS: Record<LayoutMode, string> = {
  split: "Split", terminal: "Terminal", dashboard: "Dashboard", float: "Float",
};

export default function ChatPage() {
  const [provider, setProvider] = useState("claude");
  const [model, setModel] = useState("claude-sonnet-4-6");
  const [cwd, setCwd] = useState("/tmp");
  const [layout, setLayout] = useState<LayoutMode>("split");
  const [tokensIn, setTokensIn] = useState(0);
  const [tokensOut, setTokensOut] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [lastFile, setLastFile] = useState<string | undefined>();
  const [docContent, setDocContent] = useState("");
  const [canvasOpen, setCanvasOpen] = useState(true);

  // Theme persisted to localStorage so reloads keep the user's choice.
  const [theme, setTheme] = useState("cyberpunk");
  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem("redtonomous.theme") : null;
    if (saved) setTheme(saved);
  }, []);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("redtonomous.theme", theme);
    }
  }, [theme]);

  const handleCanvasUpdate = useCallback((event: StreamEvent) => {
    if (event.type === "tool_call" && event.name === "write_file") {
      const path = event.args?.path as string | undefined;
      if (path) setLastFile(path);
      // If it's markdown, set doc content
      if (path?.endsWith(".md") && event.args?.content) {
        setDocContent(event.args.content as string);
      }
    }
  }, []);

  const handleTokenUpdate = useCallback((tIn: number, tOut: number) => {
    setTokensIn((p) => p + tIn);
    setTokensOut((p) => p + tOut);
  }, []);

  const cycleLayout = () => {
    const modes: LayoutMode[] = ["split", "terminal", "dashboard", "float"];
    const i = modes.indexOf(layout);
    setLayout(modes[(i + 1) % modes.length]);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Top navbar */}
      <header className="flex items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2 shrink-0">
        {/* Logo */}
        <a
          href="http://localhost:3001"
          className="flex items-center gap-2 text-[var(--accent)] font-bold text-sm mr-2 hover:opacity-80 transition-opacity"
          title="Open RDX Red Testing"
        >
          <span className="text-lg">⚡</span>
          <span className="hidden sm:inline tracking-wider">REDTONOMOUS</span>
        </a>

        <div className="h-4 w-px bg-[var(--border)]" />

        {/* Badges */}
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--accent)] border border-[var(--accent)]/30 bg-[var(--accent-muted)] rounded px-1.5 py-0.5">
          CHAT
        </span>
        <a
          href="http://localhost:3001"
          className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] border border-[var(--border)] rounded px-1.5 py-0.5 hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
        >
          RDX <ExternalLink size={8} />
        </a>

        <div className="flex-1" />

        {/* Layout toggle */}
        <button
          onClick={cycleLayout}
          className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
          title="Cycle layout"
          aria-label={`Cycle layout (current: ${LAYOUT_LABELS[layout]})`}
        >
          {LAYOUT_ICONS[layout]}
          <span className="hidden md:inline">{LAYOUT_LABELS[layout]}</span>
        </button>

        <div className="h-4 w-px bg-[var(--border)]" />

        {/* Model selector */}
        <ModelSelector
          provider={provider}
          model={model}
          onChange={(p, m) => { setProvider(p); setModel(m); }}
        />

        {/* Dir picker */}
        <input
          value={cwd}
          onChange={(e) => setCwd(e.target.value)}
          className="hidden md:block w-36 rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-xs font-mono text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]"
          title="Working directory"
          placeholder="/path/to/project"
        />

        {/* Token meter */}
        <TokenMeter
          tokensIn={tokensIn}
          tokensOut={tokensOut}
          provider={provider}
          isRunning={isRunning}
        />

        <div className="h-4 w-px bg-[var(--border)]" />

        {/* Actions */}
        <SessionHistory />
        <SettingsPanel />
      </header>

      {/* Main content */}
      <main className="flex flex-1 overflow-hidden">
        {/* Chat panel */}
        <div
          className={
            layout === "split"     ? "flex-1 min-w-0" :
            layout === "terminal"  ? "flex-1 min-w-0" :
            layout === "dashboard" ? "w-80 shrink-0 border-r border-[var(--border)]" :
            "flex-1 min-w-0" /* float */
          }
        >
          <ErrorBoundary>
            <ChatPanel
              provider={provider}
              model={model}
              cwd={cwd}
              onTokenUpdate={handleTokenUpdate}
              onRunningChange={setIsRunning}
              onCanvasUpdate={handleCanvasUpdate}
            />
          </ErrorBoundary>
        </div>

        {/* Canvas (split/dashboard/float only) */}
        {layout !== "terminal" && (
          <div
            className={
              layout === "split"     ? "w-[45%] shrink-0" :
              layout === "dashboard" ? "flex-1 min-w-0" :
              "w-[45%] shrink-0" /* float */
            }
          >
            <ErrorBoundary>
              <Canvas
                cwd={cwd}
                lastWrittenFile={lastFile}
                docContent={docContent}
              />
            </ErrorBoundary>
          </div>
        )}
      </main>

      {/* Status bar */}
      <footer className="flex items-center gap-4 border-t border-[var(--border)] bg-[var(--surface-2)] px-4 py-1.5 shrink-0">
        <span className="text-[10px] text-[var(--text-dim)] font-mono">
          {provider} · {model}
        </span>
        <span className="text-[10px] text-[var(--text-dim)]">·</span>
        <span className="text-[10px] text-[var(--text-dim)] font-mono truncate max-w-xs">{cwd}</span>
        <div className="flex-1" />
        <span className="text-[9px] text-[var(--text-dim)] opacity-50">
          ⌘K palette · ⌘Enter run
        </span>
      </footer>

      {/* Command palette */}
      <CommandPalette
        onSwitchModel={() => {}}
        onOpenSettings={() => {}}
        onOpenHistory={() => {}}
        onSwitchTheme={setTheme}
      />
    </div>
  );
}
