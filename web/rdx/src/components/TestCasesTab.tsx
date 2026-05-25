"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, Save, Tag, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { TestCase } from "@/lib/types";

const API = "http://localhost:8000";

const SCORING_OPTIONS = [
  { value: "llm",    label: "LLM-as-judge",    desc: "AI scores the output against a rubric" },
  { value: "exact",  label: "Exact match",      desc: "Output must contain the expected string" },
  { value: "regex",  label: "Regex pattern",    desc: "Output must match a regex" },
  { value: "custom", label: "Custom function",  desc: "JavaScript scoring function" },
] as const;

function TestEditor({ test, onSave, onCancel }: { test: Partial<TestCase>; onSave: (t: TestCase) => void; onCancel: () => void }) {
  const [form, setForm] = useState<Partial<TestCase>>(test);
  const upd = (k: keyof TestCase, v: unknown) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="flex flex-col gap-3 p-4">
      <div>
        <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">Name</label>
        <input
          value={form.name ?? ""}
          onChange={(e) => upd("name", e.target.value)}
          placeholder="e.g. Builds FastAPI app"
          className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
        />
      </div>

      <div>
        <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">Prompt (task for agent)</label>
        <textarea
          value={form.prompt ?? ""}
          onChange={(e) => upd("prompt", e.target.value)}
          rows={4}
          placeholder="Build a FastAPI app with JWT auth and a /users endpoint"
          className="mt-1 w-full resize-none rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
        />
      </div>

      <div>
        <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">Scoring method</label>
        <div className="mt-1 grid grid-cols-2 gap-1.5">
          {SCORING_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => upd("scoring", opt.value)}
              className={`rounded border px-2 py-1.5 text-left transition-colors ${
                form.scoring === opt.value
                  ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)] hover:border-[var(--accent)]/50"
              }`}
            >
              <p className="text-xs font-medium">{opt.label}</p>
              <p className="text-[10px] text-[var(--text-dim)] mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {form.scoring === "llm" && (
        <div>
          <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">Scoring rubric</label>
          <textarea
            value={form.rubric ?? ""}
            onChange={(e) => upd("rubric", e.target.value)}
            rows={3}
            placeholder="The output should contain working Python code that starts a FastAPI server. Deduct points for missing imports or syntax errors."
            className="mt-1 w-full resize-none rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>
      )}

      {(form.scoring === "exact" || form.scoring === "regex") && (
        <div>
          <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">
            {form.scoring === "exact" ? "Expected string (must be contained in output)" : "Regex pattern"}
          </label>
          <input
            value={form.expected ?? ""}
            onChange={(e) => upd("expected", e.target.value)}
            placeholder={form.scoring === "exact" ? "from fastapi import FastAPI" : "def .+\\(.*\\):"}
            className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-sm font-mono text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>
      )}

      <div>
        <label className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-semibold">Suite</label>
        <input
          value={form.suite ?? "default"}
          onChange={(e) => upd("suite", e.target.value)}
          placeholder="default"
          className="mt-1 w-full rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--accent)]"
        />
      </div>

      <div className="flex items-center justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => onSave(form as TestCase)} disabled={!form.name || !form.prompt}>
          <Save size={12} /> Save Test
        </Button>
      </div>
    </div>
  );
}

interface TestCasesTabProps {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

export function TestCasesTab({ selectedIds, onSelectionChange }: TestCasesTabProps) {
  const [tests, setTests] = useState<TestCase[]>([]);
  const [editing, setEditing] = useState<Partial<TestCase> | null>(null);

  const loadTests = () =>
    fetch(`${API}/rdx/tests`).then((r) => r.json()).then(setTests).catch(() => {});

  useEffect(() => { loadTests(); }, []);

  const saveTest = async (t: TestCase) => {
    if (t.id) {
      await fetch(`${API}/rdx/tests/${t.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(t) });
    } else {
      await fetch(`${API}/rdx/tests`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(t) });
    }
    setEditing(null);
    loadTests();
  };

  const deleteTest = async (id: string) => {
    await fetch(`${API}/rdx/tests/${id}`, { method: "DELETE" });
    onSelectionChange(selectedIds.filter((s) => s !== id));
    loadTests();
  };

  const toggleSelect = (id: string) => {
    onSelectionChange(
      selectedIds.includes(id) ? selectedIds.filter((s) => s !== id) : [...selectedIds, id]
    );
  };

  if (editing !== null) {
    return <TestEditor test={editing} onSave={saveTest} onCancel={() => setEditing(null)} />;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
        <span className="text-xs text-[var(--text-muted)]">{tests.length} tests · {selectedIds.length} selected</span>
        <Button size="sm" onClick={() => setEditing({ scoring: "llm", suite: "default", tags: [] })}>
          <Plus size={12} /> New Test
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center opacity-60">
            <FlaskConical size={32} className="text-[var(--accent)]" />
            <p className="text-sm text-[var(--text)]">No test cases yet</p>
            <p className="text-xs text-[var(--text-muted)]">Create your first test to get started</p>
          </div>
        ) : tests.map((t) => (
          <div
            key={t.id}
            className={`flex items-start gap-3 border-b border-[var(--border)] px-3 py-2.5 cursor-pointer transition-colors ${
              selectedIds.includes(t.id)
                ? "bg-[var(--accent-muted)] border-l-2 border-l-[var(--accent)]"
                : "hover:bg-[var(--surface-2)]"
            }`}
            onClick={() => toggleSelect(t.id)}
          >
            <input
              type="checkbox"
              checked={selectedIds.includes(t.id)}
              onChange={() => toggleSelect(t.id)}
              className="mt-1 accent-[var(--accent)]"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--text)] truncate">{t.name}</p>
              <p className="text-[10px] text-[var(--text-muted)] truncate mt-0.5">{t.prompt}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[9px] font-mono border border-[var(--border)] rounded px-1 text-[var(--text-dim)]">{t.scoring}</span>
                <span className="text-[9px] text-[var(--text-dim)]">{t.suite}</span>
                {t.tags?.map((tag) => (
                  <span key={tag} className="text-[9px] text-[var(--accent)]">#{tag}</span>
                ))}
              </div>
            </div>
            <div className="flex gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); setEditing(t); }}
                className="h-6 w-6 flex items-center justify-center rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--surface-2)] transition-colors"
              >
                <Tag size={11} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); deleteTest(t.id); }}
                className="h-6 w-6 flex items-center justify-center rounded text-[var(--text-dim)] hover:text-red-400 hover:bg-red-900/10 transition-colors"
              >
                <Trash2 size={11} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
