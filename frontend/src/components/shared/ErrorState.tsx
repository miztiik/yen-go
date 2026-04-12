/**
 * ErrorState — Friendly error display with retry action and technical details disclosure.
 * @module components/shared/ErrorState
 *
 * Replaces raw error messages with human-friendly display:
 * - Icon + message (always visible)
 * - Retry button (primary)
 * - Go Back link (secondary)
 * - Technical details in <details> disclosure (hidden by default)
 *
 * Spec 132, T091
 */

import type { FunctionalComponent, ComponentChildren } from 'preact';

export interface ErrorStateProps {
  /** Human-readable error message */
  message: string;
  /** Icon element or identifier */
  icon?: ComponentChildren;
  /** Primary action — "Retry" button */
  onRetry?: (() => void) | undefined;
  /** Secondary action — "Go Back" button/link */
  onGoBack?: (() => void) | undefined;
  /** Raw technical error for disclosure section */
  details?: string | undefined;
  /** Whether details disclosure is initially open */
  detailsOpen?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Test data attribute */
  testId?: string;
}

/**
 * ErrorState — Displays a friendly error with optional retry and technical details.
 */
export const ErrorState: FunctionalComponent<ErrorStateProps> = ({
  message,
  icon = (
    <svg
      width="36"
      height="36"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-warning, #f59e0b)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.999L13.732 4.001c-.77-1.333-2.694-1.333-3.464 0L3.34 16.001C2.57 17.334 3.532 19 5.072 19z" />
    </svg>
  ),
  onRetry,
  onGoBack,
  details,
  detailsOpen = false,
  className,
  testId = 'error-state',
}) => {
  return (
    <div
      className={`flex min-h-[200px] flex-col items-center justify-center gap-4 p-8 text-center ${className ?? ''}`}
      data-testid={testId}
      role="alert"
    >
      {/* Icon */}
      <div className="text-4xl" aria-hidden="true">
        {icon}
      </div>

      {/* Message */}
      <p className="m-0 max-w-[400px] text-base text-[var(--color-text-primary)]">{message}</p>

      {/* Actions */}
      {(onRetry || onGoBack) && (
        <div className="flex items-center gap-3">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-[var(--color-bg-panel)] transition-colors hover:opacity-90 min-h-[44px]"
              data-testid={`${testId}-retry`}
            >
              Retry
            </button>
          )}
          {onGoBack && (
            <button
              type="button"
              onClick={onGoBack}
              className="rounded-lg px-4 py-2 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)] min-h-[44px]"
              data-testid={`${testId}-back`}
            >
              Go Back
            </button>
          )}
        </div>
      )}

      {/* Technical details disclosure */}
      {details && (
        <details
          className="mt-2 w-full max-w-[400px] text-left"
          open={detailsOpen}
          data-testid={`${testId}-details`}
        >
          <summary className="cursor-pointer text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]">
            Technical details
          </summary>
          <pre className="mt-2 overflow-auto rounded-md bg-[var(--color-bg-secondary)] p-3 text-xs text-[var(--color-text-muted)]">
            {details}
          </pre>
        </details>
      )}
    </div>
  );
};

export default ErrorState;
