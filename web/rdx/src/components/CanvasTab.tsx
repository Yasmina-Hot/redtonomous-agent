"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { Code2, FileText, FolderTree, GitGraph } from "lucide-react";
import { cn } from "@/lib/utils";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type CanvasTab = "code" | "doc" | "files" | "diagram";

const TABS = [
  { id: "code" as CanvasTab,    label: "Code",    icon: <Code2 size={13} /> },
  { id: "doc" as CanvasTab,     label: "Doc",     icon: <FileText size={13} /> },
  { id: "files" as CanvasTab,   label: "Files",   icon: <FolderTree size={13} /> },
  { id: "diagram" as CanvasTab, label: "Diagram", icon: <GitGraph size={13} /> },
];

interface CanvasTabProps {
  cwd: string;
  lastWrittenFile?: string;
}

export function CanvasTab({ cwd, lastWrittenFile }: CanvasTabProps) {
  const [tab, setTab] = useState<CanvasTab>("code");
  const [code] = useState("// Agent output will appear here\n");

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center border-b border-[var(--border)] bg-[var(--surface-2)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-xs transition-colors border-b-2",
              tab === t.id
                ? "border-[var(--accent)] text-[var(--text)] bg-[var(--surface)]"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text)]"
            )}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === "code" && (
          <MonacoEditor
            height="100%"
            defaultLanguage="python"
            value={code}
            theme="vs-dark"
            options={{
              fontSize: 12,
              minimap: { enabled: false },
              wordWrap: "on",
              fontFamily: "'JetBrains Mono', monospace",
              automaticLayout: true,
            }}
          />
        )}
        {tab === "doc" && (
          <textarea
            defaultValue="# Test Results\n\nAgent output will appear here as a document."
            className="w-full h-full resize-none bg-[var(--surface)] text-[var(--text)] font-mono text-xs p-4 outline-none border-none leading-relaxed"
          />
        )}
        {tab === "files" && (
          <div className="flex items-center justify-center h-full text-xs text-[var(--text-dim)]">
            Files canvas — connect a run to populate
          </div>
        )}
        {tab === "diagram" && (
          <div className="flex items-center justify-center h-full text-xs text-[var(--text-dim)]">
            Diagram canvas — run a pipeline to see output here
          </div>
        )}
      </div>
    </div>
  );
}
