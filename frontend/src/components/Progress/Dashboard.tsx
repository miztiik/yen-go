/**
 * Progress Dashboard Component
 * @module components/Progress/Dashboard
 *
 * Displays user progress including:
 * - Completed puzzles count by difficulty
 * - Unlocked levels
 * - Statistics overview
 * - Streak information
 *
 * Covers: FR-015 to FR-022, US3
 */

import { useState, useEffect, useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import {
  loadProgress,
  getStatistics,
  getStreakData,
} from '../../services/progressTracker';
import type {
  UserProgress,
  UserStatistics,
  StreakData,
  GroupStats,
} from '../../models/progress';
import type { DailyChallengeGroup } from '../../models/level';
import { FireIcon } from '../shared/icons/FireIcon';
import { WarningIcon } from '../shared/icons/WarningIcon';
import { EmptyState } from '../shared/GoQuote';

/** Props for the Dashboard component */
export interface DashboardProps {
  readonly className?: string;
  readonly onLevelSelect?: (levelId: string) => void;
}

/** Daily challenge group display info */
const GROUP_INFO: Record<DailyChallengeGroup, { label: string; icon: string }> = {
  beginner: { label: 'Beginner', icon: '🟢' },
  intermediate: { label: 'Intermediate', icon: '🟡' },
  advanced: { label: 'Advanced', icon: '🔴' },
};

/**
 * Format milliseconds as a human-readable time string
 */
function formatTime(ms: number): string {
  if (ms < 1000) return '< 1s';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Stat card for displaying a single statistic
 */
function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: string | JSX.Element;
}): JSX.Element {
  return (
    <div className="stat-card" role="group" aria-label={label}>
      <span className="stat-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

/**
 * Group statistics row
 */
function GroupStatsRow({
  group,
  stats,
}: {
  group: DailyChallengeGroup;
  stats: GroupStats;
}): JSX.Element {
  const info = GROUP_INFO[group];

  return (
    <tr className={`group-row group-${group}`}>
      <td>
        <span className="group-icon" aria-hidden="true">
          {info.icon}
        </span>
        {info.label}
      </td>
      <td className="stat-cell">{stats.solved}</td>
      <td className="stat-cell">{stats.avgTimeMs > 0 ? formatTime(stats.avgTimeMs) : '-'}</td>
      <td className="stat-cell">{stats.perfectSolves}</td>
    </tr>
  );
}

/**
 * Streak display component
 */
function StreakDisplay({ streakData }: { streakData: StreakData }): JSX.Element {
  const { currentStreak, longestStreak, lastPlayedDate } = streakData;

  return (
    <div className="streak-display" role="region" aria-label="Streak information">
      <h3><FireIcon size={16} /> Daily Streak</h3>
      <div className="streak-stats">
        <div className="streak-current">
          <span className="streak-number">{currentStreak}</span>
          <span className="streak-label">Current</span>
        </div>
        <div className="streak-best">
          <span className="streak-number">{longestStreak}</span>
          <span className="streak-label">Best</span>
        </div>
      </div>
      {lastPlayedDate && (
        <p className="streak-last-played">Last played: {lastPlayedDate}</p>
      )}
    </div>
  );
}

/**
 * Progress Dashboard Component
 *
 * Displays comprehensive user progress including completed puzzles,
 * statistics by difficulty tier, streak information, and unlocked levels.
 */
export function Dashboard({ className, onLevelSelect }: DashboardProps): JSX.Element {
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load progress data on mount
  useEffect(() => {
    const result = loadProgress();
    if (result.success && result.data) {
      setProgress(result.data);
      setStatistics(getStatistics());
      setStreakData(getStreakData());
    } else {
      setError(result.message || 'Failed to load progress');
    }
    setIsLoading(false);
  }, []);

  // Reload progress data
  const refreshProgress = useCallback(() => {
    const result = loadProgress();
    if (result.success && result.data) {
      setProgress(result.data);
      setStatistics(getStatistics());
      setStreakData(getStreakData());
      setError(null);
    }
  }, []);

  // Handle level click
  const handleLevelClick = useCallback(
    (levelId: string) => {
      onLevelSelect?.(levelId);
    },
    [onLevelSelect]
  );

  if (isLoading) {
    return (
      <div className={`dashboard dashboard-loading ${className ?? ''}`} role="status">
        <p>Loading progress...</p>
      </div>
    );
  }

  if (error || !progress || !statistics) {
    return (
      <div className={`dashboard dashboard-error ${className ?? ''}`} role="alert">
        <p><WarningIcon size={14} /> {error || 'Could not load progress data'}</p>
        <button onClick={refreshProgress} className="btn-retry">
          Retry
        </button>
      </div>
    );
  }

  const completedCount = Object.keys(progress.completedPuzzles).length;
  const unlockedCount = progress.unlockedLevels.length;

  return (
    <div className={`dashboard ${className ?? ''}`} role="main" aria-label="Progress Dashboard">
      <header className="dashboard-header">
        <h2>📊 Your Progress</h2>
      </header>

      {/* Overview Stats */}
      <section className="dashboard-overview" aria-label="Overview statistics">
        <StatCard
          label="Puzzles Solved"
          value={statistics.totalSolved}
          icon="✅"
        />
        <StatCard
          label="Total Time"
          value={formatTime(statistics.totalTimeMs)}
          icon="⏱️"
        />
        <StatCard
          label="Perfect Solves"
          value={statistics.perfectSolves}
          icon="⭐"
        />
        <StatCard
          label="Levels Unlocked"
          value={unlockedCount}
          icon="🔓"
        />
      </section>

      {/* Streak Display */}
      {streakData && <StreakDisplay streakData={streakData} />}

      {/* Statistics by Difficulty */}
      <section className="dashboard-difficulty" aria-label="Statistics by difficulty">
        <h3>📈 By Difficulty</h3>
        <table className="difficulty-table" role="table">
          <thead>
            <tr>
              <th scope="col">Difficulty</th>
              <th scope="col">Solved</th>
              <th scope="col">Avg Time</th>
              <th scope="col">Perfect</th>
            </tr>
          </thead>
          <tbody>
            <GroupStatsRow group="beginner" stats={statistics.byDifficulty.beginner} />
            <GroupStatsRow group="intermediate" stats={statistics.byDifficulty.intermediate} />
            <GroupStatsRow group="advanced" stats={statistics.byDifficulty.advanced} />
          </tbody>
        </table>
      </section>

      {/* Unlocked Levels */}
      {unlockedCount > 0 && (
        <section className="dashboard-levels" aria-label="Unlocked levels">
          <h3>🔓 Unlocked Levels</h3>
          <ul className="level-list">
            {progress.unlockedLevels.map((levelId) => (
              <li key={levelId}>
                <button
                  className="level-link"
                  onClick={() => handleLevelClick(levelId)}
                  aria-label={`Go to level ${levelId}`}
                >
                  {levelId}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Empty state */}
      {completedCount === 0 && (
        <section className="dashboard-empty" aria-label="Getting started">
          <EmptyState message="You haven't completed any puzzles yet. Start solving to track your progress!" quoteMode="daily" />
        </section>
      )}
    </div>
  );
}

export default Dashboard;
