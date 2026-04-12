/**
 * StatsPage - displays user statistics and progress.
 * @module pages/StatsPage
 */

import type { JSX } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import type { UserProgress, StatisticsBySkillLevel } from '../types/progress';
import { createDefaultProgress } from '../types/progress';
import {
  getProgressStorage,
  getStatisticsSummary,
  getStorageStatus,
  loadAndRecoverProgress,
} from '../lib/progress';
import { StatCard, StatGrid, StreakDisplay, SkillLevelStats } from '../components/Stats';
import { LEVEL_SLUGS } from '../lib/levels/config';
import type { LevelSlug } from '../lib/levels/config';

/**
 * StatsPage props
 */
export interface StatsPageProps {
  /** Callback to navigate back */
  readonly onBack?: () => void;
}

/**
 * Styles for the StatsPage component.
 */
const styles = {
  page: `
    min-height: 100vh;
    background: var(--background, #f9fafb);
    padding: 16px;
  `,
  header: `
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
  `,
  backButton: `
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 8px;
    border-radius: 8px;
    color: var(--text-primary, #1f2937);
  `,
  title: `
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary, #1f2937);
    margin: 0;
  `,
  section: `
    margin-bottom: 24px;
  `,
  sectionTitle: `
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary, #1f2937);
    margin: 0 0 12px 0;
  `,
  warning: `
    background: var(--warning-bg, #fef3c7);
    border: 1px solid var(--warning-border, #f59e0b);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 0.875rem;
    color: var(--warning-text, #92400e);
  `,
  emptyState: `
    text-align: center;
    padding: 48px 24px;
    color: var(--text-muted, #6b7280);
  `,
  emptyIcon: `
    font-size: 4rem;
    margin-bottom: 16px;
  `,
  emptyTitle: `
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary, #1f2937);
    margin: 0 0 8px 0;
  `,
  emptyDescription: `
    font-size: 0.875rem;
    margin: 0;
  `,
};

/**
 * Create empty skill level stats for display.
 * Derives from config/puzzle-levels.json via Vite JSON import.
 */
function createEmptySkillLevelStats(): StatisticsBySkillLevel {
  const emptyRecord = Object.fromEntries(LEVEL_SLUGS.map((slug) => [slug, 0])) as Record<
    LevelSlug,
    number
  >;

  return {
    puzzlesBySkillLevel: { ...emptyRecord },
    avgTimeBySkillLevel: { ...emptyRecord },
  };
}

/**
 * Calculate skill level stats from progress.
 * Since PuzzleCompletion doesn't store skill level, we estimate from puzzle IDs.
 */
function calculateSkillLevelStatsFromProgress(_progress: UserProgress): StatisticsBySkillLevel {
  // In a real app, we'd need to look up puzzle metadata
  // For now, return empty stats (to be implemented with puzzle lookup)
  return createEmptySkillLevelStats();
}

/**
 * Empty state component.
 */
function EmptyState(): JSX.Element {
  return (
    <div style={styles.emptyState}>
      <div style={styles.emptyIcon}>📊</div>
      <h2 style={styles.emptyTitle}>No statistics yet</h2>
      <p style={styles.emptyDescription}>Start solving puzzles to see your progress here!</p>
    </div>
  );
}

/**
 * StatsPage component - displays user statistics.
 */
export function StatsPage({ onBack }: StatsPageProps): JSX.Element {
  const [progress, setProgress] = useState<UserProgress>(createDefaultProgress());
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Load progress with recovery
    const storage = getProgressStorage();
    const result = loadAndRecoverProgress(() => storage.getRaw());

    if (result.data) {
      setProgress(result.data);
    }

    if (result.warnings.length > 0) {
      setStorageWarning(result.warnings.join(' '));
    }

    // Check storage mode
    const status = getStorageStatus(storage.getMode());
    if (status.warning) {
      setStorageWarning(status.warning);
    }

    setIsLoading(false);
  }, []);

  // Get summary stats
  const summary = getStatisticsSummary(progress);
  const skillLevelStats = calculateSkillLevelStatsFromProgress(progress);
  const hasStats = progress.statistics.totalPuzzlesSolved > 0;

  if (isLoading) {
    return (
      <div class="stats-page" style={styles.page}>
        <p>Loading statistics...</p>
      </div>
    );
  }

  return (
    <div class="stats-page" style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        {onBack && (
          <button style={styles.backButton} onClick={onBack} aria-label="Go back">
            ←
          </button>
        )}
        <h1 style={styles.title}>Statistics</h1>
      </header>

      {/* Storage warning */}
      {storageWarning && (
        <div style={styles.warning} role="alert">
          ⚠️ {storageWarning}
        </div>
      )}

      {!hasStats ? (
        <EmptyState />
      ) : (
        <>
          {/* Streak Section */}
          <section style={styles.section}>
            <StreakDisplay streakData={progress.streakData} />
          </section>

          {/* Overview Stats */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>Overview</h2>
            <StatGrid columns={2}>
              <StatCard
                icon="🧩"
                label="Puzzles Solved"
                value={summary.puzzlesSolved}
                accent="primary"
              />
              <StatCard icon="⏱️" label="Total Time" value={summary.totalTime} />
              <StatCard icon="📈" label="Average Time" value={summary.averageTime} />
              <StatCard
                icon="💡"
                label="Hints Used"
                value={summary.hintsUsed}
                subtitle={`${summary.hintFreePercentage}% without hints`}
              />
            </StatGrid>
          </section>

          {/* Rush Mode */}
          {summary.bestRushScore !== null && (
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>Rush Mode</h2>
              <StatGrid columns={1}>
                <StatCard
                  icon="🏃"
                  label="Best Rush Score"
                  value={summary.bestRushScore}
                  accent="success"
                  size="large"
                />
              </StatGrid>
            </section>
          )}

          {/* Skill Level Breakdown */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>By Skill Level</h2>
            <SkillLevelStats stats={skillLevelStats} />
          </section>
        </>
      )}
    </div>
  );
}

export default StatsPage;
