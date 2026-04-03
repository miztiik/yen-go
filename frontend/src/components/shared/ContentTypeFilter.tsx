/**
 * ContentTypeFilter — global content-type tab selector.
 * @module components/shared/ContentTypeFilter
 *
 * Wraps FilterBar with 4 content-type options:
 *   All Types (0) — everything including training material
 *   Curated (1) — highest quality puzzles
 *   Practice (2) — proper puzzles without training noise
 *   Training Lab (3) — teaching material and drills
 *
 * Reads/writes via useContentType() global store.
 * Appears on all browsing/solving pages as a global preference.
 */

import type { FunctionalComponent } from 'preact';
import { useMemo } from 'preact/hooks';
import { FilterBar, type FilterOption } from './FilterBar';
import { useContentType, validateContentType } from '../../hooks/useContentType';

// ============================================================================
// Option Definitions
// ============================================================================

/**
 * Static content-type filter options.
 * Order: All Types → Curated → Practice → Training Lab.
 *
 * "All Types" uses id '0' (no ct filter), "Curated" uses '1', "Practice" uses '2', "Training Lab" uses '3'.
 */
const BASE_OPTIONS: readonly FilterOption[] = [
  { id: '0', label: 'All Types' },
  { id: '1', label: 'Curated', tooltip: 'Highest quality verified puzzles' },
  { id: '2', label: 'Practice', tooltip: 'Proper puzzles for training' },
  { id: '3', label: 'Training Lab', tooltip: 'Teaching material and drills' },
] as const;

// ============================================================================
// Props
// ============================================================================

export interface ContentTypeFilterProps {
  /**
   * Optional distribution counts from database.
   * Map of content-type ID → puzzle count.
   * When provided, badges are shown on each pill.
   */
  counts?: Readonly<Record<number, number>>;
  /** Optional CSS class. */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export const ContentTypeFilter: FunctionalComponent<ContentTypeFilterProps> = ({
  counts,
  className,
}) => {
  const { contentType, setContentType } = useContentType();

  const options = useMemo((): readonly FilterOption[] => {
    if (!counts) return BASE_OPTIONS;
    return BASE_OPTIONS.map((opt) => {
      const id = Number(opt.id);
      // "All" (id=0) gets total count across all types
      const count = id === 0
        ? Object.values(counts).reduce((sum, c) => sum + c, 0)
        : counts[id];
      return count !== undefined ? { ...opt, count } : opt;
    });
  }, [counts]);

  const handleChange = (id: string): void => {
    setContentType(validateContentType(Number(id)));
  };

  return (
    <FilterBar
      label="Content type"
      options={options}
      selected={String(contentType)}
      onChange={handleChange}
      {...(className ? { className } : {})}
      testId="content-type-filter"
    />
  );
};
