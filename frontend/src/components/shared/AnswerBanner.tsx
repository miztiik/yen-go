/**
 * AnswerBanner — Correct/Incorrect answer feedback banner.
 * @module components/shared/AnswerBanner
 *
 * Full-width stylized banners matching Yen-Go's warm design language.
 * Forward navigation (Next/Random) always accessible — never blocks the user.
 *
 * Spec 132: FR-070, FR-071, FR-072, FR-073 (US15)
 */

import type { JSX } from 'preact';

export interface AnswerBannerProps {
  /** Banner variant: success (correct) or error (incorrect) */
  variant: 'success' | 'error';
  /** Display message */
  message: string;
  /** Undo last move (error variant) */
  onUndo?: (() => void) | undefined;
  /** Reset puzzle (error variant) */
  onReset?: (() => void) | undefined;
  /** Advance to next puzzle (always accessible) */
  onNext?: (() => void) | undefined;
  /** Skip to another puzzle (always accessible) */
  onSkip?: (() => void) | undefined;
  /** Optional CSS class */
  className?: string;
}

/**
 * AnswerBanner — Displays correct/incorrect feedback with action buttons.
 * Forward navigation always remains accessible (FR-072).
 */
export function AnswerBanner({
  variant,
  message,
  onUndo,
  onReset,
  onNext,
  onSkip,
  className = '',
}: AnswerBannerProps): JSX.Element {
  const isSuccess = variant === 'success';

  const containerClass = isSuccess
    ? 'rounded-lg bg-[--color-success-bg-solid] border border-[--color-success-border] p-3 shadow-sm'
    : 'rounded-lg bg-[--color-warning-bg] border border-[--color-warning-border] p-3 shadow-sm';

  const textClass = isSuccess
    ? 'text-[--color-success-text] font-semibold'
    : 'text-[--color-warning-text] font-semibold';

  const iconPath = isSuccess
    ? 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' // checkmark circle
    : 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.999L13.732 4.001c-.77-1.333-2.694-1.333-3.464 0L3.34 16.001C2.57 17.334 3.532 19 5.072 19z'; // warning triangle

  return (
    <div className={`${containerClass} ${className}`} role="status" data-testid="answer-banner">
      <div className="flex items-center justify-between gap-3">
        {/* Icon + message */}
        <div className="flex items-center gap-2">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={textClass}
          >
            <path d={iconPath} />
          </svg>
          <span className={textClass}>{message}</span>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Error-only: undo + reset */}
          {!isSuccess && onUndo && (
            <button
              type="button"
              onClick={onUndo}
              className="rounded-md px-2 py-1 text-xs text-[--color-text-secondary] transition-colors hover:bg-[--color-bg-secondary]"
            >
              Undo
            </button>
          )}
          {!isSuccess && onReset && (
            <button
              type="button"
              onClick={onReset}
              className="rounded-md px-2 py-1 text-xs text-[--color-text-secondary] transition-colors hover:bg-[--color-bg-secondary]"
            >
              Reset
            </button>
          )}

          {/* Forward navigation — always accessible (FR-072) */}
          {onSkip && !isSuccess && (
            <button
              type="button"
              onClick={onSkip}
              className="rounded-md px-2 py-1 text-xs text-[--color-text-muted] transition-colors hover:bg-[--color-bg-secondary]"
            >
              Skip
            </button>
          )}
          {onNext && (
            <button
              type="button"
              onClick={onNext}
              className="rounded-md bg-[--color-accent] px-3 py-1.5 text-xs font-semibold text-[--color-bg-panel] transition-colors hover:opacity-90"
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default AnswerBanner;
