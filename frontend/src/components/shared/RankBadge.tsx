/**
 * Rank Badge Component
 * @module components/shared/RankBadge
 *
 * Displays puzzle rank/difficulty and primary tag (FR-035).
 * Shows rank from YR/YG and primary tag from YT.
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Display only, no logic
 * - Single source of truth: Uses config/puzzle-levels.json via Vite JSON import
 */

import { h, type FunctionComponent, type JSX } from 'preact';
import { LEVELS, type LevelSlug } from '../../lib/levels/config';

// ============================================================================
// Types
// ============================================================================

/**
 * Skill level from YG property - derived from config
 */
export type SkillLevel = LevelSlug;

/**
 * Props for RankBadge component
 */
export interface RankBadgeProps {
  /** Difficulty rank (e.g., "30k", "10k", "1d") from YR property */
  rank?: string | undefined;
  /** Skill level from YG property */
  level?: SkillLevel | undefined;
  /** Primary tag from YT property */
  primaryTag?: string | undefined;
  /** Size variant */
  size?: 'small' | 'medium' | 'large' | undefined;
  /** Additional CSS class */
  className?: string | undefined;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Colors for each skill level - derived from 9-level config
 */
const LEVEL_COLORS: Record<LevelSlug, { bg: string; text: string; border: string }> = {
  novice: {
    bg: 'var(--color-level-novice-bg)',
    text: 'var(--color-level-novice-text)',
    border: 'var(--color-level-novice-border)',
  }, // Very light green (30-20k)
  beginner: {
    bg: 'var(--color-level-beginner-bg)',
    text: 'var(--color-level-beginner-text)',
    border: 'var(--color-level-beginner-border)',
  }, // Green (19-15k)
  elementary: {
    bg: 'var(--color-level-elementary-bg)',
    text: 'var(--color-level-elementary-text)',
    border: 'var(--color-level-elementary-border)',
  }, // Light blue (14-10k)
  intermediate: {
    bg: 'var(--color-level-intermediate-bg)',
    text: 'var(--color-level-intermediate-text)',
    border: 'var(--color-level-intermediate-border)',
  }, // Yellow (9-5k)
  'upper-intermediate': {
    bg: 'var(--color-level-upper-intermediate-bg)',
    text: 'var(--color-level-upper-intermediate-text)',
    border: 'var(--color-level-upper-intermediate-border)',
  }, // Orange (4-1k)
  advanced: {
    bg: 'var(--color-level-advanced-bg)',
    text: 'var(--color-level-advanced-text)',
    border: 'var(--color-level-advanced-border)',
  }, // Pink (1-3d)
  'low-dan': {
    bg: 'var(--color-level-low-dan-bg)',
    text: 'var(--color-level-low-dan-text)',
    border: 'var(--color-level-low-dan-border)',
  }, // Red (4-6d)
  'high-dan': {
    bg: 'var(--color-level-high-dan-bg)',
    text: 'var(--color-level-high-dan-text)',
    border: 'var(--color-level-high-dan-border)',
  }, // Fuchsia (7d+)
  expert: {
    bg: 'var(--color-level-expert-bg)',
    text: 'var(--color-level-expert-text)',
    border: 'var(--color-level-expert-border)',
  }, // Purple (Pro)
};

/**
 * Default colors when level is not specified
 */
const DEFAULT_COLORS = {
  bg: 'var(--color-neutral-100)',
  text: 'var(--color-neutral-700)',
  border: 'var(--color-neutral-400)',
};

/**
 * Size configurations
 */
const SIZE_CONFIG = {
  small: { fontSize: '0.75rem', padding: '0.125rem 0.375rem', gap: '0.25rem' },
  medium: { fontSize: '0.875rem', padding: '0.25rem 0.5rem', gap: '0.375rem' },
  large: { fontSize: '1rem', padding: '0.375rem 0.75rem', gap: '0.5rem' },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format tag for display (convert kebab-case to title case)
 */
function formatTag(tag: string): string {
  return tag
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get level label for display - derives from config
 */
function getLevelLabel(level: LevelSlug): string {
  const levelMeta = LEVELS.find((l) => l.slug === level);
  return levelMeta?.name ?? level;
}

// ============================================================================
// Component
// ============================================================================

/**
 * RankBadge - displays puzzle rank and primary tag
 */
export const RankBadge: FunctionComponent<RankBadgeProps> = ({
  rank,
  level,
  primaryTag,
  size = 'medium',
  className = '',
}) => {
  const colors = (level ? LEVEL_COLORS[level] : DEFAULT_COLORS) ?? DEFAULT_COLORS;
  const sizeConfig = SIZE_CONFIG[size];

  // If neither rank nor level nor tag, don't render
  if (!rank && !level && !primaryTag) {
    return null;
  }

  const containerStyle: JSX.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: sizeConfig.gap,
    fontSize: sizeConfig.fontSize,
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
  };

  const badgeStyle: JSX.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    padding: sizeConfig.padding,
    borderRadius: '9999px',
    fontWeight: 500,
    lineHeight: 1.2,
  };

  const rankBadgeStyle: JSX.CSSProperties = {
    ...badgeStyle,
    backgroundColor: colors.bg,
    color: colors.text,
    border: `1px solid ${colors.border}`,
  };

  const tagBadgeStyle: JSX.CSSProperties = {
    ...badgeStyle,
    backgroundColor: 'var(--color-neutral-100)',
    color: 'var(--color-neutral-600)',
    border: '1px solid var(--color-neutral-300)',
  };

  return h(
    'div',
    {
      className: `rank-badge ${className}`.trim(),
      style: containerStyle,
      'aria-label': `Difficulty: ${rank || level || 'Unknown'}${primaryTag ? `, Tag: ${formatTag(primaryTag)}` : ''}`,
    },
    [
      // Rank or Level badge
      (rank || level) &&
        h(
          'span',
          {
            key: 'rank',
            className: 'rank-badge__rank',
            style: rankBadgeStyle,
          },
          rank || (level && getLevelLabel(level))
        ),

      // Primary tag badge
      primaryTag &&
        h(
          'span',
          {
            key: 'tag',
            className: 'rank-badge__tag',
            style: tagBadgeStyle,
          },
          formatTag(primaryTag)
        ),
    ]
  );
};

export default RankBadge;
