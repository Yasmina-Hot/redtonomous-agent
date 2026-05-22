"use client";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Code2, FileText, FolderTree, GitGraph } from "lucide-react";
import type { CanvasTab } from "@/lib/types";
import { cn } from "@/lib/utils";

const CodeCanvas    = dynamic(() => import("./CodeCanvas").then(m => m.CodeCanvas), { ssr: false, loading: () => <LoadingPane /> });
const DocCanvas     = dynamic(() => import("./DocCanvas").then(m => m.DocCanvas), { ssr: false, loading: () => <LoadingPane /> });
const FileCanvas    = dynamic(() => import("./FileCanvas").then(m => m.FileCanvas), { ssr: false, loading: () => <LoadingPane /> });
const DiagramCanvas = dynamic(() => import("./DiagramCanvas").then(m => m.DiagramCanvas), { ssr: false, loading: () => <LoadingPane /> });

function LoadingPane() {
  return (
    <div className="flex items-center justify-center h-full text-[var(--text-dim)] text-sm">
      Loading editor…
    </div>
  );
}

const TABS: { id: CanvasTab; label: string; icon: React.ReactNode }[] = [
  { id: "code",    label: "Code",    icon: <Code2 size={13} /> },
  { id: "doc",     label: "Doc",     icon: <FileText size={13} /> },
  { id: "files",   label: "Files",   icon: <FolderTree size={13} /> },
  { id: "diagram", label: "Diagram", icon: <GitGraph size={13} /> },
];

interface CanvasProps {
  cwd: string;
  lastWrittenFile?: string;
  docContent?: string;
}

export function Canvas({ cwd, lastWrittenFile, docContent }: CanvasProps) {
  const [tab, setTab] = useState<CanvasTab>("code");

  useEffect(() => {
    if (lastWrittenFile) setTab("code");
  }, [lastWrittenFile]);

  return (
    <div className="flex flex-col h-full border-l border-[var(--border)] bg-[var(--surface)]">
      {/* Tab bar */}
      <div className="flex items-center border-b border-[var(--border)] bg-[var(--surface-2)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-xs transition-colors border-b-2",
              tab === t.id
                ? "border-[var(--accent)] text-[var(--text)] bg-[var(--surface)]"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface)]"
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Canvas content */}
      <div className="flex-1 overflow-hidden">
        {tab === "code"    && <CodeCanvas filePath={lastWrittenFile} cwd={cwd} />}
        {tab === "doc"     && <DocCanvas content={docContent ?? ""} />}
        {tab === "files"   && <FileCanvas cwd={cwd} />}
        {tab === "diagram" && <DiagramCanvas />}
      </div>
    </div>
  );
}
