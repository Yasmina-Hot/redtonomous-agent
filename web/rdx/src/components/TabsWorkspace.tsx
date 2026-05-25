"use client";
import { useState } from "react";
import { FlaskConical, GitGraph, Play, Code2 } from "lucide-react";
import { TestCasesTab } from "./TestCasesTab";
import { AgentsTab } from "./AgentsTab";
import { RunsTab } from "./RunsTab";
import dynamic from "next/dynamic";
import { cn } from "@/lib/utils";
import type { TestCase } from "@/lib/types";

const CanvasTab = dynamic(() => import("./CanvasTab").then((m) => m.CanvasTab), { ssr: false });

type Tab = "tests" | "agents" | "runs" | "canvas";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "tests",  label: "Test Cases", icon: <FlaskConical size={13} /> },
  { id: "agents", label: "Agents",     icon: <GitGraph size={13} /> },
  { id: "runs",   label: "Runs",       icon: <Play size={13} /> },
  { id: "canvas", label: "Canvas",     icon: <Code2 size={13} /> },
];

export function TabsWorkspace() {
  const [tab, setTab] = useState<Tab>("tests");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [testMap, setTestMap] = useState<Record<string, string>>({});
  const [lastWrittenFile, setLastWrittenFile] = useState<string | undefined>();

  const handleSelectionChange = (ids: string[], tests?: TestCase[]) => {
    setSelectedIds(ids);
    if (tests) {
      const map: Record<string, string> = {};
      tests.forEach((t) => { map[t.id] = t.name; });
      setTestMap((prev) => ({ ...prev, ...map }));
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tab nav */}
      <nav className="flex border-b border-[var(--border)] bg-[var(--surface-2)] shrink-0">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors",
              tab === t.id
                ? "border-[var(--accent)] text-[var(--text)] bg-[var(--surface)]"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface)]"
            )}
          >
            {t.icon}
            {t.label}
            {t.id === "tests" && selectedIds.length > 0 && (
              <span className="ml-0.5 rounded-full bg-[var(--accent)] text-white text-[9px] font-bold px-1.5 py-0.5">
                {selectedIds.length}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {tab === "tests" && (
          <TestCasesTab
            selectedIds={selectedIds}
            onSelectionChange={(ids) => handleSelectionChange(ids)}
          />
        )}
        {tab === "agents" && <AgentsTab />}
        {tab === "runs" && (
          <RunsTab selectedTestIds={selectedIds} testMap={testMap} />
        )}
        {tab === "canvas" && (
          <CanvasTab cwd="/tmp" lastWrittenFile={lastWrittenFile} />
        )}
      </div>
    </div>
  );
}
