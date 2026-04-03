/**
 * Achievement card component.
 * Displays a single achievement with progress.
 * @module components/Achievements/AchievementCard
 */
import type { JSX } from 'preact';
import type { AchievementDefinition, AchievementUnlock } from '../../lib/achievements';
import { getTierColor, getTierName } from '../../lib/achievements';
import './AchievementCard.css';

export interface AchievementCardProps {
  /** Achievement definition */
  achievement: AchievementDefinition;
  /** Whether achievement is unlocked */
  unlocked: boolean;
  /** Unlock record (if unlocked) */
  unlock?: AchievementUnlock;
  /** Current progress value */
  currentProgress?: number;
  /** Optional click handler */
  onClick?: () => void;
  /** Optional class name */
  className?: string;
}

/**
 * Format date for display.
 */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Achievement card component.
 */
export function AchievementCard({
  achievement,
  unlocked,
  unlock,
  currentProgress = 0,
  onClick,
  className = '',
}: AchievementCardProps): JSX.Element {
  const tierColor = getTierColor(achievement.tier);
  const progressPercent = Math.min(100, (currentProgress / achievement.requirement) * 100);
  const isHidden = achievement.hidden && !unlocked;

  return (
    <div
      className={`achievement-card ${unlocked ? 'achievement-card--unlocked' : ''} ${isHidden ? 'achievement-card--hidden' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={{ '--tier-color': tierColor } as JSX.CSSProperties}
    >
      <div className="achievement-card__icon">
        {isHidden ? '❓' : achievement.icon}
      </div>

      <div className="achievement-card__content">
        <div className="achievement-card__header">
          <h3 className="achievement-card__name">
            {isHidden ? '???' : achievement.name}
          </h3>
          <span className={`achievement-card__tier achievement-card__tier--${achievement.tier}`}>
            {getTierName(achievement.tier)}
          </span>
        </div>

        <p className="achievement-card__description">
          {isHidden ? 'Keep playing to discover this achievement!' : achievement.description}
        </p>

        {!unlocked && !isHidden && (
          <div className="achievement-card__progress">
            <div className="achievement-card__progress-bar">
              <div
                className="achievement-card__progress-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="achievement-card__progress-text">
              {currentProgress} / {achievement.requirement}
            </span>
          </div>
        )}

        {unlocked && unlock && (
          <div className="achievement-card__unlock-date">
            Unlocked {formatDate(unlock.unlockedAt)}
          </div>
        )}
      </div>

      {unlocked && (
        <div className="achievement-card__check" aria-label="Unlocked">
          ✓
        </div>
      )}
    </div>
  );
}

/**
 * Compact achievement badge (for lists).
 */
export function AchievementBadge({
  achievement,
  unlocked,
  className = '',
}: {
  achievement: AchievementDefinition;
  unlocked: boolean;
  className?: string;
}): JSX.Element {
  const tierColor = getTierColor(achievement.tier);

  return (
    <div
      className={`achievement-badge ${unlocked ? 'achievement-badge--unlocked' : ''} ${className}`}
      title={`${achievement.name}: ${achievement.description}`}
      style={{ '--tier-color': tierColor } as JSX.CSSProperties}
    >
      <span className="achievement-badge__icon">
        {achievement.icon}
      </span>
      {!unlocked && <span className="achievement-badge__lock">🔒</span>}
    </div>
  );
}

export default AchievementCard;
