/**
 * Unit tests for useFilterState hook (WP7 — G43).
 *
 * Tests:
 * - Initial state: no filters active
 * - Setting level filter
 * - Setting tag filter
 * - Cascading counts when level is selected
 * - Cascading counts when tag is selected
 * - clearAll resets both filters
 * - hasActiveFilters reflects state
 * - activeFilterCount tracks correctly
 * - levelOptions include "All" with total count
 * - tagOptionGroups grouped by category
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useFilterState } from '@/hooks/useFilterState';
import type { LevelMasterEntry, TagMasterEntry } from '@/types/indexes';
import type { LevelFilterOption, TagFilterOption, TagFilterOptionGroup } from '@/hooks/useFilterState';

// ============================================================================
// Test data — minimal master index entries
// ============================================================================

const mockLevelMaster: LevelMasterEntry[] = [
  {
    id: 120,
    name: 'Beginner',
    slug: 'beginner',
    paginated: true,
    count: 50,
    pages: 1,
    tags: { '10': 20, '30': 15, '60': 15 },
  },
  {
    id: 130,
    name: 'Elementary',
    slug: 'elementary',
    paginated: true,
    count: 80,
    pages: 1,
    tags: { '10': 30, '30': 25, '60': 25 },
  },
];

const mockTagMaster: TagMasterEntry[] = [
  {
    id: 10,
    name: 'Life & Death',
    slug: 'life-and-death',
    paginated: true,
    count: 50,
    pages: 1,
    levels: { '120': 20, '130': 30 },
  },
  {
    id: 30,
    name: 'Snapback',
    slug: 'snapback',
    paginated: true,
    count: 40,
    pages: 1,
    levels: { '120': 15, '130': 25 },
  },
  {
    id: 60,
    name: 'Capture Race',
    slug: 'capture-race',
    paginated: true,
    count: 40,
    pages: 1,
    levels: { '120': 15, '130': 25 },
  },
];

// ============================================================================
// Tests
// ============================================================================

describe('useFilterState', () => {
  const renderFilterHook = () =>
    renderHook(() =>
      useFilterState({
        levelMaster: mockLevelMaster,
        tagMaster: mockTagMaster,
      }),
    );

  it('starts with no active filters', () => {
    const { result } = renderFilterHook();
    expect(result.current.levelId).toBeNull();
    expect(result.current.tagId).toBeNull();
    expect(result.current.hasActiveFilters).toBe(false);
    expect(result.current.activeFilterCount).toBe(0);
  });

  it('sets level filter', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120);
    });

    expect(result.current.levelId).toBe(120);
    expect(result.current.hasActiveFilters).toBe(true);
    expect(result.current.activeFilterCount).toBe(1);
    expect(result.current.selectedLevelSlug).toBe('beginner');
  });

  it('sets tag filter', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTag(30);
    });

    expect(result.current.tagId).toBe(30);
    expect(result.current.hasActiveFilters).toBe(true);
    expect(result.current.activeFilterCount).toBe(1);
    expect(result.current.selectedTagSlug).toBe('snapback');
  });

  it('tracks activeFilterCount = 2 when both filters set', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120);
      result.current.setTag(30);
    });

    expect(result.current.activeFilterCount).toBe(2);
  });

  it('clearAll resets both filters', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120);
      result.current.setTag(30);
    });

    expect(result.current.hasActiveFilters).toBe(true);

    act(() => {
      result.current.clearAll();
    });

    expect(result.current.levelId).toBeNull();
    expect(result.current.tagId).toBeNull();
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it('levelOptions include "All" with total count', () => {
    const { result } = renderFilterHook();

    const allOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === 'all');
    expect(allOption).toBeTruthy();
    // Total = 50 + 80 = 130
    expect(allOption!.count).toBe(130);
  });

  it('levelOptions reflect master counts when no tag filter', () => {
    const { result } = renderFilterHook();

    const begOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === '120');
    expect(begOption).toBeTruthy();
    expect(begOption!.count).toBe(50);
    expect(begOption!.label).toBe('Beginner');

    const elemOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === '130');
    expect(elemOption).toBeTruthy();
    expect(elemOption!.count).toBe(80);
  });

  it('levelOptions cascade when tag is selected', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTag(10); // Life & Death: levels = {"120": 20, "130": 30}
    });

    const begOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === '120');
    expect(begOption!.count).toBe(20);

    const elemOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === '130');
    expect(elemOption!.count).toBe(30);

    // "All" should sum cascaded values
    const allOption = result.current.levelOptions.find((o: LevelFilterOption) => o.id === 'all');
    expect(allOption!.count).toBe(50); // 20 + 30
  });

  it('tagOptionGroups cascade when level is selected', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120); // Beginner: tags = {"10": 20, "30": 15, "60": 15}
    });

    // Find Life & Death in the groups
    const allOptions = result.current.tagOptionGroups.flatMap((g: TagFilterOptionGroup) => g.options);
    const ladOption = allOptions.find((o: TagFilterOption) => o.id === '10');
    expect(ladOption).toBeTruthy();
    expect(ladOption!.count).toBe(20);

    const snapbackOption = allOptions.find((o: TagFilterOption) => o.id === '30');
    expect(snapbackOption!.count).toBe(15);
  });

  it('tagOptionGroups are grouped by category', () => {
    const { result } = renderFilterHook();

    const groupLabels = result.current.tagOptionGroups.map((g: TagFilterOptionGroup) => g.label);
    // Should have at least Objectives, Tesuji Patterns, Techniques
    expect(groupLabels).toContain('Objectives');
    expect(groupLabels).toContain('Tesuji Patterns');
    expect(groupLabels).toContain('Techniques');
  });

  it('tagOptions is a flat list derived from groups', () => {
    const { result } = renderFilterHook();

    const totalGroupOptions = result.current.tagOptionGroups.reduce(
      (sum: number, g: TagFilterOptionGroup) => sum + g.options.length,
      0,
    );
    expect(result.current.tagOptions.length).toBe(totalGroupOptions);
  });

  it('sets level to null to clear level filter', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120);
    });
    expect(result.current.levelId).toBe(120);

    act(() => {
      result.current.setLevel(null);
    });
    expect(result.current.levelId).toBeNull();
  });

  it('sets tag to null to clear tag filter', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTag(30);
    });
    expect(result.current.tagId).toBe(30);

    act(() => {
      result.current.setTag(null);
    });
    expect(result.current.tagId).toBeNull();
  });

  // ============================================================================
  // M5: Convenience method tests (setLevelFromOption, setTagFromOption, labels)
  // ============================================================================

  it('setLevelFromOption converts "all" to null', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevelFromOption('120');
    });
    expect(result.current.levelId).toBe(120);

    act(() => {
      result.current.setLevelFromOption('all');
    });
    expect(result.current.levelId).toBeNull();
  });

  it('setLevelFromOption guards against NaN', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevelFromOption('not-a-number');
    });
    expect(result.current.levelId).toBeNull();
  });

  it('setTagFromOption converts null to null and string to number', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTagFromOption('30');
    });
    expect(result.current.tagId).toBe(30);

    act(() => {
      result.current.setTagFromOption(null);
    });
    expect(result.current.tagId).toBeNull();
  });

  it('setTagFromOption guards against NaN', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTagFromOption('invalid');
    });
    expect(result.current.tagId).toBeNull();
  });

  it('selectedLevelLabel resolves from level options', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setLevel(120);
    });
    // Beginner level should have a short label
    expect(result.current.selectedLevelLabel).toBeTruthy();
    expect(typeof result.current.selectedLevelLabel).toBe('string');
  });

  it('selectedTagLabel resolves from tag options', () => {
    const { result } = renderFilterHook();

    act(() => {
      result.current.setTag(10);
    });
    expect(result.current.selectedTagLabel).toBe('Life & Death');
  });

  it('selectedLevelLabel is null when no level selected', () => {
    const { result } = renderFilterHook();
    expect(result.current.selectedLevelLabel).toBeNull();
  });

  it('selectedTagLabel is null when no tag selected', () => {
    const { result } = renderFilterHook();
    expect(result.current.selectedTagLabel).toBeNull();
  });
});
