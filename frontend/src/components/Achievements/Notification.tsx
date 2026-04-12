/**
 * Achievement notification component.
 * Shows toast/popup when achievement is unlocked.
 * @module components/Achievements/Notification
 */
import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import type { AchievementDefinition } from '../../lib/achievements';
import { getTierColor } from '../../lib/achievements';
import './Notification.css';

export interface NotificationProps {
  /** Achievement to display */
  achievement: AchievementDefinition;
  /** Callback when notification is dismissed */
  onDismiss?: () => void;
  /** Auto-dismiss after milliseconds (0 = no auto-dismiss) */
  autoDismissMs?: number;
  /** Optional class name */
  className?: string;
}

/**
 * Achievement notification toast.
 */
export function Notification({
  achievement,
  onDismiss,
  autoDismissMs = 5000,
  className = '',
}: NotificationProps): JSX.Element {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  const handleDismiss = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      setIsVisible(false);
      onDismiss?.();
    }, 300); // Animation duration
  }, [onDismiss]);

  // Auto-dismiss
  useEffect(() => {
    if (autoDismissMs > 0) {
      const timer = setTimeout(handleDismiss, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [autoDismissMs, handleDismiss]);

  if (!isVisible) {
    return <></>;
  }

  const tierColor = getTierColor(achievement.tier);

  return (
    <div
      className={`achievement-notification ${isExiting ? 'achievement-notification--exiting' : ''} ${className}`}
      role="alert"
      aria-live="polite"
      style={{ '--tier-color': tierColor } as JSX.CSSProperties}
    >
      <div className="achievement-notification__icon">{achievement.icon}</div>

      <div className="achievement-notification__content">
        <div className="achievement-notification__header">
          <span className="achievement-notification__label">Achievement Unlocked!</span>
          <span
            className={`achievement-notification__tier achievement-notification__tier--${achievement.tier}`}
          >
            {achievement.tier}
          </span>
        </div>
        <h3 className="achievement-notification__name">{achievement.name}</h3>
        <p className="achievement-notification__description">{achievement.description}</p>
      </div>

      <button
        type="button"
        className="achievement-notification__close"
        onClick={handleDismiss}
        aria-label="Dismiss notification"
      >
        ×
      </button>
    </div>
  );
}

/**
 * Props for notification queue.
 */
export interface NotificationQueueProps {
  /** Achievements to show (in order) */
  achievements: readonly AchievementDefinition[];
  /** Callback when an achievement is dismissed */
  onDismiss?: (achievementId: string) => void;
  /** Callback when all notifications are dismissed */
  onAllDismissed?: () => void;
  /** Auto-dismiss delay per notification */
  autoDismissMs?: number;
  /** Optional class name */
  className?: string;
}

/**
 * Queue of achievement notifications (shows one at a time).
 */
export function NotificationQueue({
  achievements,
  onDismiss,
  onAllDismissed,
  autoDismissMs = 5000,
  className = '',
}: NotificationQueueProps): JSX.Element {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handleDismiss = useCallback(() => {
    const current = achievements[currentIndex];
    if (current) {
      onDismiss?.(current.id);
    }

    const nextIndex = currentIndex + 1;
    if (nextIndex >= achievements.length) {
      onAllDismissed?.();
    } else {
      setCurrentIndex(nextIndex);
    }
  }, [achievements, currentIndex, onDismiss, onAllDismissed]);

  // Reset when achievements change
  useEffect(() => {
    setCurrentIndex(0);
  }, [achievements]);

  const current = achievements[currentIndex];
  if (!current) {
    return <></>;
  }

  return (
    <div className={`achievement-notification-queue ${className}`}>
      <Notification
        key={current.id}
        achievement={current}
        onDismiss={handleDismiss}
        autoDismissMs={autoDismissMs}
      />
      {achievements.length > 1 && (
        <div className="achievement-notification-queue__counter">
          {currentIndex + 1} of {achievements.length}
        </div>
      )}
    </div>
  );
}

export default Notification;
