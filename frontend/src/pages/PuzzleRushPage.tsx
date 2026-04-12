/**
 * PuzzleRushPage — Thin wrapper around PuzzleSetPlayer for timed puzzle rush.
 * @module pages/PuzzleRushPage
 *
 * Delegates puzzle loading/rendering to PuzzleSetPlayer + RushPuzzleLoader.
 * Preserves: useRushSession hook, countdown screen, finished screen, RushOverlay HUD.
 *
 * Spec 125, Task T090 (refactored for DRY compliance)
 */

import type { FunctionalComponent, JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { Button } from '../components/shared/Button';
import { FireIcon } from '../components/shared/icons';
import { PageLayout } from '../components/Layout';
import { getAccuracyColorClass } from '../lib/accuracy-color';
import { RushOverlay } from '../components/Rush';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { HeaderInfo } from '../components/PuzzleSetPlayer';
import { RushPuzzleLoader } from '../services/puzzleLoaders';
import { useRushSession } from '../hooks/useRushSession';
import { recordRushScore } from '../services/progress';

// ============================================================================
// Types
// ============================================================================

export interface PuzzleRushPageProps {
  /** Duration in seconds (180, 300, or 600) */
  durationSeconds?: number | undefined;
  /** Selected level numeric ID from setup, or null for all levels */
  selectedLevelId?: number | null;
  /** Selected tag numeric ID from setup, or null for all tags */
  selectedTagId?: number | null;
  /** Callback to navigate home */
  onNavigateHome: () => void;
  /** Callback to start a new rush */
  onNewRush: () => void;
  /** Test ID for container */
  testId?: string | undefined;
}

type PageState = 'countdown' | 'playing' | 'finished';

// ============================================================================
// Component
// ============================================================================

export const PuzzleRushPage: FunctionalComponent<PuzzleRushPageProps> = ({
  durationSeconds,
  selectedLevelId,
  selectedTagId,
  onNavigateHome,
  onNewRush,
  testId,
}) => {
  const [pageState, setPageState] = useState<PageState>('countdown');
  const [selectedDuration] = useState<number>(durationSeconds ?? 180);
  const [countdownValue, setCountdownValue] = useState(3);

  // Rush session hook — preserved, only rendering changes
  const {
    state: rushState,
    actions,
    isGameOver,
    timeDisplay,
  } = useRushSession({
    duration: selectedDuration,
    startingLives: 3,
    pointsPerPuzzle: 100,
  });

  // Loader for PuzzleSetPlayer (memoized on level/tag)
  const loader = useMemo(
    () => new RushPuzzleLoader(selectedLevelId ?? null, selectedTagId ?? null),
    [selectedLevelId, selectedTagId]
  );

  // Countdown before game start
  useEffect(() => {
    if (pageState !== 'countdown') return;
    const interval = setInterval(() => {
      setCountdownValue((v) => {
        if (v <= 1) {
          clearInterval(interval);
          handleGameStart();
          return 0;
        }
        return v - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [pageState]);

  // Game over detection — record score to progress
  useEffect(() => {
    if (isGameOver && pageState === 'playing') {
      setPageState('finished');
      recordRushScore(rushState.score, selectedDuration);
    }
  }, [isGameOver, pageState, rushState.score, selectedDuration]);

  const handleGameStart = useCallback(() => {
    actions.start();
    setPageState('playing');
  }, [actions]);

  // Handle skip via RushOverlay
  const handleSkip = useCallback(() => {
    actions.skip();
  }, [actions]);

  // Handle quit — record score before finishing
  const handleQuit = useCallback(() => {
    recordRushScore(rushState.score, selectedDuration);
    actions.reset();
    setPageState('finished');
  }, [actions, rushState.score, selectedDuration]);

  // Bridge useRushSession to PSP onPuzzleComplete (T24)
  const handlePuzzleComplete = useCallback(
    (_puzzleId: string, isCorrect: boolean) => {
      if (isCorrect) {
        actions.recordCorrect();
      } else {
        actions.recordWrong();
      }
    },
    [actions]
  );

  // Calculate accuracy
  const totalAttempts = rushState.puzzlesSolved + rushState.puzzlesFailed;
  const accuracy =
    totalAttempts > 0 ? Math.round((rushState.puzzlesSolved / totalAttempts) * 100) : 0;

  // Rush header: RushOverlay HUD (timer, lives, score, controls)
  const renderHeader = useCallback(
    (_info: HeaderInfo): JSX.Element => (
      <RushOverlay
        timeDisplay={timeDisplay}
        timeRemaining={rushState.timeRemaining}
        totalDuration={selectedDuration}
        lives={rushState.lives}
        maxLives={rushState.maxLives}
        score={rushState.score}
        streak={rushState.currentStreak}
        isGameOver={isGameOver}
        onSkip={handleSkip}
        onQuit={handleQuit}
        skipDisabled={rushState.lives <= 1}
      />
    ),
    [timeDisplay, rushState, selectedDuration, isGameOver, handleSkip, handleQuit]
  );

  // Rush summary: finished screen
  const renderSummary = useCallback(
    (): JSX.Element => (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-6">
        <div
          className="w-full max-w-[400px] rounded-xl bg-[var(--color-bg-elevated)] p-8 text-center shadow-lg"
          data-testid="rush-result"
        >
          <h2 className="mb-2 mt-0 text-2xl">Game Over!</h2>
          <p className="mb-6 mt-0 text-[var(--color-text-muted)]">
            {rushState.lives === 0 ? 'Out of lives!' : "Time's up!"}
          </p>
          <div
            className="mb-2 text-[64px] font-bold text-[var(--color-accent)]"
            data-testid="final-score"
          >
            {rushState.score}
          </div>
          <p className="mb-6 mt-0 text-[var(--color-text-muted)]">points</p>
          <div className="my-6 grid grid-cols-2 gap-4 rounded-lg bg-[var(--color-bg-secondary)] p-4">
            <div>
              <div className="text-2xl font-semibold">{rushState.puzzlesSolved}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Solved</div>
            </div>
            <div>
              <div className={`text-2xl font-semibold ${getAccuracyColorClass(accuracy)}`}>
                {accuracy}%
              </div>
              <div className="text-xs text-[var(--color-text-muted)]">Accuracy</div>
            </div>
          </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={onNavigateHome}
              style={{ flex: 1 }}
              data-testid="home-button"
            >
              Go Home
            </Button>
            <Button
              variant="primary"
              onClick={onNewRush}
              style={{ flex: 1 }}
              data-testid="play-again-button"
            >
              <FireIcon size={16} className="inline" /> Play Again
            </Button>
          </div>
        </div>
      </div>
    ),
    [rushState, accuracy, onNavigateHome, onNewRush]
  );

  return (
    <PageLayout variant="single-column" mode="rush">
      <div
        className="relative flex min-h-[calc(100vh-3.5rem)] flex-col"
        data-testid={testId ?? 'puzzle-rush-page'}
      >
        {/* Countdown Screen (T25) */}
        {pageState === 'countdown' && (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-6">
            <div
              className="text-[96px] font-bold leading-none text-[var(--color-accent)]"
              data-testid="countdown-value"
            >
              {countdownValue}
            </div>
            <p className="text-[var(--color-text-muted)]">Get ready!</p>
          </div>
        )}

        {/* Playing Screen — PuzzleSetPlayer with Rush configuration */}
        {pageState === 'playing' && (
          <PuzzleSetPlayer
            loader={loader}
            mode="rush"
            failOnWrong={true}
            failOnWrongDelayMs={100}
            autoAdvanceEnabled={false}
            minimal={true}
            onPuzzleComplete={handlePuzzleComplete}
            onBack={onNavigateHome}
            renderHeader={renderHeader}
            renderSummary={renderSummary}
          />
        )}

        {/* Finished Screen (T25) */}
        {pageState === 'finished' && renderSummary()}
      </div>
    </PageLayout>
  );
};

export default PuzzleRushPage;
