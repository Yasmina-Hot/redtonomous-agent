"use client";
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        default: "bg-[var(--accent)] text-white hover:bg-[var(--accent)]/80 glow-sm",
        ghost:   "hover:bg-[var(--accent-muted)] hover:text-[var(--accent)]",
        outline: "border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--accent-muted)]",
        surface: "bg-[var(--surface-2)] hover:bg-[var(--surface-2)]/80",
        danger:  "bg-red-900/30 border border-red-700 text-red-400 hover:bg-red-900/50",
        success: "bg-[var(--success)]/10 border border-[var(--success)]/30 text-[var(--success)] hover:bg-[var(--success)]/20",
      },
      size: {
        sm: "h-7 px-3 text-xs",
        md: "h-8 px-4",
        lg: "h-10 px-6 text-base",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
