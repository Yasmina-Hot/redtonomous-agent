"use client";
import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (err: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    // Surface to the browser console; in production this is where we'd hand
    // off to Sentry/Datadog/etc.
    console.error("Redtonomous UI error:", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(this.state.error, this.reset);
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 p-6 text-center">
        <div className="text-3xl">⚠️</div>
        <p className="text-sm text-[var(--text)] font-semibold">Something broke in this panel.</p>
        <p className="text-xs text-[var(--text-muted)] max-w-md font-mono">
          {this.state.error.message}
        </p>
        <button
          onClick={this.reset}
          className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs hover:border-[var(--accent)] transition-colors"
        >
          Reload panel
        </button>
      </div>
    );
  }
}
