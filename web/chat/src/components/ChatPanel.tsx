"use client";
import { useRef, useEffect, useState, KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StreamingMessage } from "./StreamingMessage";
import { createAgentWebSocket, type AgentSocket } from "@/lib/api";
import type { ChatMessage, StreamEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  provider: string;
  model: string;
  cwd: string;
  onTokenUpdate: (tokensIn: number, tokensOut: number) => void;
  onRunningChange: (running: boolean) => void;
  onCanvasUpdate?: (event: StreamEvent) => void;
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-lg bg-[var(--accent-muted)] border border-[var(--accent)]/20 px-3 py-2 text-sm text-[var(--text)]">
        {msg.content}
      </div>
    </div>
  );
}

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex gap-3">
      <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-[10px] font-bold text-white">
        R
      </div>
      <div className="flex-1 min-w-0">
        <StreamingMessage
          events={msg.events ?? []}
          finalText={msg.content}
          status={msg.status ?? "done"}
        />
      </div>
    </div>
  );
}

export function ChatPanel({
  provider, model, cwd,
  onTokenUpdate, onRunningChange, onCanvasUpdate,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const wsRef = useRef<AgentSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const stopRun = () => {
    wsRef.current?.close();
    setIsRunning(false);
    onRunningChange(false);
    setMessages((prev) =>
      prev.map((m, i) =>
        i === prev.length - 1 && m.role === "assistant" && m.status === "streaming"
          ? { ...m, status: "done" }
          : m
      )
    );
  };

  const submit = () => {
    const task = input.trim();
    if (!task || isRunning) return;
    setInput("");

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: task,
      timestamp: Date.now(),
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      events: [],
      status: "streaming",
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsRunning(true);
    onRunningChange(true);

    let finalText = "";
    let tokensIn = 0;
    let tokensOut = 0;

    const ws = createAgentWebSocket(
      task, provider, model, cwd,
      (event) => {
        if (event.type === "done") {
          finalText = event.text ?? "";
          tokensIn = event.tokens_in ?? 0;
          tokensOut = event.tokens_out ?? 0;
        }
        if (["tool_call", "tool_result"].includes(event.type)) {
          onCanvasUpdate?.(event);
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, events: [...(m.events ?? []), event] }
              : m
          )
        );
      },
      () => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, status: "done", content: finalText, tokensIn, tokensOut }
              : m
          )
        );
        setIsRunning(false);
        onRunningChange(false);
        onTokenUpdate(tokensIn, tokensOut);
      },
    );

    wsRef.current = ws;
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message thread */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 opacity-60">
            <div className="text-6xl">⚡</div>
            <div>
              <p className="text-[var(--text)] font-semibold text-lg">Redtonomous</p>
              <p className="text-[var(--text-muted)] text-sm mt-1">
                Autonomous agent · {provider}/{model}
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {["Build a FastAPI app with JWT auth", "Write unit tests for this project", "Create a React dashboard component"].map((ex) => (
                <button
                  key={ex}
                  onClick={() => setInput(ex)}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--text)] transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) =>
          msg.role === "user"
            ? <UserMessage key={msg.id} msg={msg} />
            : <AssistantMessage key={msg.id} msg={msg} />
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoResize(); }}
            onKeyDown={handleKey}
            placeholder={`Give ${model.split("-")[0]} a task… (Enter to run, Shift+Enter for newline)`}
            rows={1}
            disabled={isRunning}
            className={cn(
              "flex-1 resize-none rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] transition-colors",
              isRunning && "opacity-50"
            )}
          />
          {isRunning ? (
            <Button variant="danger" size="icon" onClick={stopRun} title="Stop">
              <Square size={14} />
            </Button>
          ) : (
            <Button size="icon" onClick={submit} disabled={!input.trim()} title="Run (Enter)">
              <Send size={14} />
            </Button>
          )}
        </div>
        <p className="mt-1.5 text-[10px] text-[var(--text-dim)] text-right">
          Dir: <span className="text-[var(--text-muted)] font-mono">{cwd}</span>
          &nbsp;·&nbsp;
          <kbd className="bg-[var(--surface-2)] border border-[var(--border)] rounded px-1 py-0.5 text-[9px]">⌘K</kbd> palette
        </p>
      </div>
    </div>
  );
}
