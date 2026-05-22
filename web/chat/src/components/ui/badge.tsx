import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "error" | "warning" | "muted";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-[var(--accent-muted)] text-[var(--accent)] border-[var(--accent)]/30",
    success: "bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/30",
    error:   "bg-red-900/20 text-red-400 border-red-700/30",
    warning: "bg-orange-900/20 text-orange-400 border-orange-700/30",
    muted:   "bg-[var(--surface-2)] text-[var(--text-muted)] border-[var(--border)]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
