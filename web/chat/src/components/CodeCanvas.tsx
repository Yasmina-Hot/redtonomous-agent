"use client";
import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

interface CodeCanvasProps {
  filePath?: string;
  cwd: string;
}

const EXT_LANG: Record<string, string> = {
  ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
  py: "python", go: "go", rs: "rust", java: "java", cs: "csharp",
  html: "html", css: "css", scss: "scss", json: "json", yaml: "yaml",
  yml: "yaml", md: "markdown", sh: "shell", bash: "shell",
  sql: "sql", php: "php", rb: "ruby", swift: "swift", kt: "kotlin",
  dockerfile: "dockerfile",
};

function detectLanguage(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const base = path.split("/").pop()?.toLowerCase() ?? "";
  if (base === "dockerfile") return "dockerfile";
  return EXT_LANG[ext] ?? "plaintext";
}

export function CodeCanvas({ filePath, cwd }: CodeCanvasProps) {
  const [code, setCode] = useState<string>("");
  const [lang, setLang] = useState("plaintext");
  const [loading, setLoading] = useState(false);
  const [displayPath, setDisplayPath] = useState("");

  useEffect(() => {
    if (!filePath) {
      setCode("// No file selected yet.\n// Files will appear here when the agent writes them.");
      setLang("plaintext");
      setDisplayPath("");
      return;
    }

    const absPath = filePath.startsWith("/") ? filePath : `${cwd}/${filePath}`;
    setDisplayPath(absPath);
    setLang(detectLanguage(filePath));
    setLoading(true);

    fetch(`http://localhost:8000/file?path=${encodeURIComponent(absPath)}`)
      .then((r) => r.text())
      .then((text) => setCode(text))
      .catch(() => setCode(`// Could not load file: ${absPath}`))
      .finally(() => setLoading(false));
  }, [filePath, cwd]);

  return (
    <div className="flex flex-col h-full">
      {displayPath && (
        <div className="flex items-center gap-2 border-b border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5">
          <span className="text-[10px] font-mono text-[var(--text-muted)] truncate">{displayPath}</span>
          {loading && <span className="text-[10px] text-[var(--accent)] animate-pulse ml-auto">loading…</span>}
        </div>
      )}
      <div className="flex-1 monaco-container">
        <Editor
          height="100%"
          language={lang}
          value={code}
          theme="vs-dark"
          options={{
            readOnly: false,
            fontSize: 12,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: "on",
            lineNumbers: "on",
            folding: true,
            automaticLayout: true,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            renderLineHighlight: "all",
            cursorBlinking: "smooth",
          }}
          onMount={(editor, monaco) => {
            monaco.editor.defineTheme("red-dark", {
              base: "vs-dark",
              inherit: true,
              rules: [],
              colors: {
                "editor.background": "#0a0a0a",
                "editor.lineHighlightBackground": "#2a151520",
                "editorLineNumber.foreground": "#444444",
                "editorLineNumber.activeForeground": "#e63946",
                "editorCursor.foreground": "#e63946",
                "editor.selectionBackground": "#e6394640",
              },
            });
            monaco.editor.setTheme("red-dark");
          }}
        />
      </div>
    </div>
  );
}
