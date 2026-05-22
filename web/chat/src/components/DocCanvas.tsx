"use client";
import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { markdown } from "@codemirror/lang-markdown";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorState } from "@codemirror/state";

interface DocCanvasProps {
  content: string;
}

export function DocCanvas({ content }: DocCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const state = EditorState.create({
      doc: content || "# Document\n\nThe agent will write here...",
      extensions: [
        basicSetup,
        markdown(),
        oneDark,
        EditorView.theme({
          "&": { background: "#0a0a0a", height: "100%" },
          ".cm-scroller": { fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" },
          ".cm-cursor": { borderLeftColor: "#e63946" },
        }),
        EditorView.lineWrapping,
      ],
    });

    const view = new EditorView({ state, parent: containerRef.current });
    viewRef.current = view;

    return () => view.destroy();
  }, []);

  // Update content when prop changes
  useEffect(() => {
    const view = viewRef.current;
    if (!view || !content) return;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: content },
    });
  }, [content]);

  return <div ref={containerRef} className="h-full w-full cm-editor" />;
}
