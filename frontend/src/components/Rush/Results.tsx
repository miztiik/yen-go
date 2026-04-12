/**
 * Rush mode results display component.
 * Shows final score, statistics, and rank.
 * @module components/Rush/Results
 */
import type { JSX } from 'preact';
import { calculateRank, formatDetailedTime } from '../../lib/rush';
import type { QueueState } from '../../lib/rush';
import { FireIcon } from '../shared/icons/FireIcon';
import './Results.css';

export interface ResultsProps {
  /** Final score */
  score: number;
  /** Total time taken in ms */
  totalTimeMs: number;
  /** Queue state with completion info */
  queueState: QueueState;
  /** Longest streak achieved */
  longestStreak: number;
  /** Whether it was a perfect run */
  isPerfect: boolean;
  /** Whether time ran out */
  timedOut: boolean;
  /** Callback to play again */
  onPlayAgain?: () => void;
  /** Callback to go home */
  onHome?: () => void;
  /** Optional class name */
  className?: string;
}

/**
 * Rush mode results display.
 */
export function Results({
  score,
  totalTimeMs,
  queueState,
  longestStreak,
  isPerfect,
  timedOut,
  onPlayAgain,
  onHome,
  className = '',
}: ResultsProps): JSX.Element {
  const rankInfo = calculateRank(score);
  const { correctCount, skippedCount, completedCount } = queueState;
  const accuracy = completedCount > 0 ? Math.round((correctCount / completedCount) * 100) : 0;

  return (
    <div className={`rush-results ${className}`}>
      <div className="rush-results__header">
        <h2 className="rush-results__title">{timedOut ? "Time's Up!" : 'Rush Complete!'}</h2>
        {isPerfect && <div className="rush-results__perfect-badge">✨ Perfect Run! ✨</div>}
      </div>

      <div className="rush-results__rank">
        <span className="rush-results__rank-letter">{rankInfo.rank}</span>
        <span className="rush-results__rank-title">{rankInfo.title}</span>
      </div>

      <div className="rush-results__score">
        <span className="rush-results__score-label">Final Score</span>
        <span className="rush-results__score-value">{score}</span>
        {rankInfo.nextRank && (
          <span className="rush-results__next-rank">
            {rankInfo.nextRankScore! - score} more for {rankInfo.nextRank} rank
          </span>
        )}
      </div>

      <div className="rush-results__stats">
        <div className="rush-results__stat">
          <span className="rush-results__stat-label">Puzzles Solved</span>
          <span className="rush-results__stat-value">{correctCount}</span>
        </div>
        <div className="rush-results__stat">
          <span className="rush-results__stat-label">Accuracy</span>
          <span className="rush-results__stat-value">{accuracy}%</span>
        </div>
        <div className="rush-results__stat">
          <span className="rush-results__stat-label">Best Streak</span>
          <span className="rush-results__stat-value">
            {longestStreak}
            {longestStreak >= 3 && <FireIcon size={14} />}
          </span>
        </div>
        <div className="rush-results__stat">
          <span className="rush-results__stat-label">Time Used</span>
          <span className="rush-results__stat-value">{formatDetailedTime(totalTimeMs)}</span>
        </div>
        {skippedCount > 0 && (
          <div className="rush-results__stat rush-results__stat--negative">
            <span className="rush-results__stat-label">Skipped</span>
            <span className="rush-results__stat-value">{skippedCount}</span>
          </div>
        )}
      </div>

      <div className="rush-results__actions">
        {onPlayAgain && (
          <button
            type="button"
            className="rush-results__button rush-results__button--primary"
            onClick={onPlayAgain}
          >
            Play Again
          </button>
        )}
        {onHome && (
          <button
            type="button"
            className="rush-results__button rush-results__button--secondary"
            onClick={onHome}
          >
            Home
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Compact results summary (for history display).
 */
export function ResultsSummary({
  score,
  puzzlesSolved,
  rank,
  date,
  className = '',
}: {
  score: number;
  puzzlesSolved: number;
  rank: string;
  date: Date | string;
  className?: string;
}): JSX.Element {
  const formattedDate = new Date(date).toLocaleDateString();

  return (
    <div className={`rush-results-summary ${className}`}>
      <span className="rush-results-summary__rank">{rank}</span>
      <span className="rush-results-summary__score">{score}</span>
      <span className="rush-results-summary__puzzles">{puzzlesSolved} solved</span>
      <span className="rush-results-summary__date">{formattedDate}</span>
    </div>
  );
}

export default Results;
