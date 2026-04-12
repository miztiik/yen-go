/**
 * RandomChallengePage — Thin wrapper around PuzzleSetPlayer for random puzzles.
 * @module pages/RandomChallengePage
 *
 * Delegates all shared logic to PuzzleSetPlayer + RandomPuzzleLoader.
 * Provides random-specific header, summary, and page chrome.
 */

import type { FunctionalComponent, JSX } from 'preact';
import { useState, useMemo, useCallback } from 'preact/hooks';
import { Button } from '../components/shared/Button';
import { getAccuracyColorClass } from '../lib/accuracy-color';
import { PageLayout } from '../components/Layout/PageLayout';
import { DiceIcon } from '../components/shared/icons/DiceIcon';
import { TrophyIcon } from '../components/shared/icons/TrophyIcon';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { HeaderInfo, SummaryInfo } from '../components/PuzzleSetPlayer';
import { RandomPuzzleLoader } from '../services/puzzleLoaders';
import type { SkillLevel } from '../models/collection';
import { getSkillLevelInfo } from '../models/collection';

export interface RandomChallengePageProps {
  /** Starting difficulty level for random puzzles */
  level: SkillLevel;
  /** Optional tag slug for filtering */
  tagSlug?: string | null;
  /** Callback to navigate home */
  onNavigateHome: () => void;
}

/**
 * RandomChallengePage — Random puzzle solving via PuzzleSetPlayer.
 * Uses RandomPuzzleLoader (StreamingPuzzleSetLoader) for infinite puzzle supply.
 */
export const RandomChallengePage: FunctionalComponent<RandomChallengePageProps> = ({
  level,
  tagSlug,
  onNavigateHome,
}) => {
  const [correctCount, setCorrectCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  const loader = useMemo(() => new RandomPuzzleLoader(level, tagSlug), [level, tagSlug]);

  const levelInfo = getSkillLevelInfo(level);
  const accuracy = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;

  const handlePuzzleComplete = useCallback((_puzzleId: string, isCorrect: boolean) => {
    setTotalCount((c) => c + 1);
    if (isCorrect) setCorrectCount((c) => c + 1);
  }, []);

  const renderHeader = useCallback(
    (info: HeaderInfo): JSX.Element => (
      <div className="bg-gradient-to-br from-[var(--color-mode-random-border)] to-[var(--color-mode-random-text)] px-4 py-4 text-[var(--color-bg-panel)]">
        <div className="mx-auto flex max-w-[800px] items-center justify-between">
          <div className="flex items-center gap-3">
            {info.onBack && (
              <button
                type="button"
                className="flex items-center justify-center rounded-md border-none bg-transparent p-1 text-inherit hover:bg-white/20"
                onClick={info.onBack}
                aria-label="Back"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>
            )}
            <div>
              <h1 className="m-0 text-lg font-semibold">Random Challenge</h1>
              <div className="mt-1 text-sm opacity-90">{levelInfo?.name ?? level} Level</div>
            </div>
          </div>
          <div className="flex gap-6 text-sm">
            <div className="text-center">
              <div className="font-semibold">{totalCount}</div>
              <div className="text-sm opacity-80">Puzzles</div>
            </div>
            <div className="text-center">
              <div className="font-semibold">{accuracy}%</div>
              <div className="text-sm opacity-80">Accuracy</div>
            </div>
          </div>
        </div>
      </div>
    ),
    [levelInfo, level, totalCount, accuracy]
  );

  const renderSummary = useCallback(
    (info: SummaryInfo): JSX.Element => (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-8">
        <div className="flex w-full max-w-[400px] flex-col items-center gap-6 rounded-lg bg-[var(--color-bg-primary)] p-8 text-center shadow-md">
          <div className="leading-none">
            {correctCount > totalCount / 2 ? (
              <TrophyIcon size={48} className="text-[var(--color-success)]" />
            ) : (
              <DiceIcon size={48} className="text-[var(--color-warning)]" />
            )}
          </div>
          <div className="flex w-full gap-6 rounded-md bg-[var(--color-bg-secondary)] p-4">
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-[var(--color-text-primary)]">
                {correctCount}/{totalCount}
              </div>
              <div className="text-sm text-[var(--color-text-muted)]">Correct</div>
            </div>
            <div className="flex-1 text-center">
              <div className={`text-xl font-bold ${getAccuracyColorClass(accuracy)}`}>
                {accuracy}%
              </div>
              <div className="text-sm text-[var(--color-text-muted)]">Accuracy</div>
            </div>
          </div>
          <div className="flex w-full gap-3">
            <Button variant="secondary" onClick={info.onBack ?? onNavigateHome} className="flex-1">
              Go Home
            </Button>
            <Button variant="primary" onClick={() => window.location.reload()} className="flex-1">
              <span className="inline-flex items-center gap-1.5">
                <DiceIcon size={16} color="currentColor" />
                Another Random
              </span>
            </Button>
          </div>
        </div>
      </div>
    ),
    [correctCount, totalCount, accuracy, onNavigateHome]
  );

  return (
    <PageLayout mode="random">
      <PuzzleSetPlayer
        loader={loader}
        mode="random"
        onBack={onNavigateHome}
        onPuzzleComplete={handlePuzzleComplete}
        renderHeader={renderHeader}
        renderSummary={renderSummary}
      />
    </PageLayout>
  );
};

export default RandomChallengePage;
