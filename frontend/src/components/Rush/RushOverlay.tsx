/**
 * RushOverlay — HUD overlay for Puzzle Rush mode.
 * @module components/Rush/RushOverlay
 *
 * Displays timer, lives, score, streak, and game controls in a
 * theme-consistent elevated bar. Uses app surface tokens instead
 * of hardcoded dark backgrounds.
 *
 * Game-over rendering is handled exclusively by PuzzleRushPage —
 * this component only renders the live HUD.
 *
 * Spec 125, Task T089
 */

import type { FunctionComponent } from 'preact';
import { HeartIcon, FireIcon } from '../shared/icons';

// ============================================================================
// Props
// ============================================================================

export interface RushOverlayProps {
  /** Formatted time remaining (MM:SS) */
  timeDisplay: string;
  /** Time remaining in seconds (for urgency coloring) */
  timeRemaining: number;
  /** Total duration in seconds (for progress bar) */
  totalDuration: number;
  /** Current number of lives */
  lives: number;
  /** Maximum lives */
  maxLives: number;
  /** Current score */
  score: number;
  /** Current streak */
  streak: number;
  /** Whether game is over */
  isGameOver: boolean;
  /** Skip callback */
  onSkip?: () => void;
  /** Quit callback */
  onQuit?: () => void;
  /** Whether skip is disabled (e.g. only 1 life left) */
  skipDisabled?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export const RushOverlay: FunctionComponent<RushOverlayProps> = ({
  timeDisplay,
  timeRemaining,
  totalDuration,
  lives,
  maxLives,
  score,
  streak,
  isGameOver,
  onSkip,
  onQuit,
  skipDisabled,
  className,
}) => {
  const isUrgent = timeRemaining <= 30;
  const isCritical = timeRemaining <= 10;
  const progressPercent = totalDuration > 0 ? (timeRemaining / totalDuration) * 100 : 0;

  // Don't render HUD when game is over — PuzzleRushPage handles that state
  if (isGameOver) return null;

  return (
    <div className={className ?? ''}>
      {/* HUD Bar — uses elevated surface, not dark background */}
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] border-b border-[var(--color-panel-border)] shadow-sm gap-3 flex-wrap"
        data-testid="rush-overlay"
      >
        {/* Timer */}
        <div className="flex items-center gap-2">
          <span
            className={`text-3xl font-bold tabular-nums min-w-[90px] ${isCritical ? 'text-[var(--color-status-wrong)] animate-pulse' : isUrgent ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-primary)]'}`}
            data-testid="rush-timer"
          >
            {timeDisplay}
          </span>
        </div>

        {/* Lives */}
        <div className="flex items-center gap-1" data-testid="rush-lives">
          {Array.from({ length: maxLives }).map((_, i) => (
            <span
              key={i}
              className={
                i < lives
                  ? 'text-[var(--color-accent)]'
                  : 'opacity-25 text-[var(--color-text-muted)]'
              }
              aria-label={i < lives ? 'Life remaining' : 'Life lost'}
            >
              <HeartIcon size={20} filled={i < lives} />
            </span>
          ))}
        </div>

        {/* Score */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
            Score
          </span>
          <span className="text-xl font-semibold" data-testid="rush-score">
            {score}
          </span>
        </div>

        {/* Streak (if > 0) */}
        {streak > 0 && (
          <span
            className="inline-flex items-center gap-1 text-sm bg-[var(--color-accent-container)] text-[var(--color-on-accent-container)] px-2.5 py-1 rounded-full font-semibold"
            data-testid="rush-streak"
          >
            <FireIcon size={14} className="inline" /> {streak}
          </span>
        )}

        {/* Controls: Skip + Quit */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Skip */}
          {onSkip && (
            <button
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] border border-[var(--color-panel-border)] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed min-h-[36px] hover:bg-[var(--color-bg-tertiary)] transition-colors"
              onClick={onSkip}
              disabled={skipDisabled}
              aria-label="Skip puzzle (costs 1 life)"
              title={skipDisabled ? "Can't skip — only 1 life left" : 'Skip puzzle (costs 1 life)'}
              data-testid="skip-button"
            >
              Skip <HeartIcon size={12} filled className="text-[var(--color-accent)]" />
            </button>
          )}

          {/* Quit */}
          {onQuit && (
            <button
              type="button"
              className="px-3 py-1.5 text-sm rounded-lg text-[var(--color-text-muted)] border border-[var(--color-panel-border)] cursor-pointer min-h-[36px] hover:text-[var(--color-status-wrong)] hover:border-[var(--color-status-wrong)] transition-colors"
              onClick={onQuit}
              aria-label="Quit game"
              data-testid="quit-button"
            >
              Quit
            </button>
          )}
        </div>
      </div>

      {/* Timer progress bar */}
      <div className="h-1 bg-[var(--color-bg-secondary)]">
        <div
          className={`h-1 transition-all duration-1000 ease-linear ${isCritical ? 'bg-[var(--color-status-wrong)]' : isUrgent ? 'bg-amber-500' : 'bg-[var(--color-accent)]'}`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
};

export default RushOverlay;
