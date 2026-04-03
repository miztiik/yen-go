/**
 * SkillLevelTabs - Tab navigation for 9 skill levels
 * @module components/ChallengeList/SkillLevelTabs
 *
 * Covers: US2 (Browse and Select Daily Challenges)
 * FR-029: Nine Skill Levels (Novice through Expert)
 *
 * Constitution Compliance:
 * - VI. Accessibility: Keyboard navigation, ARIA tabs pattern
 * - Single source of truth: Uses config/puzzle-levels.json via Vite JSON import
 */

import type { JSX } from 'preact';
import { useCallback } from 'preact/hooks';
import { LEVELS, LEVEL_SLUGS, type LevelSlug } from '../../lib/levels/config';

/** Re-export for backward compatibility */
export type SkillLevel = LevelSlug;

/** Skill level metadata derived from config */
const SKILL_LEVELS = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, { name: lvl.name, rankRange: `${lvl.rankRange.min}-${lvl.rankRange.max}` }])
) as Record<LevelSlug, { name: string; rankRange: string }>;

/**
 * Props for SkillLevelTabs component
 */
export interface SkillLevelTabsProps {
  /** Currently selected skill level (slug) */
  readonly selectedLevel: LevelSlug;
  /** Callback when a level is selected */
  readonly onSelectLevel: (level: LevelSlug) => void;
  /** Puzzle counts per level (for badges) */
  readonly puzzleCounts?: Readonly<Record<LevelSlug, number>>;
  /** Completed counts per level */
  readonly completedCounts?: Readonly<Record<LevelSlug, number>>;
  /** Whether to show compact view */
  readonly compact?: boolean;
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Level colors for visual differentiation (9 levels)
 */
const LEVEL_COLORS: Record<LevelSlug, { bg: string; text: string; active: string }> = {
  'novice': { bg: 'var(--color-level-novice-bg)', text: 'var(--color-level-novice-text)', active: 'var(--color-level-novice-active)' },
  'beginner': { bg: 'var(--color-level-beginner-bg)', text: 'var(--color-level-beginner-text)', active: 'var(--color-level-beginner-active)' },
  'elementary': { bg: 'var(--color-level-elementary-bg)', text: 'var(--color-level-elementary-text)', active: 'var(--color-level-elementary-active)' },
  'intermediate': { bg: 'var(--color-level-intermediate-bg)', text: 'var(--color-level-intermediate-text)', active: 'var(--color-level-intermediate-active)' },
  'upper-intermediate': { bg: 'var(--color-level-upper-intermediate-bg)', text: 'var(--color-level-upper-intermediate-text)', active: 'var(--color-level-upper-intermediate-active)' },
  'advanced': { bg: 'var(--color-level-advanced-bg)', text: 'var(--color-level-advanced-text)', active: 'var(--color-level-advanced-active)' },
  'low-dan': { bg: 'var(--color-level-low-dan-bg)', text: 'var(--color-level-low-dan-text)', active: 'var(--color-level-low-dan-active)' },
  'high-dan': { bg: 'var(--color-level-high-dan-bg)', text: 'var(--color-level-high-dan-text)', active: 'var(--color-level-high-dan-active)' },
  'expert': { bg: 'var(--color-level-expert-bg)', text: 'var(--color-level-expert-text)', active: 'var(--color-level-expert-active)' },
};

/**
 * Styles for SkillLevelTabs
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    gap: '0.25rem',
    padding: '0.25rem',
    background: 'var(--color-bg-primary)',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  containerCompact: {
    display: 'flex',
    gap: '2px',
    padding: '2px',
    background: 'var(--color-bg-primary)',
    borderRadius: '6px',
    overflow: 'hidden',
  },
  tab: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '0.5rem 0.25rem',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    borderRadius: '6px',
    transition: 'all 0.2s ease',
    minWidth: '50px',
  },
  tabCompact: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '0.35rem 0.15rem',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    borderRadius: '4px',
    transition: 'all 0.2s ease',
    minWidth: '40px',
  },
  levelNumber: {
    fontSize: '1rem',
    fontWeight: '700',
    lineHeight: 1,
    marginBottom: '0.15rem',
  },
  levelNumberCompact: {
    fontSize: '0.85rem',
    fontWeight: '700',
    lineHeight: 1,
  },
  levelName: {
    fontSize: '0.6rem',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: '100%',
  },
  badge: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.65rem',
    fontWeight: '500',
    marginTop: '0.25rem',
    padding: '0.1rem 0.3rem',
    borderRadius: '10px',
    minWidth: '32px',
  },
  badgeCompact: {
    fontSize: '0.55rem',
    marginTop: '0.15rem',
    padding: '0.05rem 0.2rem',
    borderRadius: '8px',
    minWidth: '24px',
  },
};

/**
 * Single tab component
 */
interface TabProps {
  readonly level: LevelSlug;
  readonly isSelected: boolean;
  readonly onClick: () => void;
  readonly puzzleCount: number | undefined;
  readonly completedCount: number | undefined;
  readonly compact: boolean;
}

function Tab({
  level,
  isSelected,
  onClick,
  puzzleCount,
  completedCount,
  compact,
}: TabProps): JSX.Element {
  const actualCompletedCount = completedCount ?? 0;
  const levelInfo = SKILL_LEVELS[level];
  const levelMeta = LEVELS.find((l) => l.slug === level);
  const colors = LEVEL_COLORS[level];
  const isComplete = puzzleCount !== undefined && actualCompletedCount >= puzzleCount && puzzleCount > 0;

  const tabStyle: JSX.CSSProperties = {
    ...(compact ? styles.tabCompact : styles.tab),
    background: isSelected ? colors.bg : 'transparent',
    boxShadow: isSelected ? `0 1px 3px rgba(0,0,0,0.1)` : 'none',
  };

  const numberStyle: JSX.CSSProperties = {
    ...(compact ? styles.levelNumberCompact : styles.levelNumber),
    color: isSelected ? colors.active : 'var(--color-text-muted)',
  };

  const nameStyle: JSX.CSSProperties = {
    ...styles.levelName,
    color: isSelected ? colors.text : 'var(--color-accent-muted)',
  };

  const badgeStyle: JSX.CSSProperties = {
    ...(compact ? styles.badgeCompact : styles.badge),
    background: isComplete ? 'var(--color-success-solid)' : isSelected ? 'rgba(0,0,0,0.08)' : 'rgba(0,0,0,0.05)',
    color: isComplete ? 'white' : isSelected ? colors.text : 'var(--color-text-muted)',
  };

  return (
    <button
      style={tabStyle}
      onClick={onClick}
      role="tab"
      aria-selected={isSelected}
      aria-label={`${levelInfo.name}, ${levelInfo.rankRange}`}
      tabIndex={isSelected ? 0 : -1}
    >
      <span style={numberStyle}>{levelMeta?.shortName ?? level}</span>
      {!compact && <span style={nameStyle}>{levelInfo.name}</span>}
      {puzzleCount !== undefined && (
        <span style={badgeStyle}>
          {actualCompletedCount}/{puzzleCount}
        </span>
      )}
    </button>
  );
}

/**
 * SkillLevelTabs - Horizontal tab navigation for 5 skill levels
 */
export function SkillLevelTabs({
  selectedLevel,
  onSelectLevel,
  puzzleCounts,
  completedCounts,
  compact = false,
  className,
}: SkillLevelTabsProps): JSX.Element {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const currentIndex = LEVEL_SLUGS.indexOf(selectedLevel);

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = (currentIndex + 1) % LEVEL_SLUGS.length;
        const nextLevel = LEVEL_SLUGS[nextIndex];
        if (nextLevel) onSelectLevel(nextLevel);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = (currentIndex - 1 + LEVEL_SLUGS.length) % LEVEL_SLUGS.length;
        const prevLevel = LEVEL_SLUGS[prevIndex];
        if (prevLevel) onSelectLevel(prevLevel);
      } else if (e.key === 'Home') {
        e.preventDefault();
        const firstLevel = LEVEL_SLUGS[0];
        if (firstLevel) onSelectLevel(firstLevel);
      } else if (e.key === 'End') {
        e.preventDefault();
        const lastLevel = LEVEL_SLUGS[LEVEL_SLUGS.length - 1];
        if (lastLevel) onSelectLevel(lastLevel);
      }
    },
    [selectedLevel, onSelectLevel]
  );

  return (
    <div
      style={compact ? styles.containerCompact : styles.container}
      className={className}
      role="tablist"
      aria-label="Skill Level"
      onKeyDown={handleKeyDown}
    >
      {LEVEL_SLUGS.map((level) => {
        const puzzleCount = puzzleCounts !== undefined ? puzzleCounts[level] : undefined;
        const completedCount = completedCounts !== undefined ? completedCounts[level] : undefined;
        return (
          <Tab
            key={level}
            level={level}
            isSelected={level === selectedLevel}
            onClick={() => onSelectLevel(level)}
            puzzleCount={puzzleCount}
            completedCount={completedCount}
            compact={compact}
          />
        );
      })}
    </div>
  );
}

export default SkillLevelTabs;
