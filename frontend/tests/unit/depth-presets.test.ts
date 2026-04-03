/**
 * Tests for depth preset filter utilities (T8).
 * @module tests/unit/depth-presets.test
 *
 * Covers buildDepthPresetOptions(), depthPresetToRange(), zero-count
 * pill behavior, cross-filter count integration, and the AC-2 negative
 * test (CollectionViewPage must NOT use depth presets).
 */

import { describe, it, expect } from 'vitest';
import {
  buildDepthPresetOptions,
  depthPresetToRange,
} from '../../src/hooks/usePuzzleFilters';
import depthPresetsConfig from '../../../config/depth-presets.json';

// ─── buildDepthPresetOptions ───────────────────────────────────────

describe('buildDepthPresetOptions', () => {
  it('returns one option per config preset in config order', () => {
    const dist = { quick: 10, medium: 5, deep: 2 };
    const options = buildDepthPresetOptions(dist);
    expect(options).toHaveLength(depthPresetsConfig.presets.length);
    expect(options[0].id).toBe('quick');
    expect(options[1].id).toBe('medium');
    expect(options[2].id).toBe('deep');
  });

  it('uses config labels', () => {
    const dist = { quick: 1, medium: 1, deep: 1 };
    const options = buildDepthPresetOptions(dist);
    expect(options[0].label).toBe('Quick');
    expect(options[1].label).toBe('Medium');
    expect(options[2].label).toBe('Deep');
  });

  it('maps counts from distribution', () => {
    const dist = { quick: 42, medium: 17, deep: 3 };
    const options = buildDepthPresetOptions(dist);
    expect(options[0].count).toBe(42);
    expect(options[1].count).toBe(17);
    expect(options[2].count).toBe(3);
  });

  it('defaults missing preset count to 0', () => {
    const dist = { medium: 5 };
    const options = buildDepthPresetOptions(dist);
    expect(options[0].count).toBe(0); // quick missing → 0
    expect(options[1].count).toBe(5); // medium present
    expect(options[2].count).toBe(0); // deep missing → 0
  });

  it('handles empty distribution', () => {
    const options = buildDepthPresetOptions({});
    expect(options).toHaveLength(3);
    expect(options.every((o) => o.count === 0)).toBe(true);
  });

  it('zero-count pills are present (not filtered out)', () => {
    // AC: Zero-count pills rendered but dimmed/disabled.
    // buildDepthPresetOptions must always return all presets.
    const dist = { quick: 0, medium: 10, deep: 0 };
    const options = buildDepthPresetOptions(dist);
    expect(options).toHaveLength(3);
    const zeroCounts = options.filter((o) => o.count === 0);
    expect(zeroCounts).toHaveLength(2);
    expect(zeroCounts.map((o) => o.id)).toEqual(['quick', 'deep']);
  });
});

// ─── depthPresetToRange ────────────────────────────────────────────

describe('depthPresetToRange', () => {
  it('returns minDepth and maxDepth for quick', () => {
    const range = depthPresetToRange('quick');
    expect(range.minDepth).toBe(1);
    expect(range.maxDepth).toBe(2);
  });

  it('returns minDepth and maxDepth for medium', () => {
    const range = depthPresetToRange('medium');
    expect(range.minDepth).toBe(3);
    expect(range.maxDepth).toBe(5);
  });

  it('returns minDepth only for deep (unbounded)', () => {
    const range = depthPresetToRange('deep');
    expect(range.minDepth).toBe(6);
    expect(range).not.toHaveProperty('maxDepth');
  });

  it('returns empty object for null', () => {
    expect(depthPresetToRange(null)).toEqual({});
  });

  it('returns empty object for undefined', () => {
    expect(depthPresetToRange(undefined)).toEqual({});
  });

  it('returns empty object for unknown preset', () => {
    expect(depthPresetToRange('nonexistent')).toEqual({});
  });

  it('returns empty object for empty string', () => {
    expect(depthPresetToRange('')).toEqual({});
  });
});

// ─── config structure ──────────────────────────────────────────────

describe('depth-presets.json config', () => {
  it('has exactly 3 presets', () => {
    expect(depthPresetsConfig.presets).toHaveLength(3);
  });

  it('presets have contiguous ranges (no gaps)', () => {
    const presets = depthPresetsConfig.presets;
    // quick ends at 2, medium starts at 3
    expect(presets[1].minDepth).toBe((presets[0].maxDepth ?? 0) + 1);
    // medium ends at 5, deep starts at 6
    expect(presets[2].minDepth).toBe((presets[1].maxDepth ?? 0) + 1);
  });

  it('last preset has null maxDepth (unbounded)', () => {
    const last = depthPresetsConfig.presets[depthPresetsConfig.presets.length - 1];
    expect(last.maxDepth).toBeNull();
  });
});

// ─── AC-2 negative test: CollectionViewPage ────────────────────────

describe('AC-2: CollectionViewPage depth preset exclusion', () => {
  it('CollectionViewPage does NOT import depth preset utilities', async () => {
    // Read CollectionViewPage source and verify no depth preset imports.
    // This is a static analysis test — if someone adds depth presets to
    // CollectionViewPage, this test fails.
    const fs = await import('fs');
    const path = await import('path');
    const pagePath = path.resolve(
      __dirname,
      '../../src/pages/CollectionViewPage.tsx',
    );
    const source = fs.readFileSync(pagePath, 'utf-8');

    expect(source).not.toContain('buildDepthPresetOptions');
    expect(source).not.toContain('depthPresetToRange');
    expect(source).not.toContain('depth-presets');
    expect(source).not.toContain('depthPreset');
  });
});
