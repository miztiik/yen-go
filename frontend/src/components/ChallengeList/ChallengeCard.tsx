/**
 * ChallengeCard - Card component for a single daily challenge
 * @module components/ChallengeList/ChallengeCard
 *
 * Covers: US2 (Browse and Select Daily Challenges)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Presentational component only
 * - VI. Accessibility: Keyboard navigation, ARIA labels
 */

import type { JSX } from 'preact';
import { LEVEL_SLUGS, type LevelSlug } from '../../lib/levels/config';
import { LockStatus } from './LockStatus';

/**
 * Data for rendering a challenge card
 */
export interface ChallengeCardData {
  /** Challenge ID */
  readonly id: string;
  /** Formatted display date */
  readonly displayDate: string;
  /** Total puzzles in challenge */
  readonly totalPuzzles: number;
  /** Puzzles completed by user */
  readonly completedPuzzles: number;
  /** Whether challenge is unlocked */
  readonly isUnlocked: boolean;
  /** Whether this is today's challenge */
  readonly isToday: boolean;
  /** Puzzles per skill level */
  readonly puzzlesByLevel: Readonly<Record<LevelSlug, number>>;
}

/**
 * Props for ChallengeCard component
 */
export interface ChallengeCardProps {
  /** Card data */
  readonly data: ChallengeCardData;
  /** Whether this card is selected */
  readonly isSelected?: boolean;
  /** Callback when card is clicked/selected */
  readonly onSelect: (id: string) => void;
}

/**
 * Get progress percentage
 */
function getProgressPercent(completed: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((completed / total) * 100);
}

/**
 * Get status text for the card
 */
function getStatusText(data: ChallengeCardData): string {
  if (!data.isUnlocked) return 'Locked';
  if (data.completedPuzzles === 0) return 'Not started';
  if (data.completedPuzzles >= data.totalPuzzles) return 'Complete!';
  return `${data.completedPuzzles}/${data.totalPuzzles}`;
}

/**
 * Get status color
 */
function getStatusColor(data: ChallengeCardData): string {
  if (!data.isUnlocked) return 'var(--color-accent-muted)';
  if (data.completedPuzzles >= data.totalPuzzles) return 'var(--color-success-solid)';
  if (data.completedPuzzles > 0) return 'var(--color-accent)';
  return 'var(--color-text-muted)';
}

/**
 * Styles for ChallengeCard component
 */
const baseCardStyle: JSX.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: '1rem',
  borderRadius: '8px',
  border: '1px solid var(--color-border)',
  background: 'var(--color-bg-elevated)',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  position: 'relative',
  overflow: 'hidden',
};

