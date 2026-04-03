/**
 * Achievement List Component
 * @module components/Progress/AchievementList
 *
 * Displays user achievements with:
 * - Unlocked achievements with unlock dates
 * - Locked achievements with progress bars
 * - Category filtering
 * - Notification toast for new achievements (FR-044)
 *
 * Covers: FR-042, FR-043, FR-044, US8
 */

import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import type { JSX } from 'preact';
import {
  ACHIEVEMENT_DEFINITIONS,
  combineWithProgress,
  sortAchievements,
  getTierColor,
  getTierDisplayName,
  type AchievementCategory,
  type AchievementWithProgress,
  type AchievementNotification,
  type AchievementProgress,
  type AchievementId,
} from '../../models/achievement';
import type { Achievement, UserProgress } from '../../models/progress';

/** Props for the AchievementList component */
export interface AchievementListProps {
  /** User progress data containing achievements */
  readonly progress: UserProgress | null;
  /** Optional class name for styling */
  readonly className?: string;
  /** Callback when an achievement is clicked for details */
  readonly onAchievementClick?: (achievementId: AchievementId) => void;
  /** New achievements to show as notifications */
  readonly newAchievements?: readonly AchievementNotification[];
  /** Callback when notification is dismissed */
  readonly onNotificationDismiss?: (achievementId: AchievementId) => void;
}

/** Category filter option */
interface CategoryOption {
  readonly value: AchievementCategory | 'all';
  readonly label: string;
  readonly icon: string;
}

/** Available category filters */
const CATEGORY_OPTIONS: readonly CategoryOption[] = [
  { value: 'all', label: 'All', icon: '🏆' },
  { value: 'puzzles', label: 'Puzzles', icon: '🧩' },
  { value: 'streaks', label: 'Streaks', icon: '🔥' },
  { value: 'rush', label: 'Rush', icon: '⏱️' },
  { value: 'mastery', label: 'Mastery', icon: '🧠' },
  { value: 'collection', label: 'Collection', icon: '📚' },
  { value: 'special', label: 'Special', icon: '✨' },
];

/**
 * Convert stored Achievement to AchievementProgress
 */
function toAchievementProgress(achievement: Achievement): AchievementProgress {
  return {
    achievementId: achievement.id as AchievementId,
    currentValue: achievement.progress ?? achievement.target,
    unlockedAt: achievement.unlockedAt ?? null,
  };
}

/**
 * Get achievements combined with user progress
 */
function getAchievementsWithProgress(
  progress: UserProgress | null
): AchievementWithProgress[] {
  const userAchievements = new Map<AchievementId, AchievementProgress>();

  if (progress?.achievements) {
    progress.achievements.forEach((a) => {
      userAchievements.set(a.id as AchievementId, toAchievementProgress(a));
    });
  }

  return ACHIEVEMENT_DEFINITIONS.map((def) =>
    combineWithProgress(def, userAchievements.get(def.id))
  );
}

/**
 * Format unlock date for display
 */
function formatUnlockDate(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoDate;
  }
}

/**
 * Individual achievement card component
 */
