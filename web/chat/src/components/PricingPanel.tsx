"use client";
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { DollarSign, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Plan {
  id: string;
  name: string;
  price_usd: number;
  period: string;
  tagline: string;
  features: string[];
  badge?: string;
  support: string;
  cli_modes: string[];
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function PricingPanel() {
  const [open, setOpen] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/plans`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => setPlans(data.plans ?? []))
      .catch((e) => setError(`Could not load plans: ${e}`));
  }, [open]);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="ghost" size="icon" title="Pricing & plans" aria-label="Open pricing">
          <DollarSign size={14} />
        </Button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[8vh] z-50 max-h-[84vh] w-[min(96vw,1100px)] -translate-x-1/2 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] sticky top-0 bg-[var(--surface)]">
            <Dialog.Title className="text-lg font-semibold text-[var(--text)]">Plans & Pricing</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close pricing">
                <X size={14} />
              </Button>
            </Dialog.Close>
          </div>

          <div className="px-6 py-5">
            {error && (
              <p className="text-xs text-red-400 mb-3">{error}</p>
            )}
            {plans.length === 0 && !error && (
              <p className="text-xs text-[var(--text-dim)]">Loading…</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {plans.map((p) => (
                <div
                  key={p.id}
                  className={`relative rounded-lg border bg-[var(--surface-2)] p-4 flex flex-col gap-3 transition-colors ${
                    p.id === "red"
                      ? "border-[var(--accent)] ring-1 ring-[var(--accent)]/40"
                      : "border-[var(--border)] hover:border-[var(--accent)]/50"
                  }`}
                >
                  {p.badge && (
                    <span className="absolute -top-2 right-3 rounded-full bg-[var(--accent)] text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 text-white">
                      {p.badge}
                    </span>
                  )}
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                      {p.name}
                    </p>
                    <p className="mt-1 text-3xl font-bold text-[var(--text)]">
                      ${p.price_usd}
                      <span className="text-xs text-[var(--text-dim)] font-normal">
                        /{p.period}
                      </span>
                    </p>
                    <p className="mt-1 text-[11px] text-[var(--text-muted)] min-h-[28px]">
                      {p.tagline}
                    </p>
                  </div>
                  <ul className="space-y-1.5 flex-1">
                    {p.features.map((f) => (
                      <li
                        key={f}
                        className="flex items-start gap-1.5 text-[11px] text-[var(--text)]"
                      >
                        <Check size={11} className="mt-0.5 shrink-0 text-[var(--accent)]" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--text-dim)]">
                      {p.support}
                    </span>
                    <Button
                      size="sm"
                      variant={p.id === "free" ? "ghost" : "default"}
                      onClick={() => {
                        // No backend purchase flow yet — surface the plan id
                        // so the user can mail-to or whatever the host wires up.
                        window.location.href = `mailto:sales@redtonomous?subject=Plan%20${encodeURIComponent(p.id)}`;
                      }}
                    >
                      {p.id === "free" ? "Current" : "Choose"}
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <p className="mt-5 text-[10px] text-[var(--text-dim)] text-center">
              Cancel anytime. Prices shown in USD. Cloud-relay sessions only —
              local CLI usage with your own keys is always free.
            </p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