const styles: Record<string, JSX.CSSProperties> = {
  card: baseCardStyle,
  cardSelected: {
    ...baseCardStyle,
    borderColor: 'var(--color-accent)',
    boxShadow: '0 2px 8px rgba(201, 166, 107, 0.3)',
  },
  cardLocked: {
    ...baseCardStyle,
    opacity: 0.7,
    cursor: 'not-allowed',
  },
  cardToday: {
    ...baseCardStyle,
    borderColor: 'var(--color-success-solid)',
    borderWidth: '2px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '0.5rem',
  },
  dateContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  date: {
    fontSize: '1rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
    margin: 0,
  },
  todayBadge: {
    fontSize: '0.65rem',
    fontWeight: '600',
    color: 'var(--color-success-solid)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  lockContainer: {
    flexShrink: 0,
  },
  progressSection: {
    marginTop: '0.5rem',
  },
  progressBar: {
    height: '4px',
    background: 'var(--color-bg-secondary)',
    borderRadius: '2px',
    overflow: 'hidden',
    marginBottom: '0.5rem',
  },
  progressFill: {
    height: '100%',
    background: 'var(--color-accent)',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  progressFillComplete: {
    height: '100%',
    background: 'var(--color-success-solid)',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  status: {
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  puzzleCount: {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
  },
  levelDots: {
    display: 'flex',
    gap: '3px',
    marginTop: '0.5rem',
  },
  levelDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--color-border)',
  },
};

/**
 * Level dot colors for 9 skill levels (slug-keyed).
 * Derived from config/puzzle-levels.json via Vite JSON import.
 */
const LEVEL_COLORS: Record<LevelSlug, string> = {
  novice: 'var(--color-challenge-novice)', // Bright green (30-20k)
  beginner: 'var(--color-challenge-beginner)', // Green (19-15k)
  elementary: 'var(--color-challenge-elementary)', // Darker green (14-10k)
  intermediate: 'var(--color-challenge-intermediate)', // Yellow (9-5k)
  'upper-intermediate': 'var(--color-challenge-upper-intermediate)', // Orange (4-1k)
  advanced: 'var(--color-challenge-advanced)', // Deep orange (1-3d)
  'low-dan': 'var(--color-challenge-low-dan)', // Red (4-6d)
  'high-dan': 'var(--color-challenge-high-dan)', // Pink (7d+)
  expert: 'var(--color-challenge-expert)', // Purple (Pro)
};

/**
 * ChallengeCard - Renders a single challenge card with progress
 */
export function ChallengeCard({
  data,
  isSelected = false,
  onSelect,
}: ChallengeCardProps): JSX.Element {
  const progressPercent = getProgressPercent(data.completedPuzzles, data.totalPuzzles);
  const isComplete = data.completedPuzzles >= data.totalPuzzles;
  const statusText = getStatusText(data);
  const statusColor = getStatusColor(data);

  // Determine card style
  let cardStyle = styles.card;
  if (!data.isUnlocked) {
    cardStyle = styles.cardLocked;
  } else if (isSelected) {
    cardStyle = styles.cardSelected;
  } else if (data.isToday) {
    cardStyle = styles.cardToday;
  }

  const handleClick = (): void => {
    if (data.isUnlocked) {
      onSelect(data.id);
    }
  };

  const handleKeyDown = (e: KeyboardEvent): void => {
    if ((e.key === 'Enter' || e.key === ' ') && data.isUnlocked) {
      e.preventDefault();
      onSelect(data.id);
    }
  };

  return (
    <div
      style={cardStyle}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={data.isUnlocked ? 0 : -1}
      role="button"
      aria-label={`${data.displayDate} challenge, ${statusText}, ${data.totalPuzzles} puzzles`}
      aria-disabled={!data.isUnlocked}
      aria-pressed={isSelected}
    >
      <div style={styles.header}>
        <div style={styles.dateContainer}>
          <h3 style={styles.date}>{data.displayDate}</h3>
          {data.isToday && <span style={styles.todayBadge}>Today</span>}
        </div>
        <div style={styles.lockContainer}>
          <LockStatus isUnlocked={data.isUnlocked} size="small" />
        </div>
      </div>

      {data.isUnlocked && (
        <div style={styles.progressSection}>
          <div style={styles.progressBar}>
            <div
              style={{
                ...(isComplete ? styles.progressFillComplete : styles.progressFill),
                width: `${progressPercent}%`,
              }}
            />
          </div>
        </div>
      )}

      <div style={styles.footer}>
        <span style={{ ...styles.status, color: statusColor }}>{statusText}</span>
        <span style={styles.puzzleCount}>{data.totalPuzzles} puzzles</span>
      </div>

      {/* Level indicator dots */}
      <div style={styles.levelDots}>
        {LEVEL_SLUGS.map((level) => (
          <div
            key={level}
            style={{
              ...styles.levelDot,
              background:
                data.puzzlesByLevel[level] > 0 ? LEVEL_COLORS[level] : 'var(--color-border)',
            }}
            title={`${level}: ${data.puzzlesByLevel[level]} puzzles`}
          />
        ))}
      </div>
    </div>
  );
}

export default ChallengeCard;
