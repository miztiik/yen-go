/**
 * LevelCard Component - Displays a single level in the list
 * @module components/Level/LevelCard
 *
 * Covers: FR-012, FR-013, US2
 *
 * Constitution Compliance:
 * - IX. Accessibility: Interactive card with proper ARIA
 */

import type { JSX } from 'preact';
import type { LevelManifestEntry } from '@services/puzzleLoader';

/** Props for LevelCard component */
export interface LevelCardProps {
  /** Level manifest entry data */
  level: LevelManifestEntry;
  /** Whether the level is unlocked */
  isUnlocked: boolean;
  /** Whether the level is completed */
  isCompleted: boolean;
  /** Click handler */
  onClick?: () => void;
  /** CSS class name */
  className?: string;
}

/** Level difficulty icons */
const LEVEL_ICONS: Record<string, string> = {
  beginner: '🟢',
  basic: '🟡',
  intermediate: '🟠',
  advanced: '🔴',
  expert: '⚫',
};

/**
 * LevelCard - Displays a skill level's summary information
 */
export function LevelCard({
  level,
  isUnlocked,
  isCompleted,
  onClick,
  className = '',
}: LevelCardProps): JSX.Element {
  const statusClass = isCompleted
    ? 'level-card--completed'
    : isUnlocked
    ? 'level-card--unlocked'
    : 'level-card--locked';

  const statusIcon = isCompleted ? '✅' : isUnlocked ? '🔓' : '🔒';
  const statusLabel = isCompleted
    ? 'Completed'
    : isUnlocked
    ? 'Unlocked'
    : 'Locked';

  const levelIcon = LEVEL_ICONS[level.id] ?? '🟢';

  return (
    <article
      className={`level-card ${statusClass} ${className}`}
      role="button"
      tabIndex={isUnlocked ? 0 : -1}
      onClick={isUnlocked ? onClick : undefined}
      onKeyDown={(e): void => {
        if (isUnlocked && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.();
        }
      }}
      aria-disabled={!isUnlocked}
      aria-label={`${level.name}. ${level.puzzleCount} puzzles. ${statusLabel}.`}
    >
      <header className="level-card__header">
        <span className="level-card__status" aria-hidden="true">
          {statusIcon}
        </span>
        <span className="level-card__level-icon" aria-hidden="true">
          {levelIcon}
        </span>
      </header>

      <h3 className="level-card__title">{level.name}</h3>

      <div className="level-card__stats">
        <span className="level-card__puzzle-count">
          {level.puzzleCount} {level.puzzleCount === 1 ? 'puzzle' : 'puzzles'}
        </span>
      </div>

      {!isUnlocked && (
        <p className="level-card__lock-message">
          Complete previous level to unlock
        </p>
      )}
    </article>
  );
}

export default LevelCard;
