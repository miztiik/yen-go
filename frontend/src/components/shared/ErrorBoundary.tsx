/**
 * ErrorBoundary — catches render errors and displays fallback UI.
 * @module components/shared/ErrorBoundary
 *
 * Uses class component for componentDidCatch.
 * Default fallback uses design system tokens (theme-aware).
 *
 * Spec 129, T115 — FR-014
 */

import { Component } from 'preact';
import type { ComponentChildren, VNode } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface ErrorBoundaryProps {
  /** Custom fallback UI. */
  fallback?: ComponentChildren;
  /** Children to render. */
  children: ComponentChildren;
  /** Called when error is caught. */
  onError?: (error: Error, errorInfo: { componentStack?: string }) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

// ============================================================================
// Component
// ============================================================================

/** Preact class-based error boundary with theme-aware fallback UI. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack?: string }): void {
    console.error('[ErrorBoundary] Caught render error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false } as ErrorBoundaryState);
  };

  render(): ComponentChildren {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="flex flex-col items-center justify-center gap-4 rounded-lg bg-[var(--color-bg-elevated)] p-6 text-center"
          role="alert"
        >
          {/* Board-shaped empty state icon */}
          <svg
            width="48"
            height="48"
            viewBox="0 0 48 48"
            fill="none"
            aria-hidden="true"
            className="text-[var(--color-text-muted)]"
          >
            <rect
              x="4"
              y="4"
              width="40"
              height="40"
              rx="4"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
            />
            <line
              x1="4"
              y1="16"
              x2="44"
              y2="16"
              stroke="currentColor"
              strokeWidth="1"
              opacity="0.3"
            />
            <line
              x1="4"
              y1="28"
              x2="44"
              y2="28"
              stroke="currentColor"
              strokeWidth="1"
              opacity="0.3"
            />
            <line
              x1="16"
              y1="4"
              x2="16"
              y2="44"
              stroke="currentColor"
              strokeWidth="1"
              opacity="0.3"
            />
            <line
              x1="28"
              y1="4"
              x2="28"
              y2="44"
              stroke="currentColor"
              strokeWidth="1"
              opacity="0.3"
            />
          </svg>

          <p className="text-sm text-[var(--color-text-muted)]">
            Something went wrong rendering the board — try refreshing
          </p>

          <button
            type="button"
            onClick={this.handleReset}
            className="rounded-lg bg-[var(--color-bg-secondary)] px-4 py-2 text-sm text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-tertiary)]"
          >
            Try again
          </button>
        </div>
      ) as VNode;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
