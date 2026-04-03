/**
 * PuzzleChrome — UI chrome surrounding the puzzle board.
 * @module components/Puzzle/PuzzleChrome
 *
 * Provides:
 * - Puzzle header (title, level, tags)
 * - Status indicator (correct/wrong/solving)
 * - Control buttons (reset, undo, hint, solution)
 * - Move counter
 *
 * Spec 125, Task T031
 */

import type { FunctionComponent, JSX } from 'preact';
import { useCallback } from 'preact/hooks';
import type { PuzzleStatus } from '../../hooks/usePuzzleState';
import { UndoIcon, ResetIcon, HintIcon, SolutionIcon, ChevronLeftIcon, ChevronRightIcon } from '../shared/icons';

// ============================================================================
// Props
// ============================================================================

export interface PuzzleChromeProps {
  /** Current puzzle status */
  status: PuzzleStatus;
  /** Number of player moves made */
  moveCount: number;
  /** Whether hints have been used */
  hintsUsed: boolean;
  /** Current hint tier (0 = none, 1-3 = hint level) */
  currentHintTier: number;
  /** Whether solution has been revealed */
  solutionRevealed: boolean;
  /** Optional puzzle title or ID */
  puzzleTitle?: string;
  /** Optional skill level display */
  skillLevel?: string;
  /** Optional tags */
  tags?: readonly string[];
  /** Reset callback */
  onReset?: () => void;
  /** Undo callback */
  onUndo?: () => void;
  /** Hint callback (tier: 1-3) */
  onHint?: (tier: number) => void;
  /** Show solution callback */
  onShowSolution?: () => void;
  /** Next puzzle callback */
  onNext?: () => void;
  /** Previous puzzle callback */
  onPrevious?: () => void;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '16px',
    backgroundColor: 'var(--color-bg-secondary, #f5f5f5)',
    borderRadius: 'var(--radius-lg, 8px)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  titleSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: 'var(--color-text-primary, #1a1a1a)',
    margin: 0,
  },
  level: {
    fontSize: '14px',
    color: 'var(--color-text-secondary, #666)',
  },
  tags: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  tag: {
    fontSize: '12px',
    padding: '2px 8px',
    borderRadius: '12px',
    backgroundColor: 'var(--color-bg-tertiary, #e5e5e5)',
    color: 'var(--color-text-secondary, #666)',
  },
  statusSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  statusBadge: {
    padding: '6px 12px',
    borderRadius: '16px',
    fontSize: '14px',
    fontWeight: '600',
  },
  statusSolving: {
    backgroundColor: 'var(--color-bg-tertiary, #e5e5e5)',
    color: 'var(--color-text-secondary, #666)',
  },
  statusCorrect: {
    backgroundColor: 'var(--color-success, #22c55e)',
    color: 'white',
  },
  statusWrong: {
    backgroundColor: 'var(--color-error, #ef4444)',
    color: 'white',
  },
  statusComplete: {
    backgroundColor: 'var(--color-accent, #3b82f6)',
    color: 'white',
  },
  moveCounter: {
    fontSize: '14px',
    color: 'var(--color-text-secondary, #666)',
  },
  controlsSection: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    borderTop: '1px solid var(--color-border, #e0e0e0)',
    paddingTop: '12px',
  },
  button: {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'opacity 0.2s',
    minWidth: '80px',
  },
  primaryButton: {
    backgroundColor: 'var(--color-accent, #3b82f6)',
    color: 'white',
  },
  secondaryButton: {
    backgroundColor: 'var(--color-bg-tertiary, #e5e5e5)',
    color: 'var(--color-text-primary, #1a1a1a)',
  },
  disabledButton: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  navButtons: {
    display: 'flex',
    gap: '8px',
    marginLeft: 'auto',
  },
} satisfies Record<string, JSX.CSSProperties>;

// ============================================================================
// Helpers
// ============================================================================

function getStatusDisplay(status: PuzzleStatus): { text: string; style: JSX.CSSProperties } {
  switch (status) {
    case 'loading':
      return { text: 'Loading...', style: styles.statusSolving };
    case 'solving':
      return { text: 'Your Turn', style: styles.statusSolving };
    case 'correct':
      return { text: '✓ Correct!', style: styles.statusCorrect };
    case 'wrong':
      return { text: '✗ Wrong', style: styles.statusWrong };
    case 'complete':
      return { text: '🎉 Solved!', style: styles.statusComplete };
    case 'review':
      return { text: 'Review Mode', style: styles.statusSolving };
    default:
      return { text: status, style: styles.statusSolving };
  }
}

// ============================================================================
// Component
// ============================================================================

