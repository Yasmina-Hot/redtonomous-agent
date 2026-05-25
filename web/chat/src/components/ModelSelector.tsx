"use client";
import { useEffect, useState } from "react";
import * as Select from "@radix-ui/react-select";
import { ChevronDown, Cpu } from "lucide-react";
import { fetchModels } from "@/lib/api";
import type { KnownModel } from "@/lib/types";

interface ModelSelectorProps {
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
}

export function ModelSelector({ provider, model, onChange }: ModelSelectorProps) {
  const [models, setModels] = useState<KnownModel[]>([]);

  useEffect(() => {
    fetchModels().then(setModels).catch(() => setModels([]));
  }, []);

  const grouped = models.reduce<Record<string, KnownModel[]>>((acc, m) => {
    (acc[m.provider] ??= []).push(m);
    return acc;
  }, {});

  const current = `${provider}/${model}`;

  return (
    <Select.Root
      value={current}
      onValueChange={(v) => {
        const [p, ...rest] = v.split("/");
        onChange(p, rest.join("/"));
      }}
    >
      <Select.Trigger className="flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--text)] transition-colors outline-none max-w-[200px]">
        <Cpu size={11} className="text-[var(--accent)] shrink-0" />
        <Select.Value>
          <span className="truncate">{model}</span>
        </Select.Value>
        <ChevronDown size={11} className="ml-auto shrink-0" />
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          className="z-50 min-w-[260px] max-h-[400px] overflow-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-2xl text-sm"
          position="popper"
          sideOffset={4}
        >
          <Select.Viewport className="p-1">
            {Object.entries(grouped).map(([prov, mlist]) => (
              <Select.Group key={prov}>
                <Select.Label className="px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-dim)]">
                  {prov}
                </Select.Label>
                {mlist.map((m) => (
                  <Select.Item
                    key={`${m.provider}/${m.model}`}
                    value={`${m.provider}/${m.model}`}
                    className="flex items-center gap-2 rounded px-2 py-1.5 text-xs text-[var(--text-muted)] cursor-pointer hover:bg-[var(--accent-muted)] hover:text-[var(--accent)] outline-none data-[highlighted]:bg-[var(--accent-muted)] data-[highlighted]:text-[var(--accent)]"
                  >
                    <Select.ItemText>
                      <span className="font-mono">{m.model}</span>
                    </Select.ItemText>
                  </Select.Item>
                ))}
                <Select.Separator className="my-1 h-px bg-[var(--border)]" />
              </Select.Group>
            ))}
            {models.length === 0 && (
              <div className="px-3 py-4 text-center text-xs text-[var(--text-muted)]">
                Backend offline — models unavailable
              </div>
            )}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
