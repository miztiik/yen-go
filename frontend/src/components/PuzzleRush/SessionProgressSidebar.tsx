import type { FunctionalComponent } from 'preact';
import { PuzzleCard, type RushPuzzleResult } from './PuzzleCard';
import { getAccuracyColorClass } from '../../lib/accuracy-color';

export interface SessionProgressSidebarProps {
  results: readonly RushPuzzleResult[];
  currentScore: number;
  skipsRemaining: number;
  strikesCount: number;
  maxStrikes: number;
}

/**
 * Sidebar showing Puzzle Rush session progress.
 * Displays score, strikes, skips, and completed puzzles.
 */
export const SessionProgressSidebar: FunctionalComponent<SessionProgressSidebarProps> = ({
  results,
  currentScore,
  skipsRemaining,
  strikesCount,
  maxStrikes,
}) => {
  const correctCount = results.filter((r) => r.success && !r.skipped).length;
  const failedCount = results.filter((r) => !r.success && !r.skipped).length;

  return (
    <div className="flex flex-col w-[280px] bg-[--color-neutral-50] border-l border-[--color-neutral-200] h-full">
      {/* Stats header */}
      <div className="p-4 bg-[--color-bg-panel] border-b border-[--color-neutral-200]">
        {/* Score */}
        <div className="text-center mb-4">
          <div className="text-xs text-[--color-neutral-500]">Score</div>
          <div className="text-[2rem] font-bold text-[--color-mode-rush-border]">
            {currentScore}
          </div>
        </div>

        {/* Strikes */}
        <div className="flex justify-center gap-2 mb-3">
          {Array.from({ length: maxStrikes }).map((_, i) => (
            <span key={i} className={`text-xl ${i < strikesCount ? 'opacity-100' : 'opacity-30'}`}>
              ❌
            </span>
          ))}
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-3 gap-2 text-xs text-center">
          <div>
            <div className="font-semibold text-[--color-mode-rush-border]">{correctCount}</div>
            <div className="text-[--color-neutral-400]">Correct</div>
          </div>
          <div>
            <div className="font-semibold text-[--color-error]">{failedCount}</div>
            <div className="text-[--color-neutral-400]">Wrong</div>
          </div>
          <div>
            <div className="font-semibold text-[--color-neutral-500]">{skipsRemaining}</div>
            <div className="text-[--color-neutral-400]">Skips</div>
          </div>
        </div>
      </div>

      {/* Session heading */}
      <div className="px-4 py-3 border-b border-[--color-neutral-200] font-semibold text-sm text-[--color-neutral-700]">
        Session Progress
      </div>

      {/* Results list */}
      <div className="flex-1 overflow-y-auto p-2">
        {results.length === 0 ? (
          <div className="px-4 py-8 text-center text-[--color-neutral-400] text-sm">
            Solve puzzles to see your progress here
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {[...results].reverse().map((result) => (
              <PuzzleCard key={result.id} result={result} isCompact={results.length > 10} />
            ))}
          </div>
        )}
      </div>

      {/* Summary at bottom */}
      {results.length > 0 && (
        <div className="px-4 py-3 border-t border-[--color-neutral-200] bg-[--color-bg-panel] flex justify-between text-xs text-[--color-neutral-500]">
          <span>{results.length} puzzles</span>
          <span>
            {correctCount > 0 &&
              (() => {
                const acc = Math.round((correctCount / results.length) * 100);
                return <span className={getAccuracyColorClass(acc)}>{acc}% accuracy</span>;
              })()}
          </span>
        </div>
      )}
    </div>
  );
};

export default SessionProgressSidebar;
