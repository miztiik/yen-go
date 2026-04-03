/**
 * DailyChallengePage Component
 * @module pages/DailyChallengePage
 *
 * Thin wrapper around PuzzleSetPlayer for daily challenge puzzle solving.
 * Provides daily-specific header (branding, date, mode badge),
 * PuzzleCarousel navigation, and DailySummary on completion.
 *
 * Covers: FR-030 to FR-041 (Daily Challenge)
 *
 * Refactored: Spec 122 T11.7 — Migrated from 674-line monolith to thin wrapper.
 * All shared logic now lives in PuzzleSetPlayer (T11.5).
 */

import type { JSX } from 'preact';
import { useState, useMemo, useCallback, useEffect, useRef } from 'preact/hooks';
import { FALLBACK_LEVEL } from '../lib/levels/level-defaults';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { HeaderInfo, NavigationInfo, SummaryInfo } from '../components/PuzzleSetPlayer';
import { PuzzleCarousel } from '../components/PuzzleNavigation/PuzzleCarousel';
import type { PuzzleIndicator } from '../components/PuzzleNavigation/PuzzleCarousel';
import { DailySummary } from '../components/DailyChallenge/DailySummary';
import { ChallengeTimer, BLITZ_DURATION_MS } from '../components/DailyChallenge/ChallengeTimer';
import { DailyPuzzleLoader } from '../services/puzzleLoaders';
import type { DailyChallengeMode, DailyPerformanceData } from '../models/dailyChallenge';
import { recordDailyPuzzleCompletion, getDailyProgress, updateDailyProgress } from '../services/progress';
import { recordPlay } from '../services/streakManager';
import { PageLayout } from '../components/Layout/PageLayout';

// ============================================================================
// Types
// ============================================================================

export interface DailyChallengePageProps {
  /** Challenge date (YYYY-MM-DD) */
  date: string;
  /** Challenge mode */
  mode?: DailyChallengeMode | undefined;
  /** Callback when navigating back */
  onBack?: () => void;
  /** Callback when challenge is complete */
  onComplete?: () => void;
  /** CSS class name */
  className?: string | undefined;
}



// ============================================================================
// Helpers
// ============================================================================

function formatDate(date: string): string {
  try {
    const d = new Date(date + 'T00:00:00');
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return date;
  }
}

// ============================================================================
// Component
// ============================================================================

/**
 * DailyChallengePage — Daily challenge puzzle solving view.
 * Delegates all shared logic to PuzzleSetPlayer.
 */