function AchievementCard({
  achievement,
  onClick,
}: {
  achievement: AchievementWithProgress;
  onClick?: () => void;
}): JSX.Element {
  const tierColor = getTierColor(achievement.tier);
  const tierName = getTierDisplayName(achievement.tier);

  const handleClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick?.();
      }
    },
    [onClick]
  );

  return (
    <div
      className={`achievement-card ${achievement.isUnlocked ? 'unlocked' : 'locked'}`}
      role="button"
      tabIndex={0}
      aria-label={`${achievement.name}: ${achievement.description}. ${
        achievement.isUnlocked
          ? `Unlocked on ${formatUnlockDate(achievement.unlockedAt!)}`
          : `${achievement.progressPercent}% complete`
      }`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={{ '--tier-color': tierColor } as JSX.CSSProperties}
    >
      <div className="achievement-icon" aria-hidden="true">
        {achievement.isUnlocked ? achievement.icon : '🔒'}
      </div>

      <div className="achievement-content">
        <div className="achievement-header">
          <h4 className="achievement-name">
            {achievement.hidden && !achievement.isUnlocked ? '???' : achievement.name}
          </h4>
          <span
            className="achievement-tier"
            style={{ backgroundColor: tierColor }}
            aria-label={`${tierName} tier`}
          >
            {tierName}
          </span>
        </div>

        <p className="achievement-description">
          {achievement.hidden && !achievement.isUnlocked
            ? 'Hidden achievement'
            : achievement.description}
        </p>

        {!achievement.isUnlocked && (
          <div className="achievement-progress">
            <div className="progress-bar" role="progressbar" aria-valuenow={achievement.progressPercent} aria-valuemin={0} aria-valuemax={100}>
              <div
                className="progress-fill"
                style={{ width: `${achievement.progressPercent}%` }}
              />
            </div>
            <span className="progress-text">
              {achievement.currentValue} / {achievement.target}
            </span>
          </div>
        )}

        {achievement.isUnlocked && achievement.unlockedAt && (
          <p className="achievement-unlock-date">
            Unlocked {formatUnlockDate(achievement.unlockedAt)}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Achievement notification toast component (FR-044)
 */
export function AchievementToast({
  notification,
  onDismiss,
  autoDismissMs = 5000,
}: {
  notification: AchievementNotification;
  onDismiss: () => void;
  autoDismissMs?: number;
}): JSX.Element {
  const timerRef = useRef<number | null>(null);
  const tierColor = getTierColor(notification.achievement.tier);

  useEffect(() => {
    if (autoDismissMs > 0) {
      timerRef.current = window.setTimeout(() => {
        onDismiss();
      }, autoDismissMs);
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [autoDismissMs, onDismiss]);

  const handleDismiss = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    onDismiss();
  }, [onDismiss]);

  return (
    <div
      className="achievement-toast"
      role="alert"
      aria-live="polite"
      style={{ '--tier-color': tierColor } as JSX.CSSProperties}
    >
      <div className="toast-icon" aria-hidden="true">
        {notification.achievement.icon}
      </div>
      <div className="toast-content">
        <p className="toast-title">🎉 Achievement Unlocked!</p>
        <p className="toast-name">{notification.achievement.name}</p>
        <p className="toast-description">{notification.achievement.description}</p>
      </div>
      <button
        className="toast-dismiss"
        onClick={handleDismiss}
        aria-label="Dismiss notification"
        type="button"
      >
        ✕
      </button>
    </div>
  );
}

/**
 * Toast container for multiple notifications
 */
export function AchievementToastContainer({
  notifications,
  onDismiss,
}: {
  notifications: readonly AchievementNotification[];
  onDismiss: (achievementId: AchievementId) => void;
}): JSX.Element | null {
  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="achievement-toast-container" aria-label="Achievement notifications">
      {notifications.map((notification) => (
        <AchievementToast
          key={notification.achievement.id}
          notification={notification}
          onDismiss={() => onDismiss(notification.achievement.id)}
        />
      ))}
    </div>
  );
}

/**
 * Category filter buttons
 */
function CategoryFilter({
  selected,
  onSelect,
}: {
  selected: AchievementCategory | 'all';
  onSelect: (category: AchievementCategory | 'all') => void;
}): JSX.Element {
  return (
    <div className="achievement-categories" role="tablist" aria-label="Achievement categories">
      {CATEGORY_OPTIONS.map((option) => (
        <button
          key={option.value}
          className={`category-btn ${selected === option.value ? 'active' : ''}`}
          onClick={() => onSelect(option.value)}
          role="tab"
          aria-selected={selected === option.value}
          type="button"
        >
          <span className="category-icon" aria-hidden="true">
            {option.icon}
          </span>
          <span className="category-label">{option.label}</span>
        </button>
      ))}
    </div>
  );
}

/**
 * Achievement summary stats
 */
function AchievementSummary({
  achievements,
}: {
  achievements: readonly AchievementWithProgress[];
}): JSX.Element {
  const unlocked = achievements.filter((a) => a.isUnlocked).length;
  const total = achievements.length;
  const percent = total > 0 ? Math.round((unlocked / total) * 100) : 0;

  return (
    <div className="achievement-summary" role="region" aria-label="Achievement summary">
      <div className="summary-stat">
        <span className="summary-value">{unlocked}</span>
        <span className="summary-label">Unlocked</span>
      </div>
      <div className="summary-divider" aria-hidden="true">/</div>
      <div className="summary-stat">
        <span className="summary-value">{total}</span>
        <span className="summary-label">Total</span>
      </div>
      <div className="summary-progress">
        <div className="progress-bar" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${percent}%` }} />
        </div>
        <span className="progress-percent">{percent}%</span>
      </div>
    </div>
  );
}

/**
 * Achievement List Component
 *
 * Displays all achievements with filtering, progress tracking,
 * and notification toasts for newly unlocked achievements.
 */
export function AchievementList({
  progress,
  className,
  onAchievementClick,
  newAchievements = [],
  onNotificationDismiss,
}: AchievementListProps): JSX.Element {
  const [selectedCategory, setSelectedCategory] = useState<AchievementCategory | 'all'>('all');
  const [achievements, setAchievements] = useState<AchievementWithProgress[]>([]);

  // Update achievements when progress changes
  useEffect(() => {
    const withProgress = getAchievementsWithProgress(progress);
    setAchievements(withProgress);
  }, [progress]);

  // Filter achievements by category
  const filteredAchievements = selectedCategory === 'all'
    ? achievements
    : achievements.filter((a) => a.category === selectedCategory);

  // Sort achievements
  const sortedAchievements = sortAchievements(filteredAchievements);

  // Handle category change
  const handleCategoryChange = useCallback((category: AchievementCategory | 'all') => {
    setSelectedCategory(category);
  }, []);

  // Handle achievement click
  const handleAchievementClick = useCallback(
    (achievementId: AchievementId) => {
      onAchievementClick?.(achievementId);
    },
    [onAchievementClick]
  );

  // Handle notification dismiss
  const handleNotificationDismiss = useCallback(
    (achievementId: AchievementId) => {
      onNotificationDismiss?.(achievementId);
    },
    [onNotificationDismiss]
  );

  return (
    <div className={`achievement-list ${className ?? ''}`} role="region" aria-label="Achievements">
      {/* Toast notifications for new achievements (FR-044) */}
      <AchievementToastContainer
        notifications={newAchievements}
        onDismiss={handleNotificationDismiss}
      />

      {/* Summary section */}
      <AchievementSummary achievements={achievements} />

      {/* Category filter */}
      <CategoryFilter selected={selectedCategory} onSelect={handleCategoryChange} />

      {/* Achievement grid */}
      <div className="achievement-grid" role="list">
        {sortedAchievements.length === 0 ? (
          <div className="achievement-empty" role="status">
            <p>No achievements in this category yet.</p>
          </div>
        ) : (
          sortedAchievements.map((achievement) => (
            <AchievementCard
              key={achievement.id}
              achievement={achievement}
              {...(onAchievementClick
                ? { onClick: () => handleAchievementClick(achievement.id) }
                : {})}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default AchievementList;
