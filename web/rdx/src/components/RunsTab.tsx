"use client";
import { useState, useRef } from "react";
import { Play, Plus, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RaceView } from "./RaceView";
import type { TestRun } from "@/lib/types";

const ALL_PROVIDERS = ["claude", "openai", "gemini", "groq", "deepseek"];
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "";

interface RunsTabProps {
  selectedTestIds: string[];
  testMap: Record<string, string>;
}

export function RunsTab({ selectedTestIds, testMap }: RunsTabProps) {
  const [selectedProviders, setSelectedProviders] = useState(["claude"]);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [running, setRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const toggleProvider = (p: string) => {
    setSelectedProviders((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const startRun = async () => {
    if (selectedTestIds.length === 0 || selectedProviders.length === 0) return;
    setRunning(true);

    // Initialise all cells as pending
    const initial: TestRun[] = selectedTestIds.flatMap((tid) =>
      selectedProviders.map((provider) => ({
        id: `${tid}:${provider}`,
        testId: tid,
        testName: testMap[tid] ?? tid,
        provider,
        model: "auto",
        output: "",
        events: [],
        status: "pending" as const,
      }))
    );
    setRuns(initial);

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (TOKEN) headers["Authorization"] = `Bearer ${TOKEN}`;
    const res = await fetch(`${API}/rdx/run`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        test_ids: selectedTestIds,
        providers: selectedProviders,
      }),
    });
    const { run_id } = await res.json();

    const wsUrl = new URL(`${API.replace(/^http/, "ws")}/rdx/ws/${run_id}`);
    wsUrl.searchParams.set("test_ids", selectedTestIds.join(","));
    wsUrl.searchParams.set("providers", selectedProviders.join(","));
    if (TOKEN) wsUrl.searchParams.set("token", TOKEN);

    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      const event = JSON.parse(evt.data);

      if (event.type === "test_start") {
        setRuns((prev) =>
          prev.map((r) =>
            r.testId === event.test_id && r.provider === event.provider
              ? { ...r, status: "running", model: event.model }
              : r
          )
        );
      } else if (event.type === "test_done") {
        setRuns((prev) =>
          prev.map((r) =>
            r.testId === event.test_id && r.provider === event.provider
              ? { ...r, status: "done", output: event.output }
              : r
          )
        );
      } else if (event.type === "run_complete") {
        setRunning(false);
        ws.close();
      } else if (event.test_id && event.provider) {
        setRuns((prev) =>
          prev.map((r) =>
            r.testId === event.test_id && r.provider === event.provider
              ? { ...r, events: [...r.events, event] }
              : r
          )
        );
      }
    };

    ws.onerror = () => { setRunning(false); };
    ws.onclose = () => { setRunning(false); };
  };

  const testNames = Array.from(new Set(selectedTestIds.map((id) => testMap[id] ?? id)));

  return (
    <div className="flex flex-col h-full">
      {/* Config bar */}
      <div className="flex items-center gap-4 px-3 py-2 border-b border-[var(--border)] bg-[var(--surface-2)]">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Providers:</span>
          {ALL_PROVIDERS.map((p) => (
            <button
              key={p}
              onClick={() => toggleProvider(p)}
              className={`rounded border px-2 py-0.5 text-[10px] font-mono transition-colors ${
                selectedProviders.includes(p)
                  ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--accent)]/50"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <span className="text-[10px] text-[var(--text-muted)]">
          {selectedTestIds.length} tests × {selectedProviders.length} providers = {selectedTestIds.length * selectedProviders.length} runs
        </span>

        <Button
          size="sm"
          onClick={startRun}
          disabled={running || selectedTestIds.length === 0 || selectedProviders.length === 0}
        >
          <Play size={11} />
          {running ? "Racing…" : "⚡ Race"}
        </Button>
      </div>

      {/* Race grid */}
      <div className="flex-1 overflow-hidden">
        {selectedTestIds.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 opacity-60">
            <p className="text-sm text-[var(--text)]">No tests selected</p>
            <p className="text-xs text-[var(--text-muted)]">Check test cases in the Test Cases tab to run them here</p>
          </div>
        ) : (
          <RaceView runs={runs} providers={selectedProviders} testNames={testNames} />
        )}
      </div>
    </div>
  );
}
