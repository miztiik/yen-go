/**
 * Rush mode score display component.
 * Shows current score with streak and breakdown.
 * @module components/Rush/Score
 */
import type { JSX } from 'preact';
import type { PuzzleScore, ScoringState } from '../../lib/rush';
import { FireIcon } from '../shared/icons/FireIcon';
import './Score.css';

export interface ScoreProps {
  /** Current scoring state */
  state: ScoringState;
  /** Latest puzzle score (for animation) */
  lastScore?: PuzzleScore | null;
  /** Show detailed breakdown */
  showBreakdown?: boolean;
  /** Optional additional class name */
  className?: string;
}

/**
 * Format score with optional sign.
 */
function formatScore(value: number, showSign: boolean = false): string {
  if (showSign && value > 0) {
    return `+${value}`;
  }
  return value.toString();
}

/**
 * Rush mode score display.
 */
export function Score({
  state,
  lastScore = null,
  showBreakdown = false,
  className = '',
}: ScoreProps): JSX.Element {
  const { totalScore, currentStreak, isPerfect } = state;

  return (
    <div className={`rush-score ${className}`} aria-label={`Score: ${totalScore}`}>
      <div className="rush-score__main">
        <span className="rush-score__label">Score</span>
        <span className="rush-score__value">{totalScore}</span>
        {isPerfect && state.puzzleCount > 0 && (
          <span className="rush-score__perfect" title="Perfect run!">
            ✨
          </span>
        )}
      </div>

      <div className="rush-score__streak">
        <span className="rush-score__streak-label">Streak</span>
        <span className="rush-score__streak-value">
          {currentStreak}
          {currentStreak >= 3 && <FireIcon size={14} />}
        </span>
      </div>

      {showBreakdown && lastScore && (
        <div className="rush-score__breakdown" aria-live="polite">
          {lastScore.basePoints > 0 && (
            <span className="rush-score__breakdown-item rush-score__breakdown-item--base">
              {formatScore(lastScore.basePoints, true)}
            </span>
          )}
          {lastScore.timeBonus > 0 && (
            <span className="rush-score__breakdown-item rush-score__breakdown-item--time">
              {formatScore(lastScore.timeBonus, true)} time
            </span>
          )}
          {lastScore.streakBonus > 0 && (
            <span className="rush-score__breakdown-item rush-score__breakdown-item--streak">
              {formatScore(lastScore.streakBonus, true)} streak
            </span>
          )}
          {lastScore.skipPenalty < 0 && (
            <span className="rush-score__breakdown-item rush-score__breakdown-item--penalty">
              {lastScore.skipPenalty} skip
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact score display for header/HUD.
 */
export function CompactScore({
  score,
  streak,
  className = '',
}: {
  score: number;
  streak: number;
  className?: string;
}): JSX.Element {
  return (
    <div className={`rush-score-compact ${className}`}>
      <span className="rush-score-compact__score">{score}</span>
      {streak > 0 && (
        <span className="rush-score-compact__streak">
          x{streak}
          {streak >= 3 && <FireIcon size={12} />}
        </span>
      )}
    </div>
  );
}

export default Score;
