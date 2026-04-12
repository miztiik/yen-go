/**
 * QualityFilter component for filtering puzzles by quality level.
 *
 * Provides a dropdown/toggle interface for selecting minimum quality level.
 *
 * @module components/QualityFilter
 */

import { FunctionalComponent } from 'preact';
import { PuzzleQualityLevel, PUZZLE_QUALITY_INFO } from '@/lib/quality/config';

/**
 * Filter options for puzzle quality level selection
 */
export type QualityFilterOption =
  | 'all'
  | 'premium-high'
  | 'standard-plus'
  | 'verified'
  | PuzzleQualityLevel;

/**
 * Props for QualityFilter component
 */
export interface QualityFilterProps {
  /** Current filter value */
  value: QualityFilterOption;
  /** Callback when filter changes */
  onChange: (value: QualityFilterOption) => void;
  /** Whether to show level counts (optional) */
  levelCounts?: Record<PuzzleQualityLevel, number>;
  /** CSS class for container */
  className?: string;
  /** Label text (default: "Quality") */
  label?: string;
  /** Compact mode (icons only) */
  compact?: boolean;
}

/**
 * Filter option definitions
 * Scale: 1=worst (Unverified), 5=best (Premium)
 */
const FILTER_OPTIONS: Array<{
  value: QualityFilterOption;
  label: string;
  description: string;
  minLevel: PuzzleQualityLevel | null;
}> = [
  {
    value: 'all',
    label: 'All',
    description: 'Show all puzzles regardless of quality',
    minLevel: null,
  },
  {
    value: 'premium-high',
    label: 'Premium + High',
    description: 'Levels 4-5: Rich solution trees with comments',
    minLevel: 4,
  },
  {
    value: 'standard-plus',
    label: 'Standard+',
    description: 'Levels 3-5: At least one refutation branch',
    minLevel: 3,
  },
  {
    value: 'verified',
    label: 'Verified',
    description: 'Levels 2-5: Has solution tree (excludes unverified)',
    minLevel: 2,
  },
];

/**
 * Star display for puzzle quality level visualization
 * Exported for use in QualityBadge component (Phase 5)
 */
export const StarDisplay: FunctionalComponent<{ tier: PuzzleQualityLevel; size?: number }> = ({
  tier,
  size = 14,
}) => {
  const info = PUZZLE_QUALITY_INFO[tier];
  const starCount = info?.stars || 3;

  return (
    <span className="quality-stars" style={{ display: 'inline-flex', gap: '1px' }}>
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          style={{
            color: i < starCount ? 'var(--color-star-filled)' : 'var(--color-star-empty)',
            fontSize: `${size}px`,
            lineHeight: 1,
          }}
        >
          ★
        </span>
      ))}
    </span>
  );
};

/**
 * QualityFilter component
 *
 * Renders a dropdown for selecting quality level filter.
 *
 * Usage:
 * ```tsx
 * <QualityFilter
 *   value={qualityFilter}
 *   onChange={setQualityFilter}
 * />
 * ```
 */
export const QualityFilter: FunctionalComponent<QualityFilterProps> = ({
  value,
  onChange,
  levelCounts,
  className = '',
  label = 'Quality',
  compact = false,
}) => {
  const handleChange = (e: Event) => {
    const target = e.target as HTMLSelectElement;
    onChange(target.value as QualityFilterOption);
  };

  // Calculate counts for each option if levelCounts provided
  // Scale: 1=worst (Unverified), 5=best (Premium)
  const getOptionCount = (option: (typeof FILTER_OPTIONS)[number]): number | null => {
    if (!levelCounts) return null;

    if (option.minLevel === null) {
      // "All" - sum all levels
      return Object.values(levelCounts).reduce((a, b) => a + b, 0);
    }

    // Sum levels from minLevel to 5 (best)
    let count = 0;
    for (let t = option.minLevel; t <= 5; t++) {
      count += levelCounts[t as PuzzleQualityLevel] || 0;
    }
    return count;
  };

  if (compact) {
    return (
      <div className={`quality-filter quality-filter--compact ${className}`}>
        <select value={value} onChange={handleChange} aria-label={label} title={label}>
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className={`quality-filter ${className}`}>
      <label className="quality-filter__label">
        {label}
        <select value={value} onChange={handleChange} className="quality-filter__select">
          {FILTER_OPTIONS.map((opt) => {
            const count = getOptionCount(opt);
            const countStr = count !== null ? ` (${count})` : '';

            return (
              <option key={opt.value} value={opt.value} title={opt.description}>
                {opt.label}
                {countStr}
              </option>
            );
          })}
        </select>
      </label>
    </div>
  );
};

/**
 * Filter puzzles by quality level
 * Scale: 1=worst (Unverified), 5=best (Premium)
 *
 * @param puzzles - Array of puzzles with qualityLevel field
 * @param filter - Selected filter option
 * @returns Filtered array of puzzles
 */
export function filterByQuality<T extends { qualityLevel?: number }>(
  puzzles: T[],
  filter: QualityFilterOption
): T[] {
  if (filter === 'all') {
    return puzzles;
  }

  const option = FILTER_OPTIONS.find((o) => o.value === filter);
  if (!option || option.minLevel === null) {
    return puzzles;
  }

  return puzzles.filter((puzzle) => {
    const level = puzzle.qualityLevel;
    // Puzzles without level are treated as unverified (level 1, worst)
    const effectiveLevel = level ?? 1;
    return effectiveLevel >= option.minLevel!;
  });
}

/**
 * Get the minimum level for a filter option
 *
 * @param filter - Filter option
 * @returns Minimum quality level, or null for "all"
 */
export function getMinLevelForFilter(filter: QualityFilterOption): PuzzleQualityLevel | null {
  if (typeof filter === 'number') {
    return filter as PuzzleQualityLevel;
  }
  const option = FILTER_OPTIONS.find((o) => o.value === filter);
  return option?.minLevel || null;
}

/** @deprecated Use getMinLevelForFilter instead */
export function getMinTierForFilter(filter: QualityFilterOption): PuzzleQualityLevel | null {
  return getMinLevelForFilter(filter);
}

export default QualityFilter;
