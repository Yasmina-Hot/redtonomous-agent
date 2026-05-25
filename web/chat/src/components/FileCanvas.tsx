"use client";
import { useEffect, useState } from "react";
import { Folder, FileText, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileEntry {
  name: string;
  path: string;
  type: "file" | "dir";
  size?: number;
}

interface FileCanvasProps {
  cwd: string;
}

export function FileCanvas({ cwd }: FileCanvasProps) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [selected, setSelected] = useState<FileEntry | null>(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);

  const loadDir = (path: string) => {
    setLoading(true);
    fetch(`http://localhost:8000/files?path=${encodeURIComponent(path)}`)
      .then((r) => r.json())
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadDir(cwd); }, [cwd]);

  const openEntry = (entry: FileEntry) => {
    setSelected(entry);
    if (entry.type === "dir") {
      loadDir(entry.path);
    } else {
      fetch(`http://localhost:8000/file?path=${encodeURIComponent(entry.path)}`)
        .then((r) => r.text())
        .then(setPreview)
        .catch(() => setPreview("Could not load file."));
    }
  };

  return (
    <div className="flex h-full">
      {/* File tree */}
      <div className="w-56 shrink-0 border-r border-[var(--border)] overflow-y-auto">
        <div className="flex items-center justify-between px-2 py-1.5 border-b border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-muted)] font-mono truncate">{cwd}</span>
          <Button variant="ghost" size="icon" onClick={() => loadDir(cwd)} className="h-5 w-5">
            <RefreshCw size={10} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
        {entries.map((e) => (
          <button
            key={e.path}
            onClick={() => openEntry(e)}
            className={`flex w-full items-center gap-1.5 px-3 py-1 text-xs text-left transition-colors ${
              selected?.path === e.path
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            }`}
          >
            {e.type === "dir"
              ? <Folder size={11} className="text-[var(--accent)] shrink-0" />
              : <FileText size={11} className="shrink-0" />
            }
            <span className="truncate font-mono">{e.name}</span>
          </button>
        ))}
        {entries.length === 0 && !loading && (
          <p className="px-3 py-4 text-[11px] text-[var(--text-dim)] text-center">Empty directory</p>
        )}
      </div>

      {/* Preview */}
      <div className="flex-1 overflow-auto bg-[var(--surface)]">
        {selected && selected.type === "file" ? (
          <pre className="p-3 text-[11px] font-mono text-[var(--text-muted)] whitespace-pre-wrap break-all leading-relaxed">
            {preview || "Loading…"}
          </pre>
        ) : (
          <div className="flex items-center justify-center h-full text-[var(--text-dim)] text-xs">
            Select a file to preview
          </div>
        )}
      </div>
    </div>
  );
}
