/**
 * Streak Display Component
 * @module components/Progress/StreakDisplay
 *
 * Displays current streak, milestones, and streak status.
 *
 * Covers: FR-023 to FR-026, US4
 */

import { useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import { useStreak } from '../../hooks/useStreak';
import type { StreakMilestone } from '../../services/streakManager';
import { STREAK_MILESTONES } from '../../services/streakManager';
import { FireIcon } from '../shared/icons/FireIcon';
import { WarningIcon } from '../shared/icons/WarningIcon';
import { SleepIcon } from '../shared/icons/SleepIcon';
import { TrophyIcon } from '../shared/icons/TrophyIcon';
import { LockIcon } from '../shared/icons/LockIcon';

/** Props for the StreakDisplay component */
export interface StreakDisplayProps {
  readonly className?: string;
  readonly showMilestones?: boolean;
  readonly compact?: boolean;
  readonly onMilestoneReached?: (milestone: StreakMilestone) => void;
}

/** Milestone badge component */
function MilestoneBadge({
  milestone,
  achieved,
}: {
  milestone: StreakMilestone;
  achieved: boolean;
}): JSX.Element {
  const icon = achieved ? <TrophyIcon size={14} /> : <LockIcon size={14} />;
  const className = achieved ? 'milestone-badge achieved' : 'milestone-badge locked';

  return (
    <span
      className={className}
      role="img"
      aria-label={`${milestone} day streak ${achieved ? 'achieved' : 'locked'}`}
      title={`${milestone} days`}
    >
      {icon} {milestone}
    </span>
  );
}

/**
 * Streak Display Component
 *
 * Shows the user's current streak with visual feedback:
 * - Fire emoji for active streaks
 * - Warning for at-risk streaks
 * - Progress towards next milestone
 * - Celebration for milestone achievements
 */
export function StreakDisplay({
  className,
  showMilestones = true,
  compact = false,
  onMilestoneReached,
}: StreakDisplayProps): JSX.Element {
  const { stats, isLoading, error, recentMilestones, clearMilestones } = useStreak();

  // Handle milestone notification
  const handleMilestoneAcknowledge = useCallback(() => {
    if (recentMilestones.length > 0 && onMilestoneReached) {
      recentMilestones.forEach((m) => onMilestoneReached(m));
    }
    clearMilestones();
  }, [recentMilestones, onMilestoneReached, clearMilestones]);

  if (isLoading) {
    return (
      <div className={`streak-display streak-loading ${className ?? ''}`} role="status">
        <span>Loading streak...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`streak-display streak-error ${className ?? ''}`} role="alert">
        <span>
          <WarningIcon size={14} /> {error}
        </span>
      </div>
    );
  }

  const {
    currentStreak,
    longestStreak,
    isActive,
    isAtRisk,
    nextMilestone,
    daysUntilNextMilestone,
  } = stats;

  // Compact mode for small displays
  if (compact) {
    return (
      <div
        className={`streak-display streak-compact ${className ?? ''}`}
        role="region"
        aria-label="Daily streak"
      >
        <span className="streak-icon" aria-hidden="true">
          {isActive ? (
            <FireIcon size={16} />
          ) : isAtRisk ? (
            <WarningIcon size={16} />
          ) : (
            <SleepIcon size={16} />
          )}
        </span>
        <span className="streak-count">{currentStreak}</span>
        <span className="streak-unit">day{currentStreak !== 1 ? 's' : ''}</span>
      </div>
    );
  }

  return (
    <div
      className={`streak-display ${className ?? ''}`}
      role="region"
      aria-label="Streak information"
    >
      {/* Milestone celebration */}
      {recentMilestones.length > 0 && (
        <div className="streak-celebration" role="alert">
          <h4>🎉 Milestone Reached!</h4>
          <p>You've maintained a {recentMilestones[recentMilestones.length - 1]}-day streak!</p>
          <button onClick={handleMilestoneAcknowledge} className="btn-acknowledge">
            Awesome!
          </button>
        </div>
      )}

      {/* Main streak display */}
      <div className="streak-main">
        <div className="streak-flame">
          <span className="flame-icon" aria-hidden="true">
            {isActive ? (
              <FireIcon size={24} />
            ) : isAtRisk ? (
              <WarningIcon size={24} />
            ) : (
              <SleepIcon size={24} />
            )}
          </span>
          <span className="streak-number">{currentStreak}</span>
        </div>
        <div className="streak-label">
          <span className="label-text">
            {currentStreak === 0 && !isAtRisk
              ? 'Start your streak!'
              : isAtRisk
                ? 'Play today to keep your streak!'
                : `Day${currentStreak !== 1 ? 's' : ''} in a row`}
          </span>
        </div>
      </div>

      {/* Best streak */}
      {longestStreak > 0 && (
        <div className="streak-best">
          <span className="best-label">Best:</span>
          <span className="best-value">
            {longestStreak} day{longestStreak !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Progress to next milestone */}
      {nextMilestone && daysUntilNextMilestone !== null && (
        <div className="streak-progress">
          <div className="progress-label">
            {daysUntilNextMilestone} more day{daysUntilNextMilestone !== 1 ? 's' : ''} to{' '}
            {nextMilestone}-day milestone
          </div>
          <div
            className="progress-bar"
            role="progressbar"
            aria-valuenow={currentStreak}
            aria-valuemax={nextMilestone}
          >
            <div
              className="progress-fill"
              style={{
                width: `${Math.min(100, (currentStreak / nextMilestone) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Milestones grid */}
      {showMilestones && (
        <div className="streak-milestones">
          <h4>Milestones</h4>
          <div className="milestone-grid">
            {STREAK_MILESTONES.map((milestone) => (
              <MilestoneBadge
                key={milestone}
                milestone={milestone}
                achieved={longestStreak >= milestone}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default StreakDisplay;
