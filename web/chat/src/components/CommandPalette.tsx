"use client";
import { useEffect, useState, useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Search, Cpu, FolderOpen, Palette, History } from "lucide-react";

type Action = {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut?: string;
  run: () => void;
};

interface CommandPaletteProps {
  onSwitchModel: () => void;
  onOpenSettings: () => void;
  onOpenHistory: () => void;
  onSwitchTheme: (theme: string) => void;
}

export function CommandPalette({ onSwitchModel, onOpenSettings, onOpenHistory, onSwitchTheme }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const ACTIONS: Action[] = [
    { id: "model",    label: "Switch model / provider",   icon: <Cpu size={13} />,     run: onSwitchModel },
    { id: "settings", label: "Open settings",             icon: <FolderOpen size={13} />, run: onOpenSettings },
    { id: "history",  label: "Session history",           icon: <History size={13} />,    run: onOpenHistory },
    { id: "theme-cyberpunk",    label: "Theme: Cyberpunk Dark Red",  icon: <Palette size={13} />, run: () => onSwitchTheme("cyberpunk") },
    { id: "theme-professional", label: "Theme: Professional Dark",   icon: <Palette size={13} />, run: () => onSwitchTheme("professional") },
    { id: "theme-bold",         label: "Theme: Bold Red + Black",    icon: <Palette size={13} />, run: () => onSwitchTheme("bold") },
    { id: "theme-warm",         label: "Theme: Warm Dark",           icon: <Palette size={13} />, run: () => onSwitchTheme("warm") },
  ];

  const filtered = ACTIONS.filter((a) => a.label.toLowerCase().includes(query.toLowerCase()));

  const execute = (action: Action) => {
    action.run();
    setOpen(false);
    setQuery("");
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[20vh] z-50 w-full max-w-lg -translate-x-1/2 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl overflow-hidden">
          <Dialog.Title className="sr-only">Command Palette</Dialog.Title>
          <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3">
            <Search size={15} className="text-[var(--text-muted)] shrink-0" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands…"
              className="flex-1 bg-transparent text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] outline-none"
            />
            <kbd className="text-[10px] border border-[var(--border)] rounded px-1.5 py-0.5 text-[var(--text-dim)]">Esc</kbd>
          </div>
          <div className="max-h-80 overflow-y-auto py-1">
            {filtered.map((action, i) => (
              <button
                key={action.id}
                onClick={() => execute(action)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-[var(--text-muted)] hover:bg-[var(--accent-muted)] hover:text-[var(--accent)] transition-colors"
              >
                <span className="text-[var(--text-dim)]">{action.icon}</span>
                {action.label}
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="px-4 py-6 text-center text-xs text-[var(--text-dim)]">No commands match "{query}"</p>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
