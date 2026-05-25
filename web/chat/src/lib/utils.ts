import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function estimateCost(tokensIn: number, tokensOut: number, provider: string): string {
  const rates: Record<string, [number, number]> = {
    claude: [0.000003, 0.000015],
    openai: [0.0000025, 0.00001],
    groq: [0.0000001, 0.0000001],
    gemini: [0.00000015, 0.0000006],
  };
  const [inRate, outRate] = rates[provider] ?? [0.000003, 0.000015];
  const cost = tokensIn * inRate + tokensOut * outRate;
  if (cost < 0.001) return `<$0.001`;
  return `$${cost.toFixed(3)}`;
}

export function timeAgo(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
