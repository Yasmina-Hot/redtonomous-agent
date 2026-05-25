"use client";
import { useState, useEffect, useRef } from "react";
import { GitGraph, Edit3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import dynamic from "next/dynamic";

const Excalidraw = dynamic(
  () => import("@excalidraw/excalidraw").then((m) => m.Excalidraw),
  { ssr: false }
);

const DEFAULT_MERMAID = `flowchart TD
    A[Start] --> B{Agent Running?}
    B -->|Yes| C[Execute Tools]
    C --> D[Update Canvas]
    D --> B
    B -->|No| E[Done ✅]
`;

type DiagramMode = "mermaid" | "excalidraw";

export function DiagramCanvas() {
  const [mode, setMode] = useState<DiagramMode>("mermaid");
  const [mermaidSrc, setMermaidSrc] = useState(DEFAULT_MERMAID);
  const [mermaidSvg, setMermaidSvg] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (mode !== "mermaid") return;
    let cancelled = false;
    import("mermaid").then(({ default: mermaid }) => {
      mermaid.initialize({ startOnLoad: false, theme: "dark", themeVariables: { primaryColor: "#e63946", primaryTextColor: "#f0f0f0", primaryBorderColor: "#2a1515", lineColor: "#888888", background: "#0a0a0a" } });
      mermaid.render("rdx-diagram", mermaidSrc).then(({ svg }) => {
        if (!cancelled) setMermaidSvg(svg);
      }).catch(() => {
        if (!cancelled) setMermaidSvg('<p style="color:#e63946;padding:1rem">Syntax error in diagram</p>');
      });
    });
    return () => { cancelled = true; };
  }, [mermaidSrc, mode]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-[var(--border)] px-3 py-1.5 bg-[var(--surface-2)]">
        <Button
          variant={mode === "mermaid" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMode("mermaid")}
        >
          <GitGraph size={11} /> Mermaid
        </Button>
        <Button
          variant={mode === "excalidraw" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMode("excalidraw")}
        >
          <Edit3 size={11} /> Freehand
        </Button>
        {mode === "mermaid" && (
          <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setEditing(!editing)}>
            {editing ? "Preview" : "Edit src"}
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {mode === "mermaid" && (
          editing ? (
            <textarea
              value={mermaidSrc}
              onChange={(e) => setMermaidSrc(e.target.value)}
              className="w-full h-full resize-none bg-[var(--surface)] text-[var(--text)] font-mono text-xs p-3 outline-none border-none"
            />
          ) : (
            <div
              className="w-full h-full flex items-start justify-center p-4 overflow-auto"
              dangerouslySetInnerHTML={{ __html: mermaidSvg }}
            />
          )
        )}
        {mode === "excalidraw" && (
          <div className="w-full h-full">
            <Excalidraw
              theme="dark"
              UIOptions={{ canvasActions: { changeViewBackgroundColor: false } }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
