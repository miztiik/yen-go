/**
 * CollectionFilter Component
 * @module components/Collections/CollectionFilter
 *
 * Filter bar for collections by skill level.
 * Uses config/puzzle-levels.json for level definitions.
 *
 * Covers: FR-003, FR-004
 */

import type { JSX } from 'preact';
import { useState, useCallback } from 'preact/hooks';
import type { SkillLevel, CollectionFilter as FilterType } from '@/models/collection';
import { SKILL_LEVELS } from '@/models/collection';

export interface CollectionFilterProps {
  /** Current filter values */
  filter: FilterType;
  /** Handler when filter changes */
  onFilterChange: (filter: FilterType) => void;
  /** Available tags for filtering (optional) */
  availableTags?: string[];
  /** Show tag filter (default: false for MVP) */
  showTagFilter?: boolean | undefined;
}

/**
 * Filter controls for collections
 */
export function CollectionFilter({
  filter,
  onFilterChange,
  availableTags = [],
  showTagFilter = false,
}: CollectionFilterProps): JSX.Element {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleLevelChange = useCallback(
    (level: SkillLevel) => {
      if (level === 'all') {
        onFilterChange({
          ...filter,
          minLevel: undefined,
          maxLevel: undefined,
        });
      } else {
        onFilterChange({
          ...filter,
          minLevel: level,
          maxLevel: level,
        });
      }
    },
    [filter, onFilterChange]
  );

  const handleSearchChange = useCallback(
    (e: Event) => {
      const target = e.target as HTMLInputElement;
      onFilterChange({
        ...filter,
        searchTerm: target.value || undefined,
      });
    },
    [filter, onFilterChange]
  );

  const handleTagToggle = useCallback(
    (tag: string) => {
      const currentTags = filter.tags ?? [];
      const newTags = currentTags.includes(tag)
        ? currentTags.filter((t) => t !== tag)
        : [...currentTags, tag];
      onFilterChange({
        ...filter,
        tags: newTags.length > 0 ? newTags : undefined,
      });
    },
    [filter, onFilterChange]
  );

  const handleClearAll = useCallback(() => {
    onFilterChange({});
  }, [onFilterChange]);

  const containerStyle: JSX.CSSProperties = {
    padding: '1rem',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '8px',
    marginBottom: '1rem',
  };

  const rowStyle: JSX.CSSProperties = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
    alignItems: 'center',
  };

  const labelStyle: JSX.CSSProperties = {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--color-neutral-600)',
    marginRight: '0.5rem',
  };

  const buttonStyle = (isActive: boolean): JSX.CSSProperties => ({
    padding: '0.375rem 0.75rem',
    fontSize: '0.75rem',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: isActive ? 'var(--color-info-solid)' : 'var(--color-neutral-100)',
    color: isActive ? 'white' : 'var(--color-neutral-600)',
    fontWeight: isActive ? 600 : 400,
    transition: 'all 0.15s ease',
  });

  const searchInputStyle: JSX.CSSProperties = {
    padding: '0.375rem 0.75rem',
    fontSize: '0.875rem',
    border: '1px solid var(--color-neutral-200)',
    borderRadius: '6px',
    width: '200px',
    outline: 'none',
  };

  const tagButtonStyle = (isActive: boolean): JSX.CSSProperties => ({
    padding: '0.25rem 0.5rem',
    fontSize: '0.6875rem',
    border: isActive ? '1px solid var(--color-info-solid)' : '1px solid var(--color-neutral-200)',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: isActive ? 'var(--color-info-bg-solid)' : 'white',
    color: isActive ? 'var(--color-info-text)' : 'var(--color-neutral-500)',
  });

  const clearButtonStyle: JSX.CSSProperties = {
    padding: '0.25rem 0.5rem',
    fontSize: '0.6875rem',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: 'transparent',
    color: 'var(--color-neutral-500)',
    textDecoration: 'underline',
  };

  const selectedLevel = filter.minLevel ?? 'all';
  const hasActiveFilters =
    filter.minLevel !== undefined || filter.tags !== undefined || filter.searchTerm !== undefined;

  return (
    <div style={containerStyle}>
      {/* Level Filter */}
      <div style={{ ...rowStyle, marginBottom: '0.75rem' }}>
        <span style={labelStyle}>Level:</span>
        <button
          type="button"
          style={buttonStyle(selectedLevel === 'all')}
          onClick={() => handleLevelChange('all')}
        >
          All
        </button>
        {SKILL_LEVELS.map((level) => (
          <button
            key={level.slug}
            type="button"
            style={buttonStyle(selectedLevel === level.slug)}
            onClick={() => handleLevelChange(level.slug)}
            title={level.description}
          >
            {level.shortName}
          </button>
        ))}
      </div>

      {/* Search and More Filters */}
      <div style={rowStyle}>
        <input
          type="text"
          placeholder="Search collections..."
          value={filter.searchTerm ?? ''}
          onInput={handleSearchChange}
          style={searchInputStyle}
          aria-label="Search collections"
        />

        {showTagFilter && availableTags.length > 0 && (
          <button
            type="button"
            style={buttonStyle(isExpanded)}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '▼ Tags' : '▶ Tags'}
          </button>
        )}

        {hasActiveFilters && (
          <button type="button" style={clearButtonStyle} onClick={handleClearAll}>
            Clear all
          </button>
        )}
      </div>

      {/* Tag Filter (Expanded) */}
      {showTagFilter && isExpanded && availableTags.length > 0 && (
        <div style={{ ...rowStyle, marginTop: '0.75rem' }}>
          <span style={labelStyle}>Tags:</span>
          {availableTags.map((tag) => (
            <button
              key={tag}
              type="button"
              style={tagButtonStyle(filter.tags?.includes(tag) ?? false)}
              onClick={() => handleTagToggle(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default CollectionFilter;
