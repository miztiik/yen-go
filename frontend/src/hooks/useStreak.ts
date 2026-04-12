/**
 * useStreak Hook
 * @module hooks/useStreak
 *
 * React hook for managing streak data and state.
 *
 * Covers: FR-023 to FR-026, US4
 */

import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import {
  recordPlay,
  getStreakStats,
  getLocalDateString,
  type StreakStats,
  type StreakUpdateResult,
  type StreakMilestone,
} from '../services/streakManager';

/** Return value from useStreak hook */
export interface UseStreakReturn {
  /** Current streak statistics */
  readonly stats: StreakStats;
  /** Whether streak data is loading */
  readonly isLoading: boolean;
  /** Error message if any */
  readonly error: string | null;
  /** Record a play and update streak */
  readonly recordPlayActivity: () => StreakUpdateResult | null;
  /** Refresh streak data */
  readonly refresh: () => void;
  /** Recently reached milestones (cleared on next refresh) */
  readonly recentMilestones: readonly StreakMilestone[];
  /** Clear recent milestones */
  readonly clearMilestones: () => void;
}

/**
 * Hook for managing daily streak data
 *
 * @example
 * ```tsx
 * function StreakWidget() {
 *   const { stats, recordPlayActivity, recentMilestones } = useStreak();
 *
 *   const handlePuzzleComplete = async () => {
 *     await recordPlayActivity();
 *   };
 *
 *   return (
 *     <div>
 *       <p>Current streak: {stats.currentStreak} days</p>
 *       {stats.isAtRisk && <p>⚠️ Play today to keep your streak!</p>}
 *       {recentMilestones.map(m => (
 *         <p key={m}>🎉 You reached {m} days!</p>
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useStreak(): UseStreakReturn {
  const [stats, setStats] = useState<StreakStats>(() => getStreakStats(getLocalDateString()));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentMilestones, setRecentMilestones] = useState<readonly StreakMilestone[]>([]);

  // Refresh streak data
  const refresh = useCallback(() => {
    setStats(getStreakStats(getLocalDateString()));
  }, []);

  // Load initial data
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Record a play activity
  const recordPlayActivity = useCallback((): StreakUpdateResult | null => {
    setIsLoading(true);
    setError(null);

    try {
      const result = recordPlay(getLocalDateString());

      if (!result.success || !result.data) {
        setError(result.message || 'Failed to record play activity');
        return null;
      }

      const updateResult = result.data;

      // Update stats
      setStats(getStreakStats(getLocalDateString()));

      // Track milestones
      if (updateResult.milestonesReached.length > 0) {
        setRecentMilestones((prev) => [...prev, ...updateResult.milestonesReached]);
      }

      return updateResult;
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Clear recent milestones
  const clearMilestones = useCallback(() => {
    setRecentMilestones([]);
  }, []);

  return useMemo(
    () => ({
      stats,
      isLoading,
      error,
      recordPlayActivity,
      refresh,
      recentMilestones,
      clearMilestones,
    }),
    [stats, isLoading, error, recordPlayActivity, refresh, recentMilestones, clearMilestones]
  );
}

export default useStreak;
