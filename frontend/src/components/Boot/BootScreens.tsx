/**
 * BootScreens — BootError and BootLoading components.
 *
 * Displayed during app boot sequence:
 * - BootLoading: App branding + loading indicator while fetching configs.
 * - BootError: Error message + "Retry" button when boot fails.
 *
 * Spec 127: FR-036, T005
 * @module components/Boot/BootScreens
 */

import type { JSX } from 'preact';
import { YenGoLogo } from '../Layout/YenGoLogo';

// ============================================================================
// BootLoading
// ============================================================================

/**
 * Loading shell shown during config fetch.
 * Renders app branding and a loading indicator to prevent blank page.
 */
export function BootLoading(): JSX.Element {
  return (
    <div
      className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-bg-primary)]"
      aria-busy="true"
      aria-label="Loading YenGo"
    >
      <YenGoLogo size={48} />
      <p className="mt-[var(--spacing-md)] text-[var(--color-text-secondary)] text-[var(--font-size-lg)]">
        Loading…
      </p>
      <div
        className="mt-[var(--spacing-sm)] w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}

// ============================================================================
// BootError
// ============================================================================

export interface BootErrorProps {
  /** Error message to display. */
  message: string;
  /** Callback to retry the boot sequence. */
  onRetry: () => void;
}

/**
 * Branded error screen shown when boot fails.
 * YenGo logo, error message, and a "Retry" button.
 */
export function BootError({ message, onRetry }: BootErrorProps): JSX.Element {
  return (
    <div
      className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-bg-primary)] p-[var(--spacing-lg)]"
    >
      <YenGoLogo size={48} />
      <p
        className="mt-[var(--spacing-md)] text-[var(--color-error)] text-[var(--font-size-base)] text-center max-w-md"
        role="alert"
      >
        {message}
      </p>
      <button
        type="button"
        className="mt-[var(--spacing-lg)] px-[var(--spacing-lg)] py-[var(--spacing-sm)] bg-[var(--color-accent)] text-[var(--color-text-inverse)] rounded-[var(--radius-md)] font-medium hover:bg-[var(--color-accent-hover)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] cursor-pointer"
        onClick={onRetry}
        autoFocus
      >
        Retry
      </button>
    </div>
  );
}
