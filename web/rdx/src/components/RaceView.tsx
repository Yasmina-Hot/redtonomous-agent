"use client";
import { CheckCircle2, Clock, AlertCircle, Zap } from "lucide-react";
import type { TestRun } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RaceViewProps {
  runs: TestRun[];
  providers: string[];
  testNames: string[];
}

function StatusIcon({ status }: { status: TestRun["status"] }) {
  if (status === "running") return <span className="status-dot" />;
  if (status === "done") return <CheckCircle2 size={12} className="text-[var(--success)]" />;
  if (status === "error") return <AlertCircle size={12} className="text-red-400" />;
  return <Clock size={12} className="text-[var(--text-dim)]" />;
}

export function RaceView({ runs, providers, testNames }: RaceViewProps) {
  const getRunForCell = (testName: string, provider: string): TestRun | undefined =>
    runs.find((r) => r.testName === testName && r.provider === provider);

  const getWinner = (testName: string): string | null => {
    const doneRuns = runs.filter((r) => r.testName === testName && r.status === "done");
    if (doneRuns.length === 0) return null;
    const fastest = doneRuns.reduce((a, b) => (a.durationMs ?? Infinity) < (b.durationMs ?? Infinity) ? a : b);
    return fastest.provider;
  };

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 opacity-60">
        <Zap size={32} className="text-[var(--accent)]" />
        <p className="text-sm text-[var(--text)]">Select tests and providers, then hit Run</p>
      </div>
    );
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--surface-2)]">
            <th className="text-left px-3 py-2 text-[var(--text-muted)] font-medium w-48">Test</th>
            {providers.map((p) => (
              <th key={p} className="text-left px-3 py-2 text-[var(--text-muted)] font-medium">
                <span className="font-mono">{p}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {testNames.map((name) => {
            const winner = getWinner(name);
            return (
              <tr key={name} className="border-b border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors">
                <td className="px-3 py-2 text-[var(--text)] font-medium truncate max-w-[200px]">{name}</td>
                {providers.map((p) => {
                  const run = getRunForCell(name, p);
                  const isWinner = winner === p;
                  return (
                    <td key={p} className={cn("px-3 py-2", isWinner && "bg-[var(--success)]/5")}>
                      {run ? (
                        <div>
                          <div className="flex items-center gap-1.5">
                            <StatusIcon status={run.status} />
                            {isWinner && run.status === "done" && (
                              <span className="text-[var(--success)] font-bold text-[9px]">FASTEST</span>
                            )}
                            {run.durationMs && (
                              <span className="text-[var(--text-dim)] text-[9px] ml-auto">{(run.durationMs / 1000).toFixed(1)}s</span>
                            )}
                          </div>
                          {run.status === "done" && run.output && (
                            <p className="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-2 leading-relaxed">
                              {run.output.slice(0, 120)}
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-[var(--text-dim)]">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
