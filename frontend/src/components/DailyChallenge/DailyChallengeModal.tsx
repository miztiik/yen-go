/**
 * DailyChallengeModal Component
 * @module components/DailyChallenge/DailyChallengeModal
 *
 * Modal for daily challenge with mode selection and progress display.
 * Supports both v1.0 (legacy) and v2.0 (timed sets) formats.
 *
 * Covers: FR-030, FR-031, FR-032
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { Modal } from '../shared/Modal';
import { DailyCountdown } from './DailyCountdown';
import { DailySummary } from './DailySummary';
import { GoQuote } from '../shared/GoQuote';
import { getTodaysChallenge, detectDailyVersion, getTimedSetsInfo } from '@/services/dailyChallengeService';
import { getDailyProgress } from '@/services/progressTracker';
import type { DailyChallengeMode, DailyProgress } from '@/models/dailyChallenge';
import type { DailyIndex } from '@/types/indexes';

export interface DailyChallengeModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Callback to close modal */
  onClose: () => void;
  /** Callback when mode is selected to start challenge
   * @param mode - Challenge mode (standard/timed)
   * @param date - Challenge date
   * @param timedSetNumber - Optional set number for v2.0 timed mode (1, 2, 3...)
   */
  onStartChallenge: (mode: DailyChallengeMode, date: string, timedSetNumber?: number) => void;
  /** Custom className */
  className?: string | undefined;
}

interface ModalState {
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** Challenge data */
  challenge: DailyIndex | null;
  /** User's progress */
  progress: DailyProgress | null;
  /** Show summary view */
  showSummary: boolean;
  /** Challenge version (1.0 or 2.0) */
  version: '1.0' | '2.0';
  /** Timed sets info for v2.0 */
  timedSets: { setNumber: number; puzzleCount: number }[];
}

const DAILY_INITIAL_STATE: ModalState = {
  isLoading: true,
  error: null,
  challenge: null,
  progress: null,
  showSummary: false,
  version: '1.0',
  timedSets: [],
};

/**
 * Format date for display
 */
