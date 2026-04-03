/**
 * Tests for usePuzzleFilters hook utilities — T8 (L6)
 * @module tests/unit/usePuzzleFilters.test
 *
 * Covers:
 * - buildDepthPresetOptions(): config order, count injection, zero-count disabling
 * - depthPresetToRange(): preset-to-depth-range translation, null/unknown handling
 * - AC-2 negative: CollectionViewPage does NOT import depth preset utilities
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { buildDepthPresetOptions, depthPresetToRange } from '@hooks/usePuzzleFilters';

// ─── buildDepthPresetOptions ───────────────────────────────────────────────

describe('buildDepthPresetOptions', () => {
  it('returns one option per config preset in config order', () => {
    const opts = buildDepthPresetOptions({});
    // depth-presets.json has 3 presets: quick, medium, deep
    expect(opts).toHaveLength(3);
    expect(opts[0]!.id).toBe('quick');
    expect(opts[1]!.id).toBe('medium');
    expect(opts[2]!.id).toBe('deep');
  });

  it('uses config labels (Quick, Medium, Deep)', () => {
    const opts = buildDepthPresetOptions({});
    expect(opts[0]!.label).toBe('Quick');
    expect(opts[1]!.label).toBe('Medium');
    expect(opts[2]!.label).toBe('Deep');
  });

  it('injects counts from distribution map', () => {
    const dist = { quick: 42, medium: 18, deep: 7 };
    const opts = buildDepthPresetOptions(dist);
    expect(opts[0]!.count).toBe(42);
    expect(opts[1]!.count).toBe(18);
    expect(opts[2]!.count).toBe(7);
  });

  it('defaults missing preset counts to 0', () => {
    const opts = buildDepthPresetOptions({ quick: 5 });
    // medium and deep not in dist → 0
    expect(opts[1]!.count).toBe(0);
    expect(opts[2]!.count).toBe(0);
  });

  it('sets count 0 for empty distribution', () => {
    const opts = buildDepthPresetOptions({});
    for (const opt of opts) {
      expect(opt.count).toBe(0);
    }
  });

  it('preserves config order even when dist is partial', () => {
    const opts = buildDepthPresetOptions({ deep: 10, quick: 3 });
    // Order must be: quick, medium, deep regardless of dist key order
    expect(opts[0]!.id).toBe('quick');
    expect(opts[0]!.count).toBe(3);
    expect(opts[1]!.id).toBe('medium');
    expect(opts[1]!.count).toBe(0);
    expect(opts[2]!.id).toBe('deep');
    expect(opts[2]!.count).toBe(10);
  });

  it('returns readonly array (TypeScript compile-time check)', () => {
    // Runtime: verify the shape is an array
    const opts = buildDepthPresetOptions({ quick: 1 });
    expect(Array.isArray(opts)).toBe(true);
  });

  it('zero-count pills should drive disabled state in FilterBar (count 0 → disabled)', () => {
    // FilterBar sets disabled={true} when opt.count === 0.
    // This test documents the contract: count:0 means the pill is disabled UI-side.
    const opts = buildDepthPresetOptions({ quick: 5 }); // medium=0, deep=0
    const medium = opts.find(o => o.id === 'medium');
    const deep = opts.find(o => o.id === 'deep');
    expect(medium!.count).toBe(0);
    expect(deep!.count).toBe(0);
    // The zero count is what FilterBar uses: isDisabled = opt.count === 0
    // (spec: src/components/shared/FilterBar.tsx line 131)
  });
});

// ─── depthPresetToRange ─────────────────────────────────────────────────────

describe('depthPresetToRange', () => {
  it('quick → minDepth:1, maxDepth:2', () => {
    expect(depthPresetToRange('quick')).toEqual({ minDepth: 1, maxDepth: 2 });
  });

  it('medium → minDepth:3, maxDepth:5', () => {
    expect(depthPresetToRange('medium')).toEqual({ minDepth: 3, maxDepth: 5 });
  });

  it('deep → minDepth:6, no maxDepth (unbounded)', () => {
    const range = depthPresetToRange('deep');
    expect(range.minDepth).toBe(6);
    expect('maxDepth' in range).toBe(false);
  });

  it('null → empty object (no filter)', () => {
    expect(depthPresetToRange(null)).toEqual({});
  });

  it('undefined → empty object (no filter)', () => {
    expect(depthPresetToRange(undefined)).toEqual({});
  });

  it('empty string → empty object (no filter)', () => {
    expect(depthPresetToRange('')).toEqual({});
  });

  it('unknown preset slug → empty object (no filter)', () => {
    expect(depthPresetToRange('ultra-deep')).toEqual({});
  });

  it('returns only minDepth for unbounded (deep) preset — no maxDepth key', () => {
    const range = depthPresetToRange('deep');
    // maxDepth absent ensures no upper bound in SQL WHERE clause
    expect(Object.keys(range)).toEqual(['minDepth']);
  });
});

// ─── AC-2 Negative test: CollectionViewPage isolation ─────────────────────

describe('AC-2: CollectionViewPage must NOT contain depth preset utilities', () => {
  it('CollectionViewPage source does not import buildDepthPresetOptions', () => {
    const src = readFileSync(
      resolve(__dirname, '../../src/pages/CollectionViewPage.tsx'),
      'utf-8',
    );
    expect(src).not.toContain('buildDepthPresetOptions');
  });

  it('CollectionViewPage source does not import depthPresetToRange', () => {
    const src = readFileSync(
      resolve(__dirname, '../../src/pages/CollectionViewPage.tsx'),
      'utf-8',
    );
    expect(src).not.toContain('depthPresetToRange');
  });

  it('CollectionViewPage source does not reference depth-filter testId', () => {
    const src = readFileSync(
      resolve(__dirname, '../../src/pages/CollectionViewPage.tsx'),
      'utf-8',
    );
    expect(src).not.toContain('depth-filter');
  });
});

// ─── Cross-filter narrowing contract ──────────────────────────────────────

describe('Cross-filter narrowing contract', () => {
  it('depthPresetToRange(quick) produces minDepth/maxDepth for QueryFilters spread', () => {
    // This tests that the range can be safely spread into a QueryFilters object
    // (the pattern used by Archetype B pages).
    const range = depthPresetToRange('quick');
    const queryFilters = { levelIds: [120], ...range };
    expect(queryFilters.minDepth).toBe(1);
    expect(queryFilters.maxDepth).toBe(2);
    expect(queryFilters.levelIds).toEqual([120]);
  });

  it('depthPresetToRange(null) spread does not add spurious keys', () => {
    const range = depthPresetToRange(null);
    const queryFilters = { levelIds: [120], ...range };
    expect('minDepth' in queryFilters).toBe(false);
    expect('maxDepth' in queryFilters).toBe(false);
  });

  it('depth-only filter (no level/tag) leaves other filter keys absent', () => {
    const range = depthPresetToRange('medium');
    expect(range).toEqual({ minDepth: 3, maxDepth: 5 });
    // No level/tag keys in the range object
    expect('levelIds' in range).toBe(false);
    expect('tagIds' in range).toBe(false);
  });
});
