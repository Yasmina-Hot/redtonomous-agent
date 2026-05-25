"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight, Terminal, Globe, FolderOpen, AlertCircle, CheckCircle2 } from "lucide-react";
import type { StreamEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

function ToolIcon({ name }: { name: string }) {
  if (name === "execute_command") return <Terminal size={11} />;
  if (name === "fetch_url") return <Globe size={11} />;
  if (name.includes("file") || name.includes("directory")) return <FolderOpen size={11} />;
  return <Terminal size={11} />;
}

function ToolCallCard({ event }: { event: StreamEvent & { type: "tool_call" } }) {
  const [open, setOpen] = useState(false);
  const argStr = Object.entries(event.args ?? {})
    .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 60)}`)
    .join("  ");

  return (
    <div className="tool-card my-1 animate-fade-up">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left"
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <ToolIcon name={event.name ?? ""} />
        <span className="text-[var(--accent)] font-semibold">{event.name}</span>
        {!open && (
          <span className="text-[var(--text-dim)] truncate ml-1">{argStr}</span>
        )}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
          {Object.entries(event.args ?? {}).map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="text-[var(--text-dim)] shrink-0">{k}=</span>
              <span className="text-[var(--text)] break-all">
                {typeof v === "string" ? v : JSON.stringify(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ToolResultCard({ event }: { event: StreamEvent & { type: "tool_result" } }) {
  const [open, setOpen] = useState(false);
  const isErr = event.error;

  return (
    <div
      className={cn(
        "flex items-start gap-2 py-0.5 pl-2 text-[11px] font-mono animate-fade-up",
        isErr ? "text-red-400" : "text-[var(--text-muted)]"
      )}
    >
      {isErr
        ? <AlertCircle size={11} className="mt-0.5 shrink-0 text-red-400" />
        : <CheckCircle2 size={11} className="mt-0.5 shrink-0 text-[var(--success)]" />
      }
      <button
        onClick={() => setOpen(!open)}
        className="text-left hover:text-[var(--text)] transition-colors"
      >
        <span className="text-[var(--text-dim)]">{event.name}: </span>
        {!open
          ? <span className="truncate">{(event.result ?? "").slice(0, 100)}</span>
          : <span className="break-all whitespace-pre-wrap">{event.result}</span>
        }
        {(event.result?.length ?? 0) > 100 && (
          <span className="ml-1 text-[var(--accent)]">{open ? "▲" : "▼"}</span>
        )}
      </button>
    </div>
  );
}

interface StreamingMessageProps {
  events: StreamEvent[];
  finalText: string;
  status: "streaming" | "done" | "error";
}

export function StreamingMessage({ events, finalText, status }: StreamingMessageProps) {
  return (
    <div className="space-y-1">
      {events.map((evt, i) => {
        if (evt.type === "thinking" && evt.text) {
          return (
            <p key={i} className="text-sm text-[var(--text-muted)] italic leading-relaxed">
              {evt.text}
            </p>
          );
        }
        if (evt.type === "tool_call") {
          return <ToolCallCard key={i} event={evt as StreamEvent & { type: "tool_call" }} />;
        }
        if (evt.type === "tool_result") {
          return <ToolResultCard key={i} event={evt as StreamEvent & { type: "tool_result" }} />;
        }
        if (evt.type === "error") {
          return (
            <div key={i} className="rounded border border-red-700/30 bg-red-900/10 px-3 py-2 text-sm text-red-400">
              {evt.message}
            </div>
          );
        }
        return null;
      })}

      {status === "done" && finalText && (
        <div className="mt-3 rounded border border-[var(--success)]/20 bg-[var(--success)]/5 px-3 py-2 text-sm text-[var(--text)]">
          <span className="text-[var(--success)] font-semibold">✅ Done</span>
          <p className="mt-1 leading-relaxed whitespace-pre-wrap">{finalText}</p>
        </div>
      )}

      {status === "streaming" && events.length === 0 && (
        <p className="text-sm text-[var(--text-muted)] streaming-cursor">Thinking</p>
      )}
    </div>
  );
}
