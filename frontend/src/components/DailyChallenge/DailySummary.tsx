/**
 * DailySummary Component
 * @module components/DailyChallenge/DailySummary
 *
 * Displays results summary after completing a daily challenge.
 * Shows time, accuracy by level, and overall performance.
 * Uses amber/gold daily theme with SVG icons (no emojis).
 *
 * Covers: FR-040, FR-041
 */

import type { JSX } from 'preact';
import type { DailyPerformanceData } from '@/models/dailyChallenge';
import { getSkillLevelInfo } from '@/models/collection';
import { getAccuracyColorClass } from '../../lib/accuracy-color';
import { TrophyIcon, StarIcon, TrendUpIcon } from '../shared/icons';

export interface DailySummaryProps {
  /** Challenge date */
  date: string;
  /** Total puzzles */
  totalPuzzles: number;
  /** Puzzles completed */
  completedPuzzles: number;
  /** Performance data */
  performance?: DailyPerformanceData | undefined;
  /** Whether this was timed mode */
  isTimedMode?: boolean | undefined;
  /** Callback to play again */
  onPlayAgain?: () => void;
  /** Callback to go home */
  onGoHome?: () => void;
  /** Custom className */
  className?: string | undefined;
}

/**
 * Format duration in ms to display string
 */
function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

/**
 * Format date for display
 */
function formatDate(date: string): string {
  try {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return date;
  }
}

/**
 * Get completion SVG icon based on accuracy
 */
function CompletionIcon({ accuracy }: { accuracy: number }): JSX.Element {
  if (accuracy >= 90) return <TrophyIcon size={48} className="text-[var(--color-mode-daily-text,#d97706)]" style={{ fill: 'currentColor', stroke: 'none' }} />;
  if (accuracy >= 70) return <StarIcon size={48} filled className="text-[var(--color-mode-daily-text,#d97706)]" />;
  return <TrendUpIcon size={48} className="text-[var(--color-mode-daily-text,#d97706)]" />;
}

/**
 * Calculate overall accuracy from level data
 */
function calculateOverallAccuracy(accuracyByLevel: Record<string, { correct: number; total: number }>): number {
  let totalCorrect = 0;
  let totalAttempts = 0;

  for (const data of Object.values(accuracyByLevel)) {
    totalCorrect += data.correct;
    totalAttempts += data.total;
  }

  return totalAttempts > 0 ? Math.round((totalCorrect / totalAttempts) * 100) : 0;
}

/**
 * DailySummary - Shows results after completing daily challenge
 */
export function DailySummary({
  date,
  totalPuzzles,
  completedPuzzles,
  performance,
  isTimedMode = false,
  onPlayAgain,
  onGoHome,
  className = '',
}: DailySummaryProps): JSX.Element {
  const accuracy = performance?.accuracyByLevel
    ? calculateOverallAccuracy(performance.accuracyByLevel)
    : Math.round((completedPuzzles / totalPuzzles) * 100);
  const isComplete = completedPuzzles >= totalPuzzles;

  // Get accuracy by level entries
  const levelAccuracyEntries = performance?.accuracyByLevel
    ? Object.entries(performance.accuracyByLevel)
    : [];

  return (
    <div class={`daily-summary max-w-[420px] w-full mx-auto text-center ${className}`}>
      {/* Warm card with amber accent border */}
      <div className="rounded-2xl border border-[var(--color-mode-daily-border,#fbbf24)] bg-[var(--color-bg-panel)] p-8 shadow-lg">

        {/* Icon + Title */}
        <div className="mb-8">
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-mode-daily-light,#fffbeb)]">
            <CompletionIcon accuracy={accuracy} />
          </div>
          <h2 className="m-0 mb-1 text-[1.75rem] font-bold leading-tight text-[var(--color-neutral-900)]">
            {isComplete ? 'Challenge Complete!' : 'Nice Progress!'}
          </h2>
          <p className="m-0 text-sm font-medium text-[var(--color-mode-daily-text,#d97706)]">
            {formatDate(date)}
          </p>
        </div>

        {/* Stats — 2-column grid */}
        <div className="mb-8 grid grid-cols-2 gap-3">
          {/* Accuracy */}
          <div className="rounded-xl bg-[var(--color-mode-daily-light,#fffbeb)] px-4 py-5">
            <span className={`block text-3xl font-extrabold tabular-nums ${getAccuracyColorClass(accuracy)}`}>
              {accuracy}%
            </span>
            <span className="mt-1 block text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--color-neutral-500)]">
              Accuracy
            </span>
          </div>

          {/* Puzzles */}
          <div className="rounded-xl bg-[var(--color-mode-daily-light,#fffbeb)] px-4 py-5">
            <span className="block text-3xl font-extrabold tabular-nums text-[var(--color-neutral-900)]">
              {completedPuzzles}/{totalPuzzles}
            </span>
            <span className="mt-1 block text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--color-neutral-500)]">
              Puzzles
            </span>
          </div>

          {/* Total Time */}
          {performance?.totalTimeMs !== undefined && (
            <div className="rounded-xl bg-[var(--color-mode-daily-light,#fffbeb)] px-4 py-5">
              <span className="block text-3xl font-extrabold tabular-nums text-[var(--color-neutral-900)]">
                {formatDuration(performance.totalTimeMs)}
              </span>
              <span className="mt-1 block text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--color-neutral-500)]">
                Total Time
              </span>
            </div>
          )}

          {/* Timed Score */}
          {isTimedMode && performance?.timedHighScore !== undefined && (
            <div className="rounded-xl bg-[var(--color-mode-daily-light,#fffbeb)] px-4 py-5">
              <span className="block text-3xl font-extrabold tabular-nums text-[var(--color-mode-daily-text,#d97706)]">
                {performance.timedHighScore}
              </span>
              <span className="mt-1 block text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--color-neutral-500)]">
                Score
              </span>
            </div>
          )}
        </div>

        {/* Accuracy by Level */}
        {levelAccuracyEntries.length > 0 && (
          <div className="mb-8">
            <h3 className="mb-3 text-left text-xs font-bold uppercase tracking-wider text-[var(--color-neutral-500)]">
              By Difficulty
            </h3>
            <div className="space-y-2">
              {levelAccuracyEntries.map(([level, data]) => {
                const levelInfo = getSkillLevelInfo(level);
                const levelAccuracy = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;
                return (
                  <div key={level} className="flex items-center justify-between rounded-lg bg-[var(--color-neutral-50)] px-4 py-2.5">
                    <span className="text-sm font-medium text-[var(--color-neutral-700)]">
                      {levelInfo?.name ?? level}
                    </span>
                    <span className={`text-sm font-bold tabular-nums ${getAccuracyColorClass(levelAccuracy)}`}>
                      {data.correct}/{data.total} ({levelAccuracy}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          {onGoHome && (
            <button
              type="button"
              className="flex-1 cursor-pointer rounded-xl border border-[var(--color-neutral-200)] bg-[var(--color-neutral-50)] px-5 py-3.5 text-sm font-bold text-[var(--color-neutral-700)] transition-all hover:bg-[var(--color-neutral-100)] active:scale-[0.97]"
              onClick={onGoHome}
            >
              Home
            </button>
          )}
          {onPlayAgain && (
            <button
              type="button"
              className="flex-1 cursor-pointer rounded-xl border-none bg-[var(--color-mode-daily-text,#d97706)] px-5 py-3.5 text-sm font-bold text-white shadow-md transition-all hover:brightness-110 active:scale-[0.97]"
              onClick={onPlayAgain}
            >
              {isComplete ? 'Play Again' : 'Continue'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default DailySummary;
