/**
 * PuzzleSetPlayer — shared component for sequential puzzle solving.
 *
 * Used by CollectionViewPage and DailyChallengePage. Manages loading,
 * pagination, and rendering of a set of puzzles via SolverView.
 *
 * Props accept render functions for headers, navigation, and summaries
 * so each page can customize chrome while sharing core logic.
 *
 * Spec 127: T045–T047, FR-007, FR-034
 * Spec 122: T11.5 (shared player architecture)
 * @module components/PuzzleSetPlayer
 */

import type { VNode, JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo, useRef } from 'preact/hooks';
import type {
  PuzzleSetLoader,
  LoaderStatus,
  StreamingPuzzleSetLoader,
} from '../../services/puzzleLoaders';
import type { PageMode } from '../../types/page-mode';
import { SolverView } from '../Solver/SolverView';
import { GoTipDisplay } from '../Loading/GoTipDisplay';
import { ErrorState } from '../shared/ErrorState';
import { SkeletonLayout } from '../Loading/SkeletonLayout';
import { ChevronLeftIcon } from '../shared/icons';
import { FALLBACK_LEVEL } from '../../lib/levels/level-defaults';
import { getCategoryLevels } from '../../lib/levels/categories';
import { useSettings } from '../../hooks/useSettings';
import { useAutoAdvance } from '../../hooks/useAutoAdvance';
import { ProblemNav, type PuzzleStatus } from '../ProblemNav/ProblemNav';
import { mapIdsToIndexes, findNextUnsolved } from './puzzleSetUtils';

// ============================================================================
// Types
// ============================================================================

/** Info passed to header render function. */
export interface HeaderInfo {
  name: string;
  currentIndex: number;
  totalPuzzles: number;
  onBack?: () => void;
  /** P1-2: Skip forward to next unsolved puzzle. Undefined when all are solved. */
  onSkipToUnsolved?: () => void;
  /** Number of puzzles completed so far (for progress display). */
  completedCount: number;
}

/** Info passed to navigation render function. */
export interface NavigationInfo {
  currentIndex: number;
  totalPuzzles: number;
  completedIndexes: Set<number>;
  /** Indexes of puzzles completed incorrectly (for red dot display). */
  failedIndexes: Set<number>;
  onSelect: (index: number) => void;
}

/** Info passed to summary render function. */
export interface SummaryInfo {
  totalPuzzles: number;
  completedCount: number;
  onBack?: () => void;
}

