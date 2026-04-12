/**
 * FilterStrip — composite filter bar with level pills, tag dropdown,
 * active filter chips, and "Clear all" button.
 * @module components/shared/FilterStrip
 *
 * Consistent layout used across Training, Technique, Collections, and Random pages.
 * Renders inline in the accent-bordered filter layer between header and content.
 *
 * Spec: plan-compact-schema-filtering.md WP8 §8.11, §8.12, §8.17, §8.18
 */

import type { FunctionalComponent, JSX } from 'preact';
import { FilterBar, type FilterOption } from './FilterBar';
import { FilterDropdown, type DropdownOptionGroup } from './FilterDropdown';
import { ActiveFilterChip } from './ActiveFilterChip';
import { ClearAllFiltersButton } from './ClearAllFiltersButton';
import type { LevelFilterOption, TagFilterOptionGroup } from '@/hooks/useFilterState';

// ============================================================================
// Types
// ============================================================================

export interface FilterStripProps {
  /** Level filter options (from useFilterState). If provided, renders level FilterBar. */
  readonly levelOptions?: readonly LevelFilterOption[];
  /** Currently selected level ID as string, or 'all'. */
  readonly selectedLevel?: string;
  /** Called when level pill is clicked. */
  readonly onLevelChange?: (id: string) => void;

  /** Tag option groups (from useFilterState). If provided, renders tag FilterDropdown. */
  readonly tagOptionGroups?: readonly TagFilterOptionGroup[];
  /** Currently selected tag ID as string, or null for "All". */
  readonly selectedTag?: string | null;
  /** Called when tag is selected/cleared. */
  readonly onTagChange?: (id: string | null) => void;

  /** Label for the selected level chip (e.g., "Elementary"). */
  readonly selectedLevelLabel?: string | null;
  /** Label for the selected tag chip (e.g., "Ladder"). */
  readonly selectedTagLabel?: string | null;

  /** Called to clear level filter. */
  readonly onDismissLevel?: () => void;
  /** Called to clear tag filter. */
  readonly onDismissTag?: () => void;
  /** Called to clear all filters. */
  readonly onClearAll?: () => void;

  /** Number of active filters. */
  readonly activeFilterCount?: number;

  /** Extra content to render at the end (e.g., ViewToggle, sort FilterBar). */
  readonly trailing?: JSX.Element;

  /** Test ID prefix. */
  readonly testId?: string;
}

// ============================================================================
// Helpers
// ============================================================================

/** Convert LevelFilterOption[] to FilterBar FilterOption[] with tooltip title. */
function toLevelBarOptions(options: readonly LevelFilterOption[]): FilterOption[] {
  return options.map((o) => ({
    id: o.id,
    label: o.label,
    count: o.count,
    tooltip: o.tooltip,
  }));
}

/** Convert TagFilterOptionGroup[] to FilterDropdown DropdownOptionGroup[]. */
function toDropdownGroups(groups: readonly TagFilterOptionGroup[]): DropdownOptionGroup[] {
  return groups.map((g) => ({
    label: g.label,
    options: g.options.map((o) => ({
      id: o.id,
      label: o.label,
      count: o.count,
    })),
  }));
}

// ============================================================================
// Component
// ============================================================================

export const FilterStrip: FunctionalComponent<FilterStripProps> = ({
  levelOptions,
  selectedLevel = 'all',
  onLevelChange,
  tagOptionGroups,
  selectedTag = null,
  onTagChange,
  selectedLevelLabel,
  selectedTagLabel,
  onDismissLevel,
  onDismissTag,
  onClearAll,
  activeFilterCount = 0,
  trailing,
  testId = 'filter-strip',
}) => {
  return (
    <div
      className="px-4 py-3"
      style={{
        backgroundColor: 'var(--color-bg-elevated)',
        borderTop: '3px solid var(--color-accent-border, var(--color-border))',
        borderBottom: '1px solid var(--color-border)',
      }}
      data-testid={testId}
    >
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
        {/* Level FilterBar — responsive: 9 pills desktop, scrollable mobile */}
        {levelOptions && onLevelChange && (
          <div className="overflow-x-auto max-w-full" data-testid={`${testId}-levels`}>
            <FilterBar
              label="Filter by level"
              options={toLevelBarOptions(levelOptions)}
              selected={selectedLevel}
              onChange={onLevelChange}
              testId={`${testId}-level-bar`}
            />
          </div>
        )}

        {/* Tag FilterDropdown */}
        {tagOptionGroups && onTagChange && (
          <FilterDropdown
            label="Tag"
            placeholder="All Tags"
            groups={toDropdownGroups(tagOptionGroups)}
            selected={selectedTag}
            onChange={onTagChange}
            testId={`${testId}-tag-dropdown`}
          />
        )}

        {/* Active filter chips (inline, right-aligned) */}
        <div className="ml-auto flex items-center gap-1.5">
          {selectedLevelLabel && onDismissLevel && (
            <ActiveFilterChip
              label={selectedLevelLabel}
              onDismiss={onDismissLevel}
              testId={`${testId}-level-chip`}
            />
          )}
          {selectedTagLabel && onDismissTag && (
            <ActiveFilterChip
              label={selectedTagLabel}
              onDismiss={onDismissTag}
              testId={`${testId}-tag-chip`}
            />
          )}

          {/* Clear all — visible only when 2+ filters active (UX Expert #4) */}
          {activeFilterCount >= 2 && onClearAll && (
            <ClearAllFiltersButton onClear={onClearAll} testId={`${testId}-clear-all`} />
          )}

          {trailing}
        </div>
      </div>
    </div>
  );
};

export default FilterStrip;
