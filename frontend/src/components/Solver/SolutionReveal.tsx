/**
 * SolutionReveal — "Show Solution" button + "Next Move" stepper.
 *
 * Allows user to step through the trunk line one move at a time.
 * Reads C[] comments at each step. No auto-play.
 *
 * Spec 127: FR-042, US5, contracts/solver.ts
 * @module components/Solver/SolutionReveal
 */

import { useState, useCallback } from 'preact/hooks';
import type { VNode } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface SolutionRevealState {
  isRevealing: boolean;
  currentStep: number;
  totalSteps: number;
  currentComment: string | null;
}

export interface SolutionRevealProps {
  /** Total moves in the correct sequence. */
  totalSteps: number;
  /** Called to advance one trunk move via goban.showNext(). Returns the C[] comment. */
  onShowNext?: () => string | null;
  /** Called when solution reveal begins. */
  onRevealStart?: () => void;
  /** Called when solution stepping completes (reached end). */
  onRevealComplete?: () => void;
  /** Whether the puzzle is already solved. */
  isSolved?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export function SolutionReveal({
  totalSteps,
  onShowNext,
  onRevealStart,
  onRevealComplete,
}: SolutionRevealProps): VNode {
  const [state, setState] = useState<SolutionRevealState>({
    isRevealing: false,
    currentStep: 0,
    totalSteps,
    currentComment: null,
  });

  const isComplete = state.currentStep >= totalSteps;

  const startReveal = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isRevealing: true,
      currentStep: 0,
      currentComment: null,
    }));
    onRevealStart?.();
  }, [onRevealStart]);

  const nextMove = useCallback(() => {
    if (isComplete) return;

    const comment = onShowNext?.() ?? null;
    const nextStep = state.currentStep + 1;
    const done = nextStep >= totalSteps;

    setState((prev) => ({
      ...prev,
      currentStep: nextStep,
      currentComment: comment,
    }));

    if (done) {
      onRevealComplete?.();
    }
  }, [state.currentStep, totalSteps, isComplete, onShowNext, onRevealComplete]);

  // Not revealing yet — show the trigger button
  if (!state.isRevealing) {
    return (
      <div data-component="solution-reveal">
        <button
          type="button"
          onClick={startReveal}
          className="inline-flex items-center gap-1.5 rounded-[8px] bg-[var(--color-bg-secondary)] px-3 py-1.5 text-sm font-medium text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-tertiary)]"
          aria-label="Show solution"
        >
          <span>Show Solution</span>
        </button>
      </div>
    );
  }

  // Revealing — show stepper
  return (
    <div className="flex flex-col gap-2" data-component="solution-reveal">
      {/* Comment display */}
      {state.currentComment && (
        <div
          className="rounded-[12px] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
          aria-live="polite"
        >
          {state.currentComment}
        </div>
      )}

      {/* Step controls — styled stepper (not native range) */}
      <div className="flex items-center gap-3">
        {isComplete ? (
          <span className="text-sm font-medium text-[var(--color-accent)]">
            Solution complete
          </span>
        ) : (
          <button
            type="button"
            onClick={nextMove}
            aria-label={`Step ${state.currentStep + 1} of ${totalSteps}`}
            className="inline-flex items-center gap-1.5 rounded-[8px] bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-[var(--color-button-primary-text)] shadow-sm transition-colors hover:opacity-90"
          >
            Next Move
          </button>
        )}

        {/* Step indicator dots (for small sequences) or counter */}
        {totalSteps <= 6 ? (
          <div className="flex items-center gap-1">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div
                key={i}
                className={`h-2 w-2 rounded-full transition-colors ${
                  i < state.currentStep
                    ? 'bg-[var(--color-accent)]'
                    : 'bg-[var(--color-neutral-300)]'
                }`}
                aria-hidden="true"
              />
            ))}
          </div>
        ) : (
          <span className="text-xs text-[var(--color-text-muted)] tabular-nums">
            {state.currentStep} / {totalSteps}
          </span>
        )}
      </div>
    </div>
  );
}

export default SolutionReveal;
