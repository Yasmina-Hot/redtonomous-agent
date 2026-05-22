"use client";
import { formatTokens, estimateCost } from "@/lib/utils";

interface TokenMeterProps {
  tokensIn: number;
  tokensOut: number;
  provider: string;
  isRunning?: boolean;
}

export function TokenMeter({ tokensIn, tokensOut, provider, isRunning }: TokenMeterProps) {
  if (tokensIn === 0 && tokensOut === 0 && !isRunning) return null;

  return (
    <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)] font-mono">
      {isRunning && (
        <span className="flex items-center gap-1.5 text-[var(--accent)]">
          <span className="status-dot" />
          running
        </span>
      )}
      {(tokensIn > 0 || tokensOut > 0) && (
        <>
          <span title="Input tokens">↑ {formatTokens(tokensIn)}</span>
          <span className="text-[var(--text-dim)]">·</span>
          <span title="Output tokens">↓ {formatTokens(tokensOut)}</span>
          <span className="text-[var(--text-dim)]">·</span>
          <span className="text-[var(--accent)]" title="Estimated cost">
            ~{estimateCost(tokensIn, tokensOut, provider)}
          </span>
        </>
      )}
    </div>
  );
}
