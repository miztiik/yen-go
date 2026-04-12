/**
 * DailyChallengeCard Component
 * @module components/DailyChallenge/DailyChallengeCard
 *
 * Card display for daily challenge on home screen.
 * Shows date, puzzle count, mode buttons, and progress.
 *
 * Covers: FR-030, FR-031
 */

import type { JSX } from 'preact';
import type { DailyChallengeSummary, DailyChallengeMode } from '@/models/dailyChallenge';

export interface DailyChallengeCardProps {
  /** Challenge summary data */
  challenge: DailyChallengeSummary | null;
  /** User's progress (number of completed puzzles) */
  completedCount?: number | undefined;
  /** Whether challenge is loading */
  isLoading?: boolean | undefined;
  /** Whether today's challenge is available */
  isAvailable?: boolean | undefined;
  /** Callback when mode is selected */
  onModeSelect?: (mode: DailyChallengeMode) => void;
  /** Callback when card is clicked (alternative to mode select) */
  onClick?: () => void;
  /** Custom className */
  className?: string | undefined;
}

/**
 * Format date for display
 */
function formatDisplayDate(date: string): string {
  try {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return date;
  }
}

/**
 * DailyChallengeCard - Shows today's challenge with mode options
 */
export function DailyChallengeCard({
  challenge,
  completedCount = 0,
  isLoading = false,
  isAvailable = true,
  onModeSelect,
  onClick,
  className = '',
}: DailyChallengeCardProps): JSX.Element {
  const handleModeClick = (mode: DailyChallengeMode, e: Event): void => {
    e.stopPropagation();
    onModeSelect?.(mode);
  };

  if (isLoading) {
    return (
      <div
        class={`daily-challenge-card bg-[--color-bg-panel] rounded-xl p-5 shadow-md border border-[--color-neutral-200] transition-all cursor-pointer ${className}`}
      >
        <div className="flex justify-center items-center min-h-[120px] text-[--color-text-muted]">
          Loading today's challenge...
        </div>
      </div>
    );
  }

  if (!isAvailable || !challenge) {
    return (
      <div
        class={`daily-challenge-card bg-[--color-bg-panel] rounded-xl p-5 shadow-md border border-[--color-neutral-200] transition-all cursor-pointer ${className}`}
      >
        <div className="text-center p-6 text-[--color-text-muted]">
          <p className="text-xl font-semibold text-[--color-text-primary] m-0 mb-1">
            Daily Challenge
          </p>
          <p>Coming soon! Check back later.</p>
        </div>
      </div>
    );
  }

  const progressPercent =
    challenge.puzzleCount > 0 ? Math.round((completedCount / challenge.puzzleCount) * 100) : 0;

  const isComplete = completedCount >= challenge.puzzleCount;

  return (
    <div
      class={`daily-challenge-card bg-[--color-bg-panel] rounded-xl p-5 shadow-md border border-[--color-neutral-200] transition-all cursor-pointer hover:-translate-y-0.5 hover:shadow-lg ${className}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-semibold text-[--color-text-primary] m-0 mb-1">
            Daily Challenge
          </h3>
          <p className="text-sm text-[--color-text-muted] m-0">
            {formatDisplayDate(challenge.date)}
          </p>
        </div>
        {challenge.isToday && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[--color-success] bg-[--color-success-bg] px-2.5 py-1 rounded-xl">
            <span>●</span> Today
          </span>
        )}
        {isComplete && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[--color-success] bg-[--color-success-bg] px-2.5 py-1 rounded-xl">
            ✓ Complete
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-4 mb-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-2xl font-semibold text-[--color-text-primary]">
            {challenge.puzzleCount}
          </span>
          <span className="text-xs text-[--color-text-muted] uppercase tracking-wider">
            Puzzles
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-2xl font-semibold text-[--color-text-primary]">
            {completedCount}
          </span>
          <span className="text-xs text-[--color-text-muted] uppercase tracking-wider">
            Completed
          </span>
        </div>
      </div>

      {/* Progress */}
      {completedCount > 0 && (
        <div className="h-1 bg-[--color-neutral-200] rounded-sm mt-3 overflow-hidden">
          <div
            className="h-full bg-[--color-success-solid] rounded-sm transition-[width] duration-300 ease-in-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}

      {/* Mode Buttons */}
      {onModeSelect && !isComplete && (
        <div className="flex gap-3 mt-4">
          <button
            type="button"
            className="flex-1 px-4 py-3 rounded-lg border-2 bg-transparent cursor-pointer flex flex-col items-center gap-1 transition-all border-[--color-info-solid] text-[--color-mode-daily-text]"
            onClick={(e) => handleModeClick('standard', e)}
          >
            <span className="text-xl">📝</span>
            <span className="text-sm font-semibold">Standard</span>
            <span className="text-xs opacity-80">No time limit</span>
          </button>
          <button
            type="button"
            className="flex-1 px-4 py-3 rounded-lg border-2 bg-transparent cursor-pointer flex flex-col items-center gap-1 transition-all border-[--color-warning] text-[--color-warning]"
            onClick={(e) => handleModeClick('timed', e)}
          >
            <span className="text-xl">⏱️</span>
            <span className="text-sm font-semibold">Timed</span>
            <span className="text-xs opacity-80">Beat the clock</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default DailyChallengeCard;