export interface PuzzleSetPlayerProps {
  /** Loader instance for fetching puzzle set. */
  loader: PuzzleSetLoader;
  /** Starting puzzle index (0-based). */
  startIndex?: number;
  /** Callback when navigating back. */
  onBack?: () => void;
  /** Callback when all puzzles are complete. */
  onAllComplete?: () => void;
  /** Called when any puzzle reaches a terminal state (solved or gave up). */
  onPuzzleComplete?: (puzzleId: string, isCorrect: boolean) => void;
  /** Called when the current puzzle changes (for URL tracking). */
  onPuzzleChange?: (puzzleId: string | null, index?: number) => void;
  /** Custom header renderer. */
  renderHeader?: (info: HeaderInfo) => JSX.Element;
  /** Custom navigation renderer (e.g., PuzzleCarousel). */
  renderNavigation?: (info: NavigationInfo) => JSX.Element;
  /** Custom summary renderer (shown when all complete). */
  renderSummary?: (info: SummaryInfo) => JSX.Element;
  /** Custom empty state renderer (H5: shown when set is empty, e.g. after filtering). */
  renderEmpty?: () => JSX.Element;
  /** Page mode for CSS accent cascade. */
  mode?: PageMode;
  /** CSS class name. */
  className?: string;
  /**
   * P1-1: Pre-completed puzzle IDs from localStorage progress.
   * After loader is ready, these are mapped to indexes for dot display.
   * Enables progress persistence across page reloads.
   */
  initialCompletedIds?: readonly string[];
  /**
   * When true, any wrong answer immediately marks the puzzle as failed
   * and auto-advances to the next puzzle (timed blitz behavior).
   */
  failOnWrong?: boolean;
  /**
   * Delay in ms before auto-advancing after a wrong answer in failOnWrong mode.
   * Defaults to 400ms. Rush mode uses 100ms for snappy transitions.
   */
  failOnWrongDelayMs?: number;
  /**
   * Override global appSettings.autoAdvance at the component level.
   * When false, disables auto-advance even if the user has it enabled globally.
   * When undefined, falls through to global setting.
   */
  autoAdvanceEnabled?: boolean;
  /**
   * When true, SolverView renders in minimal mode (board only, no sidebar).
   */
  minimal?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export function PuzzleSetPlayer({
  loader,
  startIndex = 0,
  onBack,
  onAllComplete,
  onPuzzleComplete,
  onPuzzleChange,
  renderHeader,
  renderNavigation,
  renderSummary,
  renderEmpty,
  mode,
  className = '',
  initialCompletedIds,
  failOnWrong = false,
  failOnWrongDelayMs = 400,
  autoAdvanceEnabled,
  minimal = false,
}: PuzzleSetPlayerProps): VNode {
  const [loaderStatus, setLoaderStatus] = useState<LoaderStatus>('idle');
  const [currentIndex, setCurrentIndex] = useState(startIndex);
  const [currentSgf, setCurrentSgf] = useState<string | null>(null);
  const [sgfError, setSgfError] = useState<string | null>(null);
  const [completedIndexes, setCompletedIndexes] = useState<Set<number>>(new Set());
  const [failedIndexes, setFailedIndexes] = useState<Set<number>>(new Set());
  const [isLoadingSgf, setIsLoadingSgf] = useState(false);
  const [sgfRetryCount, setSgfRetryCount] = useState(0);

  // Auto-advance settings
  const { settings: appSettings } = useSettings();

  // Phase 4 (D3): one-time hint when the user solves their first puzzle in
  // this session and auto-advance is OFF. The hint is dismissible and
  // remembered in localStorage so we never nag a user who has already seen it.
  // Storage key is intentionally namespaced; clearing it re-enables the hint.
  const AUTO_ADV_HINT_KEY = 'yengo:autoAdvanceHintShown';
  const [autoAdvanceHint, setAutoAdvanceHint] = useState<string | null>(null);
  const autoAdvanceHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dismissAutoAdvanceHint = useCallback(() => {
    setAutoAdvanceHint(null);
    if (autoAdvanceHintTimerRef.current) {
      clearTimeout(autoAdvanceHintTimerRef.current);
      autoAdvanceHintTimerRef.current = null;
    }
  }, []);
  useEffect(() => {
    return () => {
      if (autoAdvanceHintTimerRef.current) clearTimeout(autoAdvanceHintTimerRef.current);
    };
  }, []);

  // Load the puzzle set on mount (or when loader changes due to filter change)
  useEffect(() => {
    let cancelled = false;
    // H4: Reset position when loader changes (e.g., filter change in CollectionViewPage)
    setCurrentIndex(startIndex);
    setCompletedIndexes(new Set());
    setFailedIndexes(new Set());
    setCurrentSgf(null);
    setSgfError(null);
    setLoaderStatus('loading'); // Reset to loading to avoid stale error/empty flash

    void (async () => {
      await loader.load();
      if (cancelled) return;
      setLoaderStatus(loader.getStatus());
    })();
    return () => {
      cancelled = true;
    };
  }, [loader]);

  // P1-1: Hydrate completedIndexes from pre-existing progress (e.g. collection
  // progress in localStorage). Runs after loader becomes ready so entry IDs can
  // be mapped to indexes. Merges with any session completions.
  useEffect(() => {
    if (loaderStatus !== 'ready' || !initialCompletedIds || initialCompletedIds.length === 0)
      return;

    const hydrated = mapIdsToIndexes(loader, initialCompletedIds);

    if (hydrated.size > 0) {
      setCompletedIndexes((prev) => {
        if (prev.size === 0) return hydrated;
        const merged = new Set(prev);
        for (const idx of hydrated) merged.add(idx);
        return merged;
      });
    }
  }, [loaderStatus, loader, initialCompletedIds]);

  // Retry handler: re-invokes loader without full page reload
  const handleRetry = useCallback(async () => {
    setLoaderStatus('loading');
    await loader.load();
    setLoaderStatus(loader.getStatus());
  }, [loader]);

  // Load SGF when index changes
  useEffect(() => {
    if (loaderStatus !== 'ready') return;
    let cancelled = false;

    void (async () => {
      setIsLoadingSgf(true);
      setSgfError(null);
      setCurrentSgf(null);

      const result = await loader.getPuzzleSgf(currentIndex);
      if (cancelled) return;

      if (result.success && result.data) {
        setCurrentSgf(result.data);
        // T060: Prefetch next puzzle SGF (cached by loader)
        if (currentIndex < loader.getTotal() - 1) {
          void loader.getPuzzleSgf(currentIndex + 1);
        }
      } else {
        // T046: Show clear error, don't blank page
        setSgfError(result.message ?? 'Failed to load puzzle');
      }
      setIsLoadingSgf(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [loaderStatus, currentIndex, loader, sgfRetryCount]);

  // Streaming loader detection: RC-7 — totalPuzzles starts at first batch size,
  // incremented by loadMore(). For non-streaming loaders this is a no-op.
  const isStreaming =
    'hasMore' in loader && typeof (loader as StreamingPuzzleSetLoader).hasMore === 'function';

  // Streaming: proactively load more puzzles when nearing the end of loaded set
  useEffect(() => {
    if (!isStreaming || loaderStatus !== 'ready') return;
    const streamLoader = loader as StreamingPuzzleSetLoader;
    const remaining = streamLoader.getTotal() - currentIndex - 1;
    if (remaining <= 1 && streamLoader.hasMore()) {
      void streamLoader.loadMore();
    }
  }, [isStreaming, loaderStatus, currentIndex, loader]);

  const totalPuzzles = loader.getTotal();
  // For streaming loaders, never consider "all complete" since more can be loaded
  const allComplete = !isStreaming && completedIndexes.size >= totalPuzzles && totalPuzzles > 0;

  // Ref-based cancelCountdown to break circular dependency:
  // handleNext → cancelCountdown (from useAutoAdvance) → onAdvance → handleNext
  const cancelCountdownRef = useRef<() => void>(() => {});

  // Next puzzle — also cancels any running auto-advance countdown
  const handleNext = useCallback(() => {
    cancelCountdownRef.current();
    if (currentIndex < totalPuzzles - 1) {
      setCurrentIndex((i) => i + 1);
    } else if (allComplete) {
      onAllComplete?.();
    }
  }, [currentIndex, totalPuzzles, allComplete, onAllComplete]);

  // Auto-advance hook — starts countdown after correct solve, fires handleNext
  // RC-6: autoAdvanceEnabled prop overrides global setting without mutating it
  const effectiveAutoAdvance =
    autoAdvanceEnabled !== undefined ? autoAdvanceEnabled : appSettings.autoAdvance;
  const {
    startCountdown,
    cancelCountdown,
    isCountingDown,
    remainingMs,
    totalMs: autoAdvanceTotalMs,
  } = useAutoAdvance({
    enabled: effectiveAutoAdvance,
    delayMs: appSettings.autoAdvanceDelay * 1000,
    onAdvance: handleNext,
  });

  // Keep ref in sync with latest cancelCountdown
  cancelCountdownRef.current = cancelCountdown;

  // Puzzle complete handler
  const handleComplete = useCallback(
    (isCorrect: boolean) => {
      setCompletedIndexes((prev) => {
        const next = new Set(prev);
        next.add(currentIndex);
        return next;
      });

      // Track failures for red dot display
      if (!isCorrect) {
        setFailedIndexes((prev) => {
          const next = new Set(prev);
          next.add(currentIndex);
          return next;
        });
      }

      // Notify parent with puzzle ID and result
      const entry = loader.getEntry(currentIndex);
      const puzzleId = entry?.id ?? `puzzle-${currentIndex}`;
      onPuzzleComplete?.(puzzleId, isCorrect);

      // Auto-advance on correct solve
      if (isCorrect) {
        if (failOnWrong) {
          // Rush/blitz mode: advance immediately (same delay as wrong answers)
          // since useAutoAdvance is disabled in this mode.
          setTimeout(() => {
            if (currentIndex < totalPuzzles - 1) {
              setCurrentIndex((i) => i + 1);
            }
          }, failOnWrongDelayMs);
        } else {
          startCountdown();
          // Phase 4 (D3): if auto-advance is off and this is the user's first
          // correct solve in the set, surface a one-time hint. Skipped if the
          // user has already seen it in any prior session.
          if (!effectiveAutoAdvance && completedIndexes.size === 0) {
            try {
              const seen =
                typeof localStorage !== 'undefined' && localStorage.getItem(AUTO_ADV_HINT_KEY);
              if (!seen) {
                setAutoAdvanceHint(
                  'Auto-advance is off — enable it in Settings to skip ahead automatically.'
                );
                if (typeof localStorage !== 'undefined') {
                  localStorage.setItem(AUTO_ADV_HINT_KEY, '1');
                }
                if (autoAdvanceHintTimerRef.current) clearTimeout(autoAdvanceHintTimerRef.current);
                autoAdvanceHintTimerRef.current = setTimeout(() => setAutoAdvanceHint(null), 6000);
              }
            } catch {
              // localStorage unavailable (private mode etc.) — silently skip.
            }
          }
        }
      }
    },
    [
      currentIndex,
      loader,
      onPuzzleComplete,
      startCountdown,
      failOnWrong,
      failOnWrongDelayMs,
      totalPuzzles,
      effectiveAutoAdvance,
      completedIndexes.size,
    ]
  );

  // Timed blitz: wrong answer → mark failed + auto-advance
  const handleFail = useCallback(() => {
    if (!failOnWrong) return;
    if (completedIndexes.has(currentIndex)) return; // already handled
    handleComplete(false);
    // Brief delay so the user sees the wrong flash, then advance
    setTimeout(() => {
      if (currentIndex < totalPuzzles - 1) {
        setCurrentIndex((i) => i + 1);
      }
    }, failOnWrongDelayMs);
  }, [
    failOnWrong,
    currentIndex,
    completedIndexes,
    handleComplete,
    totalPuzzles,
    failOnWrongDelayMs,
  ]);

  // Skip puzzle (move to next, skipping failed SGF)
  const handleSkip = useCallback(() => {
    cancelCountdownRef.current();
    if (currentIndex < totalPuzzles - 1) {
      setCurrentIndex((i) => i + 1);
    }
  }, [currentIndex, totalPuzzles]);

  // Select specific puzzle (from navigation)
  const handleSelect = useCallback(
    (index: number) => {
      cancelCountdownRef.current();
      if (index >= 0 && index < totalPuzzles) {
        setCurrentIndex(index);
      }
    },
    [totalPuzzles]
  );

  // Retry loading current puzzle SGF (not skip)
  const handleRetrySgf = useCallback(() => {
    setSgfError(null);
    setCurrentSgf(null);
    // Re-trigger the SGF loading effect by incrementing retry counter
    setSgfRetryCount((c) => c + 1);
  }, []);

  // Previous puzzle (UI-034/UI-039)
  const handlePrev = useCallback(() => {
    cancelCountdownRef.current();
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
    }
  }, [currentIndex]);

  // P1-2: Skip to next unsolved puzzle (wraps around)
  // A1: Cancel any running auto-advance countdown to prevent double navigation.
  const handleSkipToUnsolved = useCallback(() => {
    cancelCountdownRef.current();
    const total = loader.getTotal();
    const nextIdx = findNextUnsolved(currentIndex, total, completedIndexes);
    if (nextIdx !== null) {
      setCurrentIndex(nextIdx);
    }
  }, [currentIndex, loader, completedIndexes]);

  // UI-034: Compute ProblemNav statuses
  const puzzleStatuses = useMemo<PuzzleStatus[]>(() => {
    return Array.from({ length: totalPuzzles }, (_, i) => {
      if (completedIndexes.has(i)) {
        return failedIndexes.has(i) ? 'failed' : 'solved';
      }
      return 'unsolved';
    });
  }, [totalPuzzles, completedIndexes, failedIndexes]);

  // UI-034: Compute current streak of consecutive solved puzzles
  const currentStreak = useMemo(() => {
    let streak = 0;
    for (let i = currentIndex; i >= 0; i--) {
      if (completedIndexes.has(i) && !failedIndexes.has(i)) {
        streak++;
      } else {
        break;
      }
    }
    return streak;
  }, [currentIndex, completedIndexes, failedIndexes]);

  const entryMeta = loader.getEntry(currentIndex);

  // Notify parent when current puzzle changes (for URL tracking)
  useEffect(() => {
    if (loaderStatus === 'ready' && entryMeta?.id) {
      onPuzzleChange?.(entryMeta.id, currentIndex);
    }
  }, [currentIndex, loaderStatus, entryMeta?.id, onPuzzleChange]);

  // ── Loading state ──
  if (loaderStatus === 'idle' || loaderStatus === 'loading') {
    return (
      <div className={className}>
        <SkeletonLayout />
      </div>
    );
  }

  // ── Error state ──
  if (loaderStatus === 'error') {
    return (
      <div className={`flex min-h-[50vh] flex-col items-center justify-center p-6 ${className}`}>
        <ErrorState
          message="Failed to load puzzles"
          onRetry={() => void handleRetry()}
          onGoBack={onBack}
          details={loader.getError() ?? undefined}
        />
      </div>
    );
  }

  // ── T047: Empty collection state ──
  if (loaderStatus === 'empty') {
    // H5: Use custom empty renderer if provided (e.g. EmptyFilterState)
    if (renderEmpty) {
      return (
        <div className={className} {...(mode ? { 'data-mode': mode } : {})}>
          {renderEmpty()}
        </div>
      );
    }
    const isTechnique = mode === 'technique';
    const browseHref = `${import.meta.env.BASE_URL}${isTechnique ? 'technique' : 'collections'}`;
    const browseLabel = isTechnique ? 'Browse techniques' : 'Browse collections';
    const emptyMessage = isTechnique
      ? 'No puzzles available for this technique yet.'
      : 'No puzzles available in this collection yet.';
    return (
      <div
        className={`flex min-h-[50vh] flex-col items-center justify-center gap-6 p-6 ${className}`}
      >
        <GoTipDisplay level={FALLBACK_LEVEL} tips={[]} />
        <div className="text-center">
          <p className="mb-4 text-lg text-[var(--color-text-muted)]">{emptyMessage}</p>
          <a
            href={browseHref}
            className="inline-block rounded-full bg-[var(--color-accent)] px-6 py-2 text-sm text-white transition-colors hover:opacity-90"
          >
            {browseLabel}
          </a>
          <p className="mb-4 mt-8 text-sm text-[var(--color-text-muted)]">
            Or try one of these levels:
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {getCategoryLevels('beginner').map((level) => (
              <a
                key={level}
                href={`${import.meta.env.BASE_URL}training/${level}`}
                className="rounded-full bg-[var(--color-bg-secondary)] px-4 py-2 text-sm capitalize text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-accent)] hover:text-white"
              >
                {level}
              </a>
            ))}
          </div>
        </div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-[var(--color-text-muted)] underline"
          >
            <ChevronLeftIcon size={14} /> Back
          </button>
        )}
      </div>
    );
  }

  // ── Summary state (all complete) ──
  if (allComplete && renderSummary) {
    return (
      <div className={className} {...(mode ? { 'data-mode': mode } : {})}>
        {renderHeader?.({
          name: entryMeta?.level ?? 'Puzzles',
          currentIndex,
          totalPuzzles,
          completedCount: completedIndexes.size,
          ...(onBack && { onBack }),
        })}
        {renderSummary({
          totalPuzzles,
          completedCount: completedIndexes.size,
          ...(onBack && { onBack }),
        })}
      </div>
    );
  }

  // ── Normal puzzle-solving state ──
  return (
    <div
      className={`flex min-h-[calc(100vh-3.5rem)] md:max-h-[calc(100vh-3.5rem)] md:overflow-hidden flex-col bg-[var(--color-bg-primary)] ${className}`}
      {...(mode ? { 'data-mode': mode } : {})}
    >
      {/* Header */}
      {renderHeader?.({
        name: entryMeta?.level ?? 'Puzzles',
        currentIndex,
        totalPuzzles,
        completedCount: completedIndexes.size,
        ...(onBack && { onBack }),
        // P1-2: Only offer skip-to-unsolved when there are unsolved puzzles
        ...(!allComplete &&
          completedIndexes.size > 0 && { onSkipToUnsolved: handleSkipToUnsolved }),
      })}

      {/* Navigation */}
      {renderNavigation?.({
        currentIndex,
        totalPuzzles,
        completedIndexes,
        failedIndexes,
        onSelect: handleSelect,
      })}

      {/* Puzzle content — flex-1 fills remaining space after header */}
      <div className="flex-1 flex flex-col min-h-0">
        {isLoadingSgf && (
          <div className="flex flex-1 items-center justify-center">
            <SkeletonLayout />
          </div>
        )}

        {sgfError && (
          <ErrorState
            message="Couldn't load this puzzle"
            onRetry={handleRetrySgf}
            onGoBack={handleSkip}
            details={sgfError}
            className="flex-1"
          />
        )}

        {currentSgf && !isLoadingSgf && (
          <SolverView
            key={entryMeta?.id ?? currentIndex}
            sgf={currentSgf}
            {...(entryMeta?.level && { level: entryMeta.level })}
            {...(entryMeta?.id != null && { puzzleId: entryMeta.id })}
            onComplete={handleComplete}
            {...(failOnWrong && { onFail: handleFail })}
            onNext={handleNext}
            onPrev={currentIndex > 0 ? handlePrev : undefined}
            onSkip={handleSkip}
            {...(isCountingDown && {
              autoAdvanceCountdown: {
                remainingMs,
                totalMs: autoAdvanceTotalMs,
                onCancel: cancelCountdown,
              },
            })}
            minimal={minimal}
            puzzleNav={
              totalPuzzles > 1 ? (
                <ProblemNav
                  totalProblems={totalPuzzles}
                  currentIndex={currentIndex}
                  statuses={puzzleStatuses}
                  onNavigate={handleSelect}
                  onPrev={handlePrev}
                  onNext={handleNext}
                  currentStreak={currentStreak}
                />
              ) : undefined
            }
            puzzleCounter={
              <span className="inline-flex items-center gap-1 px-3.5 py-1 rounded-full bg-[var(--color-bg-secondary)] text-xs font-bold text-[var(--color-text-secondary)] tracking-wide">
                {currentIndex + 1} / {totalPuzzles}
              </span>
            }
          />
        )}
      </div>
      {/* Phase 4 (D3): one-time auto-advance hint toast (dismissible). */}
      {autoAdvanceHint && (
        <div
          role="status"
          aria-live="polite"
          data-testid="auto-advance-hint"
          className="fixed left-1/2 -translate-x-1/2 bottom-[5.5rem] z-50 max-w-[20rem] flex items-center gap-2 px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] text-xs shadow-[var(--shadow-md)] border border-[var(--color-panel-border)]"
        >
          <span className="flex-1">{autoAdvanceHint}</span>
          <button
            type="button"
            onClick={dismissAutoAdvanceHint}
            className="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
            aria-label="Dismiss hint"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

export default PuzzleSetPlayer;
