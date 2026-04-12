/**
 * Achievements Page
 * @module pages/AchievementsPage
 *
 * Displays all achievements with progress and unlock status.
 *
 * Covers: US8 (Achievements)
 */

import type { JSX } from 'preact';
import { useState, useMemo } from 'preact/hooks';
import { ACHIEVEMENTS, type AchievementCategory, type AchievementTier } from '../lib/achievements';
import {
  loadAchievementProgress,
  getUnlockRecord,
  getProgressValue,
  getUnlockedCount,
} from '../lib/achievements';
import { AchievementCard } from '../components/Achievements';
import './AchievementsPage.css';

/**
 * Props for AchievementsPage
 */
export interface AchievementsPageProps {
  /** Callback to go back */
  onBack?: () => void;
  /** Optional class name */
  className?: string;
}

/**
 * Category display info.
 */
const CATEGORY_INFO: Record<AchievementCategory, { name: string; icon: string }> = {
  puzzle: { name: 'Puzzles', icon: '🧩' },
  streak: { name: 'Streaks', icon: '🔥' },
  rush: { name: 'Rush Mode', icon: '⚡' },
  mastery: { name: 'Mastery', icon: '🎯' },
  milestone: { name: 'Milestones', icon: '🏆' },
};

/**
 * Tier filter options.
 */
const TIER_OPTIONS: (AchievementTier | 'all')[] = ['all', 'bronze', 'silver', 'gold', 'platinum'];

/**
 * Styles for AchievementsPage.
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    background:
      'linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 50%, var(--color-bg-tertiary) 100%)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem',
    borderBottom: '1px solid rgba(0, 0, 0, 0.1)',
    background: 'rgba(255, 255, 255, 0.8)',
    backdropFilter: 'blur(8px)',
  },
  backButton: {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    padding: '0.5rem',
    color: 'var(--color-text-primary)',
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
  },
  stats: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
    fontSize: '0.875rem',
    color: 'var(--color-text-secondary)',
  },
  main: {
    flex: 1,
    padding: '1rem',
    maxWidth: '800px',
    margin: '0 auto',
    width: '100%',
  },
  summary: {
    display: 'flex',
    justifyContent: 'center',
    gap: '2rem',
    padding: '1.5rem',
    background: 'rgba(255, 255, 255, 0.6)',
    borderRadius: '12px',
    marginBottom: '1.5rem',
    flexWrap: 'wrap',
  },
  summaryItem: {
    textAlign: 'center',
  },
  summaryValue: {
    display: 'block',
    fontSize: '2rem',
    fontWeight: '700',
    color: 'var(--color-text-primary)',
  },
  summaryLabel: {
    display: 'block',
    fontSize: '0.75rem',
    color: 'var(--color-text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  filters: {
    display: 'flex',
    gap: '0.5rem',
    marginBottom: '1rem',
    flexWrap: 'wrap',
  },
  filterButton: {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '20px',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
    textTransform: 'capitalize',
  },
  filterButtonActive: {
    background: 'var(--color-text-primary)',
    color: 'var(--color-text-inverse)',
  },
  filterButtonInactive: {
    background: 'rgba(255, 255, 255, 0.6)',
    color: 'var(--color-text-secondary)',
  },
  categorySection: {
    marginBottom: '2rem',
  },
  categoryHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '1rem',
  },
  categoryIcon: {
    fontSize: '1.25rem',
  },
  categoryTitle: {
    margin: 0,
    fontSize: '1.125rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
  },
  categoryCount: {
    fontSize: '0.75rem',
    color: 'var(--color-text-secondary)',
    background: 'rgba(0, 0, 0, 0.05)',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  achievementGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  emptyState: {
    textAlign: 'center',
    padding: '3rem 1rem',
    color: 'var(--color-text-secondary)',
  },
};

/**
 * Achievements Page Component.
 */
