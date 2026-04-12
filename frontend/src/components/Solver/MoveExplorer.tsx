/**
 * MoveExplorer — off-trunk exploration feedback.
 *
 * Detects correct/wrong/exploring moves and provides feedback:
 * - Correct: positive feedback, opponent auto-responds
 * - Wrong (with refutation): "not the solution" marker, refutation auto-plays
 * - Wrong (no refutation): "not the solution" marker, free exploration
 * - Exploring: subsequent off-trunk moves, no markers
 *
 * Spec 127: FR-037, US5, contracts/solver.ts
 * @module components/Solver/MoveExplorer
 */

import type { VNode } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface MoveResult {
  type: 'correct' | 'wrong' | 'exploring';
  isOnTrunk: boolean;
  hasRefutation: boolean;
  comment: string | null;
}

export interface MoveExplorerProps {
  /** The result of the most recent move. */
  moveResult: MoveResult | null;
  /** Whether the puzzle is currently solved. */
  isSolved?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export function MoveExplorer({ moveResult, isSolved = false }: MoveExplorerProps): VNode | null {
  if (!moveResult || isSolved) return null;

  if (moveResult.type === 'correct') {
    return (
      <div
        className="rounded-lg bg-[--color-success-bg] px-3 py-2 text-sm font-medium text-[--color-success-text] dark:bg-[--color-success-bg] dark:text-[--color-success]"
        data-component="move-explorer"
        role="status"
        aria-live="polite"
      >
        ✓ Correct!
        {moveResult.comment && <p className="mt-1 text-xs font-normal">{moveResult.comment}</p>}
      </div>
    );
  }

  if (moveResult.type === 'wrong') {
    return (
      <div
        className="rounded-lg bg-[--color-error-bg] px-3 py-2 text-sm text-[--color-error-text] dark:bg-[--color-error-bg] dark:text-[--color-error]"
        data-component="move-explorer"
        role="status"
        aria-live="polite"
      >
        <span className="font-medium">Not the solution</span>
        {moveResult.hasRefutation && (
          <p className="mt-1 text-xs">The opponent's refutation will play automatically.</p>
        )}
        {moveResult.comment && <p className="mt-1 text-xs">{moveResult.comment}</p>}
      </div>
    );
  }

  // Exploring — subtle indicator
  if (moveResult.type === 'exploring') {
    return (
      <div className="px-3 py-1 text-xs text-[--color-text-muted]" data-component="move-explorer">
        Exploring — you're off the main line
      </div>
    );
  }

  return null;
}

export default MoveExplorer;
