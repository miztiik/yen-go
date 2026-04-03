/**
 * Tests for puzzle utilities.
 * @module tests/unit/puzzle-utils.test
 *
 * Spec 119: View Schema Simplification - tests for path-based ID extraction.
 */

import { describe, it, expect } from 'vitest';
import { extractPuzzleIdFromPath, extractLevelFromPath } from '../../src/lib/puzzle/utils';

describe('extractPuzzleIdFromPath', () => {
  it('should extract puzzle ID from full path', () => {
    const path = 'sgf/beginner/2026/02/batch-001/abc123def456.sgf';
    expect(extractPuzzleIdFromPath(path)).toBe('abc123def456');
  });

  it('should extract puzzle ID from simple filename', () => {
    const path = 'abc123.sgf';
    expect(extractPuzzleIdFromPath(path)).toBe('abc123');
  });

  it('should handle paths without .sgf extension', () => {
    const path = 'sgf/beginner/2026/02/batch-001/abc123';
    expect(extractPuzzleIdFromPath(path)).toBe('abc123');
  });

  it('should handle 16-char hex puzzle IDs', () => {
    const path = 'sgf/intermediate/2026/02/batch-001/df816043bebbd30f.sgf';
    expect(extractPuzzleIdFromPath(path)).toBe('df816043bebbd30f');
  });

  it('should return empty string for empty path', () => {
    expect(extractPuzzleIdFromPath('')).toBe('');
  });

  it('should handle path with only filename', () => {
    const path = 'puzzle123.sgf';
    expect(extractPuzzleIdFromPath(path)).toBe('puzzle123');
  });
});

describe('extractLevelFromPath', () => {
  it('should extract level from full path', () => {
    const path = 'sgf/beginner/2026/02/batch-001/abc123.sgf';
    expect(extractLevelFromPath(path)).toBe('beginner');
  });

  it('should extract different levels', () => {
    expect(extractLevelFromPath('sgf/intermediate/2026/01/batch-001/xyz.sgf')).toBe('intermediate');
    expect(extractLevelFromPath('sgf/advanced/2026/01/batch-001/xyz.sgf')).toBe('advanced');
    expect(extractLevelFromPath('sgf/novice/2026/01/batch-001/xyz.sgf')).toBe('novice');
  });

  it('should return empty string when no sgf folder', () => {
    const path = 'views/by-level/beginner.json';
    expect(extractLevelFromPath(path)).toBe('');
  });

  it('should return empty string for empty path', () => {
    expect(extractLevelFromPath('')).toBe('');
  });

  it('should handle path starting with sgf/', () => {
    const path = 'sgf/elementary/file.sgf';
    expect(extractLevelFromPath(path)).toBe('elementary');
  });
});