function formatDisplayDate(date: string): string {
  try {
    const d = new Date(date + 'T00:00:00');
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
 * DailyChallengeModal - Modal for starting daily challenge
 * Supports v1.0 (legacy) and v2.0 (timed sets) formats
 */
export function DailyChallengeModal({
  isOpen,
  onClose,
  onStartChallenge,
  className = '',
}: DailyChallengeModalProps): JSX.Element {
  const [state, setState] = useState<ModalState>(DAILY_INITIAL_STATE);

  // Load challenge data when modal opens
  useEffect(() => {
    if (!isOpen) return;

    const loadData = (): void => {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const result = getTodaysChallenge();
      
      if (!result.success || !result.data) {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: result.message ?? 'Daily challenge not available',
          challenge: null,
          version: '1.0',
          timedSets: [],
        }));
        return;
      }

      // Detect version and get timed sets info
      const version = detectDailyVersion(result.data);
      const timedSets = getTimedSetsInfo(result.data);

      // Load progress
      const progressResult = getDailyProgress(result.data.date);
      const progress: DailyProgress | null = progressResult.success && progressResult.data ? progressResult.data : null;

      setState(prev => ({
        ...prev,
        isLoading: false,
        challenge: result.data ?? null,
        progress,
        version,
        timedSets,
      }));
    };

    loadData();
  }, [isOpen]);

  const handleModeSelect = useCallback((mode: DailyChallengeMode): void => {
    if (state.challenge) {
      // For standard mode or v1.0 timed, no set number needed
      onStartChallenge(mode, state.challenge.date);
    }
  }, [state.challenge, onStartChallenge]);

  /** Handle timed set selection for v2.0 format */
  const handleTimedSetSelect = useCallback((setNumber: number): void => {
    if (state.challenge) {
      onStartChallenge('timed', state.challenge.date, setNumber);
    }
  }, [state.challenge, onStartChallenge]);

  const handleContinue = useCallback((): void => {
    if (state.challenge) {
      onStartChallenge('standard', state.challenge.date);
    }
  }, [state.challenge, onStartChallenge]);

  const toggleSummary = useCallback((): void => {
    setState(prev => ({ ...prev, showSummary: !prev.showSummary }));
  }, []);

  const { isLoading, error, challenge, progress, showSummary, version, timedSets } = state;

  // Calculate progress stats
  const completedCount = progress?.completed.length ?? 0;
  const standardPuzzles = challenge?.standard?.puzzles ?? [];
  const totalCount = standardPuzzles.length;
  const isComplete = completedCount >= totalCount && totalCount > 0;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const isInProgress = completedCount > 0 && !isComplete;

  // Check if v2.0 with multiple timed sets
  const hasTimedSets = version === '2.0' && timedSets.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Daily Challenge"
      className={className}
    >
      <div className="p-6 max-h-[80vh] overflow-y-auto">
        {isLoading && (
          <div className="flex justify-center items-center min-h-[200px] text-[--color-neutral-400]">Loading...</div>
        )}

        {!isLoading && error && (
          <div className="text-center px-4 py-8">
            <p className="text-xl font-semibold text-[--color-neutral-900] mb-2">Coming Soon</p>
            <p className="text-sm text-[--color-neutral-500] mb-4">
              Our puzzle masters are hard at work crafting today's challenge. 
              Check back shortly — good things take time.
            </p>
            <GoQuote mode="daily" size="sm" />
            <div className="mb-6 text-center">
              <DailyCountdown size="md" />
            </div>
          </div>
        )}

        {!isLoading && challenge && !showSummary && (
          <>
            {/* Header */}
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-[--color-neutral-900] m-0 mb-1">Today's Challenge</h2>
              <p className="text-base text-[--color-neutral-500] m-0">{formatDisplayDate(challenge.date)}</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="bg-[--color-neutral-50] rounded-lg p-4 text-center">
                <span className="text-2xl font-bold text-[--color-neutral-900] block">{totalCount}</span>
                <span className="text-xs text-[--color-neutral-500] uppercase tracking-wider">Puzzles</span>
              </div>
              <div className="bg-[--color-neutral-50] rounded-lg p-4 text-center">
                <span className="text-2xl font-bold text-[--color-neutral-900] block">{completedCount}</span>
                <span className="text-xs text-[--color-neutral-500] uppercase tracking-wider">Completed</span>
              </div>
              <div className="bg-[--color-neutral-50] rounded-lg p-4 text-center">
                <span className="text-2xl font-bold text-[--color-neutral-900] block">{progressPercent}%</span>
                <span className="text-xs text-[--color-neutral-500] uppercase tracking-wider">Progress</span>
              </div>
            </div>

            {/* Progress Bar */}
            {completedCount > 0 && (
              <div className="mb-6">
                <span className="text-sm text-[--color-neutral-600] mb-2 block">
                  {isComplete ? 'Challenge Complete!' : `${completedCount} of ${totalCount} puzzles solved`}
                </span>
                <div className="h-2 bg-[--color-neutral-200] rounded overflow-hidden">
                  <div className="h-full bg-[--color-success-solid] rounded transition-[width] duration-300 ease-in-out" style={{ width: `${progressPercent}%` }} />
                </div>
              </div>
            )}

            {/* Mode Selection (not shown if complete) */}
            {!isComplete && !isInProgress && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-[--color-neutral-700] mb-3">Select Mode</h3>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    className="bg-[--color-bg-panel] border-2 border-[--color-neutral-200] rounded-xl p-5 cursor-pointer text-center transition-all hover:border-[--color-info-solid] hover:bg-[--color-mode-daily-light]"
                    onClick={() => handleModeSelect('standard')}
                  >
                    <span className="text-[2rem] mb-2 block">📝</span>
                    <span className="text-base font-semibold text-[--color-neutral-900] mb-1 block">Standard</span>
                    <span className="text-xs text-[--color-neutral-500]">Take your time, no pressure</span>
                  </button>
                  
                  {/* v1.0 format: single timed button */}
                  {!hasTimedSets && (
                    <button
                      type="button"
                      className="bg-[--color-bg-panel] border-2 border-[--color-neutral-200] rounded-xl p-5 cursor-pointer text-center transition-all hover:border-[--color-info-solid] hover:bg-[--color-mode-daily-light]"
                      onClick={() => handleModeSelect('timed')}
                    >
                      <span className="text-[2rem] mb-2 block">⏱️</span>
                      <span className="text-base font-semibold text-[--color-neutral-900] mb-1 block">Timed</span>
                      <span className="text-xs text-[--color-neutral-500]">Race against the clock</span>
                    </button>
                  )}
                </div>

                {/* v2.0 format: multiple timed sets */}
                {hasTimedSets && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold text-[--color-neutral-700] mb-3">⏱️ Timed Sets</h3>
                    <div className="flex gap-3 flex-wrap justify-center">
                      {timedSets.map((set) => (
                        <button
                          key={set.setNumber}
                          type="button"
                          className="px-5 py-3 bg-[--color-neutral-50] border-2 border-[--color-neutral-200] rounded-lg cursor-pointer text-center min-w-[100px] transition-all hover:border-[--color-warning-border] hover:bg-[--color-mode-daily-light]"
                          onClick={() => handleTimedSetSelect(set.setNumber)}
                        >
                          <span className="text-xl font-bold text-[--color-neutral-900] block mb-1">Set {set.setNumber}</span>
                          <span className="text-xs text-[--color-neutral-500]">{set.puzzleCount} puzzles</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Continue Button (if in progress) */}
            {isInProgress && (
              <button
                type="button"
                className="w-full p-3 bg-[--color-info-solid] text-[--color-bg-panel] border-none rounded-lg cursor-pointer text-sm font-semibold mt-4"
                onClick={handleContinue}
              >
                Continue Challenge
              </button>
            )}

            {/* View Summary Button (if complete) */}
            {isComplete && (
              <button
                type="button"
                className="w-full p-3 bg-[--color-neutral-100] text-[--color-neutral-700] border border-[--color-neutral-200] rounded-lg cursor-pointer text-sm font-medium mt-4"
                onClick={toggleSummary}
              >
                View Summary
              </button>
            )}

            {/* Next Challenge Countdown */}
            <div className="mt-6 text-center">
              <DailyCountdown size="sm" />
            </div>
          </>
        )}

        {!isLoading && challenge && showSummary && progress && (
          <DailySummary
            date={challenge.date}
            totalPuzzles={totalCount}
            completedPuzzles={completedCount}
            performance={progress.performance}
            onGoHome={toggleSummary}
          />
        )}
      </div>
    </Modal>
  );
}

export default DailyChallengeModal;
