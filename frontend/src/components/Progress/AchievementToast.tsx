/**
 * AchievementToast — Fixed-position toast for newly unlocked achievements.
 * @module components/Progress/AchievementToast
 */

import type { FunctionalComponent } from 'preact';
import { useEffect } from 'preact/hooks';
import type { Achievement } from '../../models/progress';
import { TrophyIcon } from '../shared/icons';

export interface AchievementToastProps {
  achievement: Achievement;
  onDismiss: () => void;
}

export const AchievementToast: FunctionalComponent<AchievementToastProps> = ({
  achievement,
  onDismiss,
}) => {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="alert"
      data-testid="achievement-toast"
      className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-xl bg-[var(--color-bg-elevated)] p-4 shadow-lg"
      style={{ minWidth: '280px', maxWidth: '360px' }}
    >
      <div className="shrink-0 text-yellow-500">
        <TrophyIcon size={28} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-[var(--color-text-primary)]">{achievement.name}</p>
        <p className="text-xs text-[var(--color-text-muted)]">{achievement.description}</p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 rounded p-1 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)]"
        aria-label="Dismiss"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
};
