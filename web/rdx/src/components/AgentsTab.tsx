"use client";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Code2, GitGraph, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

const PipelineGraph = dynamic(
  () => import("./PipelineGraph").then((m) => m.PipelineGraph),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-full text-[var(--text-dim)] text-sm">Loading graph editor…</div> }
);

const DEFAULT_YAML = `# Redtonomous pipeline config
name: "My Pipeline"
nodes:
  - id: input
    type: input
    label: "User Task"

  - id: agent1
    type: agent
    label: "Research Agent"
    model: claude-sonnet-4-6
    system_prompt: |
      You are a research assistant. Gather information about the task.

  - id: agent2
    type: agent
    label: "Builder Agent"
    model: claude-sonnet-4-6
    system_prompt: |
      You are a builder. Use the research to create the deliverable.

  - id: output
    type: output
    label: "Final Output"

edges:
  - source: input   → target: agent1
  - source: agent1  → target: agent2
  - source: agent2  → target: output
`;

type ViewMode = "graph" | "yaml" | "split";

export function AgentsTab() {
  const [view, setView] = useState<ViewMode>("split");
  const [yaml, setYaml] = useState(DEFAULT_YAML);
  const [running, setRunning] = useState(false);
  const [task, setTask] = useState("");

  const runPipeline = async () => {
    if (!task.trim()) return;
    setRunning(true);
    try {
      await fetch("http://localhost:8000/rdx/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_yaml: yaml, task }),
      });
    } catch {
      /* TODO: wire up streaming */
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)] bg-[var(--surface-2)]">
        <div className="flex rounded border border-[var(--border)] overflow-hidden">
          {(["graph", "split", "yaml"] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1 text-xs transition-colors ${
                view === v ? "bg-[var(--accent)] text-white" : "text-[var(--text-muted)] hover:bg-[var(--surface)]"
              }`}
            >
              {v === "graph" ? <><GitGraph size={11} className="inline mr-1" />Graph</> :
               v === "yaml"  ? <><Code2 size={11} className="inline mr-1" />YAML</> :
               "Split"}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <input
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Task to run through pipeline…"
          className="w-64 rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-xs text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
        />
        <Button size="sm" onClick={runPipeline} disabled={running || !task.trim()}>
          <Play size={11} /> {running ? "Running…" : "Run Pipeline"}
        </Button>
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {(view === "graph" || view === "split") && (
          <div className={view === "split" ? "flex-1 border-r border-[var(--border)]" : "flex-1"}>
            <PipelineGraph />
          </div>
        )}
        {(view === "yaml" || view === "split") && (
          <div className={view === "split" ? "w-80 shrink-0" : "flex-1"}>
            <div className="h-4 bg-[var(--surface-2)] border-b border-[var(--border)] flex items-center px-2">
              <span className="text-[9px] text-[var(--text-dim)] font-mono">pipeline.yaml</span>
            </div>
            <textarea
              value={yaml}
              onChange={(e) => setYaml(e.target.value)}
              className="w-full h-full resize-none bg-[var(--surface)] text-[var(--text)] font-mono text-xs p-3 outline-none border-none"
              style={{ height: "calc(100% - 16px)" }}
              spellCheck={false}
            />
          </div>
        )}
      </div>
    </div>
  );
}
