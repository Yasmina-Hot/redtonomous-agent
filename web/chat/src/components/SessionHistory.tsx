"use client";
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { History, X, ChevronRight, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchLogs, fetchLog } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import type { SessionLog, SessionLogDetail } from "@/lib/types";

export function SessionHistory() {
  const [open, setOpen] = useState(false);
  const [logs, setLogs] = useState<SessionLog[]>([]);
  const [selected, setSelected] = useState<SessionLogDetail | null>(null);

  useEffect(() => {
    if (open) {
      fetchLogs().then(setLogs).catch(() => setLogs([]));
    }
  }, [open]);

  const openLog = async (log: SessionLog) => {
    const detail = await fetchLog(log.id).catch(() => null);
    setSelected(detail);
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="ghost" size="icon" title="Session history">
          <History size={14} />
        </Button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-0 top-0 z-50 h-full w-[520px] bg-[var(--surface)] border-r border-[var(--border)] shadow-2xl flex flex-col">
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
            <Dialog.Title className="text-sm font-semibold">Session History</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon"><X size={14} /></Button>
            </Dialog.Close>
          </div>

          <div className="flex flex-1 overflow-hidden">
            {/* Log list */}
            <div className="w-52 shrink-0 border-r border-[var(--border)] overflow-y-auto">
              {logs.length === 0 ? (
                <p className="p-4 text-xs text-[var(--text-dim)] text-center">No sessions yet</p>
              ) : logs.map((log) => (
                <button
                  key={log.id}
                  onClick={() => openLog(log)}
                  className="w-full text-left px-3 py-2.5 border-b border-[var(--border)] hover:bg-[var(--surface-2)] transition-colors"
                >
                  <p className="text-xs text-[var(--text)] truncate">{log.task || "(no task)"}</p>
                  <div className="flex items-center gap-1 mt-1">
                    <Clock size={9} className="text-[var(--text-dim)]" />
                    <span className="text-[10px] text-[var(--text-muted)]">{timeAgo(log.mtime)}</span>
                    <span className="ml-auto text-[9px] text-[var(--text-dim)]">{log.steps} steps</span>
                  </div>
                  <p className="text-[9px] text-[var(--text-dim)] mt-0.5 font-mono">{log.provider}/{log.model}</p>
                </button>
              ))}
            </div>

            {/* Detail */}
            <div className="flex-1 overflow-y-auto p-3">
              {selected ? (
                <div className="space-y-3">
                  <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] p-2.5 text-xs space-y-1">
                    <p><span className="text-[var(--text-muted)]">Task:</span> <span className="text-[var(--text)]">{selected.task}</span></p>
                    <p><span className="text-[var(--text-muted)]">Model:</span> <span className="font-mono">{selected.provider}/{selected.model}</span></p>
                    <p><span className="text-[var(--text-muted)]">Dir:</span> <span className="font-mono">{selected.cwd}</span></p>
                  </div>
                  <div className="space-y-1.5">
                    {selected.log.map((step, i) => (
                      <div key={i} className="tool-card text-[10px]">
                        <div className="flex items-center gap-2">
                          <span className="text-[var(--text-dim)]">#{step.iter}</span>
                          <span className="text-[var(--accent)]">{step.tool}</span>
                          {step.error && <span className="text-red-400 ml-auto">✗ error</span>}
                        </div>
                        <p className="text-[var(--text-muted)] mt-1 truncate">{step.result}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-[var(--text-dim)]">
                  Select a session to inspect
                </div>
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
