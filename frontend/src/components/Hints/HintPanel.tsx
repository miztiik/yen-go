/**
 * HintPanel — Component for displaying puzzle hints and solution controls.
 * @module components/Hints/HintPanel
 *
 * Contains:
 * - Hint button with tier indicator
 * - Tiered hint text display
 * - Solution reveal button
 *
 * Spec 125, Task T080
 */

import type { FunctionComponent } from 'preact';
import { HintIcon, SolutionIcon } from '../shared/icons';

// ============================================================================
// Props
// ============================================================================

export interface HintPanelProps {
  /** Number of hints revealed so far */
  hintsUsed: number;
  /** Total hints available */
  totalHints: number;
  /** Revealed hint texts */
  revealedHints: readonly string[];
  /** Whether more hints are available */
  hasMoreHints: boolean;
  /** Whether solution has been revealed */
  solutionRevealed: boolean;
  /** Request next hint callback */
  onRequestHint: () => void;
  /** Reveal solution callback */
  onRevealSolution: () => void;
  /** Disabled state */
  disabled?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

/**
 * HintPanel — Displays hint controls and revealed hints.
 *
 * Shows:
 * - "Get Hint" button with tier indicator (e.g., "1/3")
 * - "Show Solution" button
 * - List of revealed hints
 */
export const HintPanel: FunctionComponent<HintPanelProps> = ({
  hintsUsed,
  totalHints,
  revealedHints,
  hasMoreHints,
  solutionRevealed,
  onRequestHint,
  onRevealSolution,
  disabled = false,
  className,
}) => {
  const hintButtonDisabled = disabled || !hasMoreHints;
  const solutionButtonDisabled = disabled || solutionRevealed;

  return (
    <div className={`hint-panel flex flex-col gap-3 ${className ?? ''}`} data-testid="hint-panel">
      {/* Button Row */}
      <div className="flex flex-wrap gap-2">
        {/* Hint Button */}
        <button
          type="button"
          className={`flex min-h-[44px] min-w-[100px] items-center justify-center gap-1.5 rounded-lg border border-[--color-hint-border] bg-[--color-hint-bg] px-4 py-2.5 text-sm font-medium text-[--color-text-primary] transition-colors ${hintButtonDisabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
          onClick={onRequestHint}
          disabled={hintButtonDisabled}
          aria-label={`Get hint ${hintsUsed + 1} of ${totalHints}`}
          data-testid="hint-button"
        >
          <HintIcon size={14} /> Hint
          {totalHints > 0 && (
            <span className="rounded-full bg-black/10 px-1.5 py-0.5 text-xs">
              {hintsUsed}/{totalHints}
            </span>
          )}
        </button>

        {/* Solution Button */}
        <button
          type="button"
          className={`flex min-h-[44px] min-w-[100px] items-center justify-center gap-1.5 rounded-lg border border-[--color-solution-border] bg-[--color-solution-bg] px-4 py-2.5 text-sm font-medium text-[--color-text-primary] transition-colors ${solutionButtonDisabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
          onClick={onRevealSolution}
          disabled={solutionButtonDisabled}
          aria-label={solutionRevealed ? 'Solution revealed' : 'Show solution'}
          data-testid="solution-button"
        >
          {solutionRevealed ? (
            '✓ Solution Shown'
          ) : (
            <>
              <SolutionIcon size={14} /> Show Solution
            </>
          )}
        </button>
      </div>

      {/* Revealed Hints */}
      {revealedHints.length > 0 && (
        <div className="flex flex-col gap-2" data-testid="hint-list">
          {revealedHints.map((hint, index) => (
            <div
              key={index}
              className="m-0 rounded-md border-l-3 border-[--color-hint-border] bg-[--color-bg-tertiary] px-3.5 py-2.5 text-sm leading-relaxed text-[--color-text-secondary]"
              data-testid={`hint-${index + 1}`}
            >
              <span className="mb-1 block text-xs font-semibold text-[--color-hint-border]">
                Hint {index + 1}
              </span>
              {hint}
            </div>
          ))}
        </div>
      )}

      {/* No hints available message */}
      {totalHints === 0 && !solutionRevealed && (
        <p className="text-xs italic text-[--color-text-muted]">
          No hints available for this puzzle.
        </p>
      )}
    </div>
  );
};

export default HintPanel;