/**
 * PuzzleChrome — UI controls and status display for puzzle solving.
 *
 * @example
 * ```tsx
 * <PuzzleChrome
 *   status={puzzleState.status}
 *   moveCount={puzzleState.moveCount}
 *   hintsUsed={puzzleState.hintsUsed}
 *   currentHintTier={puzzleState.currentHintTier}
 *   solutionRevealed={puzzleState.solutionRevealed}
 *   onReset={handleReset}
 *   onUndo={handleUndo}
 * />
 * ```
 */
export const PuzzleChrome: FunctionComponent<PuzzleChromeProps> = ({
  status,
  moveCount,
  hintsUsed,
  currentHintTier,
  solutionRevealed,
  puzzleTitle,
  skillLevel,
  tags,
  onReset,
  onUndo,
  onHint,
  onShowSolution,
  onNext,
  onPrevious,
  className,
}) => {
  const statusDisplay = getStatusDisplay(status);
  const canUndo = moveCount > 0 && status !== 'complete' && status !== 'loading';
  const canReset = moveCount > 0 && status !== 'loading';
  const canHint = !solutionRevealed && currentHintTier < 3 && status !== 'complete';
  const canShowSolution = !solutionRevealed && status !== 'loading';
  const isComplete = status === 'complete' || status === 'review';

  const handleHint = useCallback(() => {
    if (onHint && canHint) {
      onHint(currentHintTier + 1);
    }
  }, [onHint, canHint, currentHintTier]);

  return (
    <div className={className} style={styles.container}>
      {/* Header: Title, Level, Tags */}
      <div style={styles.header}>
        <div style={styles.titleSection}>
          {puzzleTitle && <h2 style={styles.title}>{puzzleTitle}</h2>}
          {skillLevel && <span style={styles.level}>{skillLevel}</span>}
          {tags && tags.length > 0 && (
            <div style={styles.tags}>
              {tags.map((tag) => (
                <span key={tag} style={styles.tag}>{tag}</span>
              ))}
            </div>
          )}
        </div>

        {/* Status and Move Counter */}
        <div style={styles.statusSection}>
          <span style={styles.moveCounter}>
            {moveCount} {moveCount === 1 ? 'move' : 'moves'}
          </span>
          <div style={{ ...styles.statusBadge, ...statusDisplay.style }}>
            {statusDisplay.text}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controlsSection}>
        {/* Undo */}
        <button
          type="button"
          onClick={onUndo}
          disabled={!canUndo}
          style={{
            ...styles.button,
            ...styles.secondaryButton,
            ...(!canUndo ? styles.disabledButton : {}),
          }}
          aria-label="Undo last move"
        >
          <UndoIcon size={14} /> Undo
        </button>

        {/* Reset */}
        <button
          type="button"
          onClick={onReset}
          disabled={!canReset}
          style={{
            ...styles.button,
            ...styles.secondaryButton,
            ...(!canReset ? styles.disabledButton : {}),
          }}
          aria-label="Reset puzzle"
        >
          <ResetIcon size={14} /> Reset
        </button>

        {/* Hint */}
        {onHint && (
          <button
            type="button"
            onClick={handleHint}
            disabled={!canHint}
            style={{
              ...styles.button,
              ...styles.secondaryButton,
              ...(!canHint ? styles.disabledButton : {}),
            }}
            aria-label={`Request hint (${3 - currentHintTier} remaining)`}
          >
            <HintIcon size={14} /> Hint {currentHintTier > 0 && `(${currentHintTier}/3)`}
          </button>
        )}

        {/* Show Solution */}
        {onShowSolution && (
          <button
            type="button"
            onClick={onShowSolution}
            disabled={!canShowSolution}
            style={{
              ...styles.button,
              ...styles.secondaryButton,
              ...(!canShowSolution ? styles.disabledButton : {}),
            }}
            aria-label="Show solution"
          >
            <SolutionIcon size={14} /> Solution
          </button>
        )}

        {/* Navigation */}
        <div style={styles.navButtons}>
          {onPrevious && (
            <button
              type="button"
              onClick={onPrevious}
              style={{ ...styles.button, ...styles.secondaryButton }}
              aria-label="Previous puzzle"
            >
              <ChevronLeftIcon size={14} /> Prev
            </button>
          )}
          {onNext && (
            <button
              type="button"
              onClick={onNext}
              style={{
                ...styles.button,
                ...(isComplete ? styles.primaryButton : styles.secondaryButton),
              }}
              aria-label="Next puzzle"
            >
              Next <ChevronRightIcon size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Hint indicator if hints used */}
      {hintsUsed && (
        <div style={{ fontSize: '12px', color: 'var(--color-text-muted, #888)' }}>
          ⓘ Hints used — this puzzle won't count as "solved cleanly"
        </div>
      )}
    </div>
  );
};

export default PuzzleChrome;
