/**
 * PuzzleGrid - Grid display of puzzles within a skill level
 * @module components/ChallengeList/PuzzleGrid
 *
 * Covers: US2 (Browse and Select Daily Challenges)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Grid handles layout, cards handle display
 * - VI. Accessibility: Keyboard navigation, ARIA grid pattern
 */

import type { JSX } from 'preact';
import { useCallback } from 'preact/hooks';
import type { SkillLevel, PuzzleTag } from '../../types';
import { HintIcon } from '../shared/icons';

/**
 * Summary data for a puzzle in the grid
 */
export interface PuzzleGridItem {
  /** Puzzle ID */
  readonly id: string;
  /** Puzzle index within the level (1-based for display) */
  readonly index: number;
  /** Skill level */
  readonly level: SkillLevel;
  /** Whether puzzle is completed */
  readonly isCompleted: boolean;
  /** Star rating (0-3) if completed */
  readonly stars?: number;
  /** Time taken if completed (seconds) */
  readonly timeTaken?: number;
  /** Puzzle tags/categories */
  readonly tags?: readonly PuzzleTag[];
  /** Source collection */
  readonly source?: string;
  /** Number of hints used (0 = no hints) */
  readonly hintsUsed?: number;
}

/**
 * Props for PuzzleGrid component
 */
export interface PuzzleGridProps {
  /** Puzzles to display */
  readonly puzzles: readonly PuzzleGridItem[];
  /** Callback when puzzle is selected */
  readonly onSelectPuzzle: (puzzleId: string) => void;
  /** Optional columns count (auto by default) */
  readonly columns?: number;
  /** Whether to show completion badges */
  readonly showBadges?: boolean;
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Format time in seconds to display string
 */
function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

/**
 * Get color for star rating
 */
function getStarColor(stars: number): string {
  switch (stars) {
    case 3:
      return 'var(--color-medal-gold)'; // Gold
    case 2:
      return 'var(--color-medal-silver)'; // Silver
    case 1:
      return 'var(--color-medal-bronze)'; // Bronze
    default:
      return 'var(--color-border)';
  }
}

/**
 * Styles for PuzzleGrid
 */
const styles: Record<string, JSX.CSSProperties> = {
  grid: {
    display: 'grid',
    gap: '0.5rem',
    padding: '0.5rem',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0.75rem 0.5rem',
    background: 'var(--color-bg-elevated)',
    border: '1px solid var(--color-bg-secondary)',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    minHeight: '70px',
  },
  cardCompleted: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0.75rem 0.5rem',
    background: 'linear-gradient(135deg, var(--color-success-bg-solid) 0%, var(--color-bg-elevated) 100%)',
    border: '1px solid var(--color-success-border)',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    minHeight: '70px',
  },
  cardNumber: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
    lineHeight: 1,
  },
  cardNumberCompleted: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: 'var(--color-success-solid)',
    lineHeight: 1,
  },
  stars: {
    display: 'flex',
    gap: '2px',
    marginTop: '0.35rem',
  },
  star: {
    fontSize: '0.75rem',
  },
  time: {
    fontSize: '0.65rem',
    color: 'var(--color-text-muted)',
    marginTop: '0.25rem',
  },
  checkmark: {
    marginTop: '0.25rem',
  },
  hintIndicator: {
    fontSize: '0.6rem',
    color: 'var(--color-warning)',
    marginTop: '0.15rem',
  },
  empty: {
    gridColumn: '1 / -1',
    textAlign: 'center',
    padding: '2rem',
    color: 'var(--color-text-muted)',
    fontSize: '0.9rem',
  },
};

/**
 * Star display component
 */
function Stars({ count }: { count: number }): JSX.Element {
  const color = getStarColor(count);
  return (
    <div style={styles.stars}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          style={{
            ...styles.star,
            color: i <= count ? color : 'var(--color-border)',
          }}
        >
          ★
        </span>
      ))}
    </div>
  );
}

/**
 * Checkmark icon
 */
function Checkmark(): JSX.Element {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-success-solid)"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={styles.checkmark}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

/**
 * Hint indicator component
 */
function HintIndicator({ count }: { count: number }): JSX.Element {
  return (
    <span
      style={styles.hintIndicator}
      title={`${count} hint${count > 1 ? 's' : ''} used`}
      aria-label={`${count} hint${count > 1 ? 's' : ''} used`}
    >
      <HintIcon size={12} />{count}
    </span>
  );
}

/**
 * Single puzzle card in the grid
 */
interface PuzzleCardProps {
  readonly puzzle: PuzzleGridItem;
  readonly onClick: () => void;
  readonly showBadges: boolean;
}

function PuzzleCard({ puzzle, onClick, showBadges }: PuzzleCardProps): JSX.Element {
  const handleKeyDown = (e: KeyboardEvent): void => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  const cardStyle = puzzle.isCompleted ? styles.cardCompleted : styles.card;
  const numberStyle = puzzle.isCompleted ? styles.cardNumberCompleted : styles.cardNumber;

  return (
    <div
      style={cardStyle}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Puzzle ${puzzle.index}${puzzle.isCompleted ? ', completed' : ''}${puzzle.hintsUsed ? `, ${puzzle.hintsUsed} hints used` : ''}`}
    >
      <span style={numberStyle}>{puzzle.index}</span>
      {showBadges && puzzle.isCompleted && (
        <>
          {puzzle.stars !== undefined && puzzle.stars > 0 ? (
            <Stars count={puzzle.stars} />
          ) : (
            <Checkmark />
          )}
          {puzzle.hintsUsed !== undefined && puzzle.hintsUsed > 0 && (
            <HintIndicator count={puzzle.hintsUsed} />
          )}
          {puzzle.timeTaken !== undefined && (
            <span style={styles.time}>{formatTime(puzzle.timeTaken)}</span>
          )}
        </>
      )}
    </div>
  );
}

/**
 * PuzzleGrid - Displays puzzles in a responsive grid layout
 */
export function PuzzleGrid({
  puzzles,
  onSelectPuzzle,
  columns,
  showBadges = true,
  className,
}: PuzzleGridProps): JSX.Element {
  const handleSelect = useCallback(
    (puzzleId: string) => {
      onSelectPuzzle(puzzleId);
    },
    [onSelectPuzzle]
  );

  if (puzzles.length === 0) {
    return (
      <div style={styles.grid} className={className}>
        <div style={styles.empty}>No puzzles in this level.</div>
      </div>
    );
  }

  const gridStyle: JSX.CSSProperties = {
    ...styles.grid,
    gridTemplateColumns: columns
      ? `repeat(${columns}, 1fr)`
      : 'repeat(auto-fill, minmax(70px, 1fr))',
  };

  return (
    <div style={gridStyle} className={className} role="grid" aria-label="Puzzle grid">
      {puzzles.map((puzzle) => (
        <PuzzleCard
          key={puzzle.id}
          puzzle={puzzle}
          onClick={() => handleSelect(puzzle.id)}
          showBadges={showBadges}
        />
      ))}
    </div>
  );
}

export default PuzzleGrid;
