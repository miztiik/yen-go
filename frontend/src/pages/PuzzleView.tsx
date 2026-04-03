/**
 * PuzzleView — Stub component for goban migration.
 * @module pages/PuzzleView
 *
 * TODO (Phase 3 - T029): Replace with goban-based PuzzleSolvePage.
 * This stub maintains backward compatibility with PuzzleSetPlayer
 * during the migration. It renders a placeholder instead of the
 * old custom board renderer.
 */

import type { FunctionComponent, JSX } from 'preact';
import type { LoadedPuzzle } from '../services/puzzleLoader';
import type { PuzzleStatus } from '../types/puzzle-internal';

/**
 * Temporary CompletionResult type — replaces deleted lib/solver/completion.
 * goban provides puzzle-correct-answer / puzzle-wrong-answer events instead.
 *
 * TODO (Phase 3): Remove this type; use goban events directly.
 */
export interface CompletionResult {
  /** Whether the puzzle was completed successfully */
  readonly isComplete: boolean;
  /** Whether the user failed the puzzle */
  readonly isFailed: boolean;
  /** Number of moves made */
  readonly moveCount: number;
  /** Number of wrong attempts (for progress tracking) */
  readonly wrongAttempts: number;
  /** Time taken in milliseconds */
  readonly timeTaken: number;
  /** Number of hints used */
  readonly hintsUsed: number;
}

/**
 * Puzzle set navigation info passed from PuzzleSetPlayer.
 */
export interface PuzzleSetNavigation {
  readonly totalPuzzles: number;
  readonly currentIndex: number;
  readonly statuses: PuzzleStatus[];
  readonly onNavigate: (index: number) => void;
  readonly currentStreak?: number;
}

export interface PuzzleViewProps {
  /** The loaded puzzle (contains raw SGF for goban to parse) */
  puzzle: LoadedPuzzle;
  /** Puzzle identifier */
  puzzleId: string;
  /** Skill level for display */
  skillLevel: string  ;
  /** Callback when puzzle is completed */
  onComplete?: (result: CompletionResult) => void;
  /** Navigate to next puzzle */
  onNextPuzzle?: () => void;
  /** Navigate to previous puzzle */
  onPrevPuzzle?: () => void;
  /** Show timer */
  showTimer?: boolean;
  /** Puzzle set navigation */
  puzzleSetNavigation?: PuzzleSetNavigation;
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    padding: 'var(--spacing-lg)',
    color: 'var(--color-text-muted)',
    gap: 'var(--spacing-md)',
  },
  title: {
    fontSize: 'var(--font-size-lg)',
    fontWeight: 'var(--font-weight-semibold)',
    color: 'var(--color-text-primary)',
  },
  subtitle: {
    fontSize: 'var(--font-size-sm)',
    color: 'var(--color-text-muted)',
  },
};

/**
 * Stub PuzzleView — renders a placeholder during goban migration.
 * Will be replaced with goban-based rendering in Phase 3 (T029-T041).
 */
export const PuzzleView: FunctionComponent<PuzzleViewProps> = ({
  puzzleId,
  skillLevel,
}) => {
  return (
    <div style={styles.container}>
      <p style={styles.title}>Puzzle: {puzzleId}</p>
      <p style={styles.subtitle}>Level: {skillLevel}</p>
      <p style={styles.subtitle}>
        goban board integration in progress — Phase 3
      </p>
    </div>
  );
};

export default PuzzleView;
