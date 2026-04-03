/**
 * SkillLevelStats component - shows stats breakdown by skill level.
 * @module components/Stats/SkillLevelStats
 *
 * Constitution Compliance:
 * - Single source of truth: Uses config/puzzle-levels.json via Vite JSON import
 */

import type { JSX } from 'preact';
import type { StatisticsBySkillLevel } from '../../types/progress';
import { LEVELS, LEVEL_SLUGS, type LevelSlug } from '../../lib/levels/config';
import { formatDuration } from '../../lib/progress';

/** Re-export for backward compatibility */
export type SkillLevel = LevelSlug;

/** Skill level names derived from config */
const SKILL_LEVEL_NAMES = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, lvl.name])
) as Record<LevelSlug, string>;

/** Skill level rank ranges derived from config */
const SKILL_LEVEL_RANKS = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, `${lvl.rankRange.min}-${lvl.rankRange.max}`])
) as Record<LevelSlug, string>;

/**
 * SkillLevelStats props
 */
export interface SkillLevelStatsProps {
  /** Stats by skill level */
  readonly stats: StatisticsBySkillLevel;
  /** Total puzzles available per level (for progress bars) */
  readonly totalByLevel?: Record<LevelSlug, number>;
}

/**
 * Styles for the SkillLevelStats component.
 */
const styles = {
  container: `
    display: flex;
    flex-direction: column;
    gap: 12px;
  `,
  levelRow: `
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: var(--color-card-bg, #ffffff);
    border: 1px solid var(--color-card-border, #e5e7eb);
    border-radius: 8px;
  `,
  levelBadge: `
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    color: white;
  `,
  levelInfo: `
    flex: 1;
    min-width: 0;
  `,
  levelName: `
    font-weight: 600;
    font-size: 0.875rem;
    color: var(--color-text-primary, #1f2937);
    margin: 0;
  `,
  levelRank: `
    font-size: 0.75rem;
    color: var(--color-text-muted, #6b7280);
    margin: 2px 0 0 0;
  `,
  statsGroup: `
    display: flex;
    gap: 16px;
    text-align: right;
  `,
  statItem: `
    min-width: 60px;
  `,
  statValue: `
    font-weight: 600;
    font-size: 1rem;
    color: var(--color-text-primary, #1f2937);
    margin: 0;
  `,
  statLabel: `
    font-size: 0.625rem;
    color: var(--color-text-disabled, #9ca3af);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0;
  `,
  progressBar: `
    height: 4px;
    background: var(--color-neutral-200, #e5e7eb);
    border-radius: 2px;
    margin-top: 6px;
    overflow: hidden;
  `,
  progressFill: `
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s ease;
  `,
};

/**
 * Level badge colors (9 levels).
 */
const LEVEL_COLORS: Record<LevelSlug, string> = {
  'novice': 'var(--color-level-novice)',
  'beginner': 'var(--color-level-beginner)',
  'elementary': 'var(--color-level-elementary)',
  'intermediate': 'var(--color-level-intermediate)',
  'upper-intermediate': 'var(--color-level-upper-intermediate)',
  'advanced': 'var(--color-level-advanced)',
  'low-dan': 'var(--color-level-low-dan)',
  'high-dan': 'var(--color-level-high-dan)',
  'expert': 'var(--color-level-expert)',
};

/**
 * Single level row component.
 */
function LevelRow({
  level,
  solved,
  avgTime,
  total,
}: {
  level: LevelSlug;
  solved: number;
  avgTime: number;
  total?: number | undefined;
}): JSX.Element {
  const percentage = total ? Math.round((solved / total) * 100) : 0;
  const levelMeta = LEVELS.find((l) => l.slug === level);

  return (
    <div class="skill-level-row" style={styles.levelRow}>
      <div
        class="level-badge"
        style={`${styles.levelBadge} background: ${LEVEL_COLORS[level]};`}
      >
        {levelMeta?.shortName ?? level}
      </div>
      <div style={styles.levelInfo}>
        <p style={styles.levelName}>{SKILL_LEVEL_NAMES[level]}</p>
        <p style={styles.levelRank}>{SKILL_LEVEL_RANKS[level]}</p>
        {total !== undefined && total > 0 && (
          <div style={styles.progressBar}>
            <div
              style={`${styles.progressFill} width: ${percentage}%; background: ${LEVEL_COLORS[level]};`}
            />
          </div>
        )}
      </div>
      <div style={styles.statsGroup}>
        <div style={styles.statItem}>
          <p style={styles.statValue}>{solved}</p>
          <p style={styles.statLabel}>Solved</p>
        </div>
        <div style={styles.statItem}>
          <p style={styles.statValue}>
            {avgTime > 0 ? formatDuration(avgTime) : '—'}
          </p>
          <p style={styles.statLabel}>Avg</p>
        </div>
      </div>
    </div>
  );
}

/**
 * SkillLevelStats component - shows stats by skill level.
 */
export function SkillLevelStats({
  stats,
  totalByLevel,
}: SkillLevelStatsProps): JSX.Element {
  return (
    <div class="skill-level-stats" style={styles.container}>
      {LEVEL_SLUGS.map((level) => (
        <LevelRow
          key={level}
          level={level}
          solved={stats.puzzlesBySkillLevel[level] ?? 0}
          avgTime={stats.avgTimeBySkillLevel[level] ?? 0}
          total={totalByLevel?.[level]}
        />
      ))}
    </div>
  );
}

export default SkillLevelStats;