export function DailyChallengePage({
  date,
  mode = 'standard',
  onBack,
  onComplete,
  className,
}: DailyChallengePageProps): JSX.Element {
  const displayDate = formatDate(date);

  // Create loader (memoized)
  const loader = useMemo(() => new DailyPuzzleLoader(date, mode), [date, mode]);

  // Timed mode state
  const [timeUp, setTimeUp] = useState(false);
  const puzzleStartRef = useRef(Date.now());
  // Track puzzles already recorded to prevent double-counting on replay
  const recordedPuzzlesRef = useRef(new Set<string>());
  // Key to force PuzzleSetPlayer remount on Play Again
  const [playKey, setPlayKey] = useState(0);

  const handleTimeUp = useCallback(() => {
    setTimeUp(true);
  }, []);

  const handlePlayAgain = useCallback(() => {
    // Reset daily performance in localStorage for fresh replay
    updateDailyProgress(date, {
      completed: [],
      performance: { accuracyByLevel: {}, totalTimeMs: 0 },
    });
    setCompletedIds([]);
    setTimeUp(false);
    puzzleStartRef.current = Date.now();
    recordedPuzzlesRef.current.clear();
    setPlayKey(k => k + 1);
  }, [date]);

  // A5: Hydrate completed puzzle IDs from localStorage for returning users
  const [completedIds, setCompletedIds] = useState<readonly string[]>([]);
  useEffect(() => {
    const result = getDailyProgress(date);
    if (result.success && result.data) {
      setCompletedIds(result.data.completed);
    }
  }, [date]);

  // Progress tracking: record daily puzzle completion + streak
  // Guard against double-counting when replaying already-completed puzzles
  const handlePuzzleComplete = useCallback((puzzleId: string, isCorrect: boolean) => {
    if (recordedPuzzlesRef.current.has(puzzleId)) return;
    recordedPuzzlesRef.current.add(puzzleId);
    // Find the correct level by scanning loader entries for matching puzzle ID
    let level = FALLBACK_LEVEL;
    const total = loader.getTotal();
    for (let i = 0; i < total; i++) {
      const e = loader.getEntry(i);
      if (e?.id === puzzleId) {
        level = e.level ?? FALLBACK_LEVEL;
        break;
      }
    }
    const timeMs = Date.now() - puzzleStartRef.current;
    recordDailyPuzzleCompletion(date, puzzleId, level, isCorrect, timeMs);
    puzzleStartRef.current = Date.now();
    if (isCorrect) {
      recordPlay();
    }
  }, [date, loader]);

  // Header renderer — contextual info only (AppHeader provides branding) (T031)
  const renderHeader = (info: HeaderInfo): JSX.Element => (
    <header className="flex items-center justify-between px-4 pb-2 pt-4">
      <div className="flex items-center gap-3">
        {info.onBack && (
          <button
            className="flex items-center justify-center rounded-md border-none bg-transparent p-1 text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]"
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
          <p className="m-0 text-sm font-medium text-[var(--color-text-primary)]">
            Daily Challenge
          </p>
          <p className="m-0 text-xs text-[var(--color-text-muted)]">{displayDate}</p>
        </div>
      </div>
      {mode === 'timed' && !timeUp && info.completedCount < loader.getTotal() ? (
        <ChallengeTimer durationMs={BLITZ_DURATION_MS} onTimeUp={handleTimeUp} />
      ) : (
        <span
          className={`rounded-md px-2 py-1 text-xs font-medium ${
            mode === 'timed'
              ? 'bg-[var(--color-accent-muted)] text-[var(--color-text-secondary)]'
              : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
          }`}
        >
          {mode === 'timed' ? 'Timed' : 'Standard'}
        </span>
      )}
    </header>
  );

  // Navigation renderer
  const renderNavigation = (info: NavigationInfo): JSX.Element => {
    // Construct puzzle list from loader
    const puzzles = Array.from({ length: info.totalPuzzles }, (_, i) => loader.getEntry(i))
      .filter((p): p is NonNullable<typeof p> => p !== null);

    const indicators: PuzzleIndicator[] = puzzles.map((puzzle, index) => ({
      index,
      id: puzzle.id,
      status: info.failedIndexes.has(index)
        ? 'incorrect' as const
        : info.completedIndexes.has(index)
          ? 'correct' as const
          : index === info.currentIndex
            ? 'current' as const
            : 'unsolved' as const
    }));

    return (
      <div className="border-t border-[var(--color-bg-tertiary)] bg-[var(--color-bg-primary)] px-4 py-2">
        <PuzzleCarousel
          puzzles={indicators}
          currentIndex={info.currentIndex}
          onPuzzleClick={info.onSelect}
          autoScrollToCurrent={true}
          size="sm"
        />
      </div>
    );
  };

  // Read real performance from localStorage
  const getPerformance = useCallback((): DailyPerformanceData => {
    const result = getDailyProgress(date);
    const saved = result.success ? result.data?.performance : undefined;
    const perf: DailyPerformanceData = saved ?? { accuracyByLevel: {}, totalTimeMs: 0 };
    if (mode === 'timed' && perf.timedHighScore === undefined) {
      const correct = Object.values(perf.accuracyByLevel)
        .reduce((sum, d) => sum + d.correct, 0);
      return { ...perf, timedHighScore: correct };
    }
    return perf;
  }, [date, mode]);

  // Summary renderer
  const renderSummary = (info: SummaryInfo): JSX.Element => {
    const performance = getPerformance();

    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <DailySummary
          date={date}
          totalPuzzles={info.totalPuzzles}
          completedPuzzles={info.completedCount}
          performance={performance}
          isTimedMode={mode === 'timed'}
          onPlayAgain={handlePlayAgain}
          {...(info.onBack ? { onGoHome: info.onBack } : {})}
        />
      </div>
    );
  };

  // Timed mode: when time is up, show summary immediately
  if (timeUp) {
    const performance = getPerformance();
    const total = loader.getTotal();
    // Derive puzzle count from performance data when loader isn't ready (HMR/race)
    const perfTotal = performance.accuracyByLevel
      ? Object.values(performance.accuracyByLevel).reduce((sum, d) => sum + d.total, 0)
      : 0;
    const effectiveTotal = total > 0 ? total : perfTotal;
    const completedCount = total > 0 ? Math.min(total, perfTotal) : perfTotal;
    return (
      <PageLayout mode="daily">
        <div className="flex flex-1 items-center justify-center p-6">
          <DailySummary
            date={date}
            totalPuzzles={effectiveTotal}
            completedPuzzles={completedCount}
            performance={performance}
            isTimedMode={true}
            onPlayAgain={handlePlayAgain}
            {...(onBack ? { onGoHome: onBack } : {})}
          />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout mode="daily">
      <PuzzleSetPlayer
        key={playKey}
        loader={loader}
        mode="daily"
        {...(onBack && { onBack })}
        {...(onComplete && { onAllComplete: onComplete })}
        onPuzzleComplete={handlePuzzleComplete}
        renderHeader={renderHeader}
        renderNavigation={renderNavigation}
        renderSummary={renderSummary}
        initialCompletedIds={completedIds}
        {...(mode === 'timed' && { failOnWrong: true })}
        {...(className && { className })}
      />
    </PageLayout>
  );
}

export default DailyChallengePage;
