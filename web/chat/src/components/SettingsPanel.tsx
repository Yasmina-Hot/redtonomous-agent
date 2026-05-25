"use client";
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Settings, X, Upload, Save, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { saveConfig } from "@/lib/api";

interface SettingsPanelProps {
  trigger?: React.ReactNode;
}

export function SettingsPanel({ trigger }: SettingsPanelProps) {
  const [json, setJson] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [open, setOpen] = useState(false);

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setJson(ev.target?.result as string ?? "");
      setError("");
    };
    reader.readAsText(file);
  };

  const handleSave = async () => {
    setError("");
    let parsed: unknown;
    try {
      parsed = JSON.parse(json);
    } catch {
      setError("Invalid JSON — check your config syntax.");
      return;
    }
    try {
      await saveConfig(parsed as object);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Failed to save config to backend.");
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        {trigger ?? (
          <Button variant="ghost" size="icon" title="Settings">
            <Settings size={14} />
          </Button>
        )}
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed right-0 top-0 z-50 h-full w-[480px] bg-[var(--surface)] border-l border-[var(--border)] shadow-2xl flex flex-col">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
            <div>
              <Dialog.Title className="text-sm font-semibold text-[var(--text)]">Settings</Dialog.Title>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Import config from CLI or edit manually</p>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon"><X size={14} /></Button>
            </Dialog.Close>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {/* Import section */}
            <div>
              <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Import from CLI</p>
              <p className="text-xs text-[var(--text-dim)] mb-3">
                Run <code className="bg-[var(--surface-2)] px-1 rounded font-mono">redtonomous config show</code> in your terminal, then paste the JSON below or upload the file.
              </p>
              <label className="flex items-center gap-2 cursor-pointer rounded border border-dashed border-[var(--border)] hover:border-[var(--accent)] px-4 py-3 text-xs text-[var(--text-muted)] transition-colors">
                <Upload size={13} />
                Upload config.json
                <input type="file" accept=".json" className="hidden" onChange={handleImport} />
              </label>
            </div>

            {/* JSON editor */}
            <div>
              <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Config JSON</p>
              <textarea
                value={json}
                onChange={(e) => { setJson(e.target.value); setError(""); }}
                placeholder={'{\n  "default_provider": "claude",\n  "default_model": "claude-sonnet-4-6",\n  "providers": {\n    "claude": { "api_key": "sk-ant-..." }\n  }\n}'}
                rows={16}
                className="w-full resize-none rounded border border-[var(--border)] bg-[var(--surface-2)] p-3 font-mono text-xs text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
              />
              {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
            </div>

            {/* Key reference */}
            <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">Provider key env vars (alternative)</p>
              {["CLAUDE_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"].map((k) => (
                <p key={k} className="text-[10px] font-mono text-[var(--text-dim)]">{k}</p>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[var(--border)]">
            <Dialog.Close asChild>
              <Button variant="ghost" size="sm">Cancel</Button>
            </Dialog.Close>
            <Button size="sm" onClick={handleSave} disabled={!json.trim()}>
              {saved ? <><CheckCircle size={12} /> Saved</> : <><Save size={12} /> Save Config</>}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