export function AchievementsPage({ onBack, className = '' }: AchievementsPageProps): JSX.Element {
  const [tierFilter, setTierFilter] = useState<AchievementTier | 'all'>('all');
  const [showUnlockedOnly, setShowUnlockedOnly] = useState(false);

  // Load progress
  const progress = useMemo(() => loadAchievementProgress(), []);

  // Calculate stats
  const totalAchievements = ACHIEVEMENTS.length;
  const unlockedCount = getUnlockedCount(progress);
  const progressPercent = Math.round((unlockedCount / totalAchievements) * 100);

  // Count by tier
  const tierCounts = useMemo(() => {
    const counts: Record<AchievementTier, { total: number; unlocked: number }> = {
      bronze: { total: 0, unlocked: 0 },
      silver: { total: 0, unlocked: 0 },
      gold: { total: 0, unlocked: 0 },
      platinum: { total: 0, unlocked: 0 },
    };

    for (const achievement of ACHIEVEMENTS) {
      counts[achievement.tier].total++;
      if (progress.unlockedIds.includes(achievement.id)) {
        counts[achievement.tier].unlocked++;
      }
    }

    return counts;
  }, [progress]);

  // Filter achievements
  const filteredAchievements = useMemo(() => {
    return ACHIEVEMENTS.filter((a) => {
      if (tierFilter !== 'all' && a.tier !== tierFilter) return false;
      if (showUnlockedOnly && !progress.unlockedIds.includes(a.id)) return false;
      return true;
    });
  }, [tierFilter, showUnlockedOnly, progress]);

  // Group by category
  const categories: AchievementCategory[] = ['puzzle', 'streak', 'rush', 'mastery', 'milestone'];

  return (
    <div className={`achievements-page ${className}`} style={styles.container}>
      <header style={styles.header}>
        {onBack && (
          <button type="button" style={styles.backButton} onClick={onBack} aria-label="Go back">
            ←
          </button>
        )}
        <h1 style={styles.title}>Achievements</h1>
        <div style={styles.stats}>
          {unlockedCount}/{totalAchievements}
        </div>
      </header>

      <main style={styles.main}>
        {/* Summary */}
        <div style={styles.summary}>
          <div style={styles.summaryItem}>
            <span style={styles.summaryValue}>{unlockedCount}</span>
            <span style={styles.summaryLabel}>Unlocked</span>
          </div>
          <div style={styles.summaryItem}>
            <span style={styles.summaryValue}>{progressPercent}%</span>
            <span style={styles.summaryLabel}>Complete</span>
          </div>
          <div style={styles.summaryItem}>
            <span style={styles.summaryValue}>
              {tierCounts.gold.unlocked + tierCounts.platinum.unlocked}
            </span>
            <span style={styles.summaryLabel}>Rare</span>
          </div>
        </div>

        {/* Filters */}
        <div style={styles.filters}>
          {TIER_OPTIONS.map((tier) => (
            <button
              key={tier}
              type="button"
              style={{
                ...styles.filterButton,
                ...(tierFilter === tier ? styles.filterButtonActive : styles.filterButtonInactive),
              }}
              onClick={() => setTierFilter(tier)}
            >
              {tier === 'all' ? 'All' : tier}
            </button>
          ))}
          <button
            type="button"
            style={{
              ...styles.filterButton,
              ...(showUnlockedOnly ? styles.filterButtonActive : styles.filterButtonInactive),
            }}
            onClick={() => setShowUnlockedOnly(!showUnlockedOnly)}
          >
            Unlocked Only
          </button>
        </div>

        {/* Achievement categories */}
        {filteredAchievements.length === 0 ? (
          <div style={styles.emptyState}>
            <p>No achievements match your filters.</p>
          </div>
        ) : (
          categories.map((category) => {
            const categoryAchievements = filteredAchievements.filter(
              (a) => a.category === category
            );
            if (categoryAchievements.length === 0) return null;

            const categoryInfo = CATEGORY_INFO[category];
            const categoryUnlocked = categoryAchievements.filter((a) =>
              progress.unlockedIds.includes(a.id)
            ).length;

            return (
              <section key={category} style={styles.categorySection}>
                <div style={styles.categoryHeader}>
                  <span style={styles.categoryIcon}>{categoryInfo.icon}</span>
                  <h2 style={styles.categoryTitle}>{categoryInfo.name}</h2>
                  <span style={styles.categoryCount}>
                    {categoryUnlocked}/{categoryAchievements.length}
                  </span>
                </div>

                <div style={styles.achievementGrid}>
                  {categoryAchievements.map((achievement) => {
                    const unlockRecord = getUnlockRecord(progress, achievement.id);
                    return (
                      <AchievementCard
                        key={achievement.id}
                        achievement={achievement}
                        unlocked={progress.unlockedIds.includes(achievement.id)}
                        currentProgress={getProgressValue(progress, achievement.id)}
                        {...(unlockRecord !== undefined && { unlock: unlockRecord })}
                      />
                    );
                  })}
                </div>
              </section>
            );
          })
        )}
      </main>
    </div>
  );
}

export default AchievementsPage;
