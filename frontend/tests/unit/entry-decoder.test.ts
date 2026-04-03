/**
 * Tests for entryDecoder module.
 * @module tests/unit/entry-decoder.test
 *
 * Tests expandPath and decodePuzzleRow (the live SQLite path).
 */

import { describe, it, expect } from 'vitest';
import {
  expandPath,
  decodePuzzleRow,
} from '../../src/services/entryDecoder';
import type { PuzzleRow } from '../../src/services/puzzleQueryService';

// ─── Fixtures ──────────────────────────────────────────────────────

const SAMPLE_ROW: PuzzleRow = {
  content_hash: '1e9b57de9becd05f',
  batch: '0001',
  level_id: 120,
  quality: 3,
  content_type: 2,
  cx_depth: 1,
  cx_refutations: 2,
  cx_solution_len: 25,
  cx_unique_resp: 1,
  ac: 0,
  attrs: '{}',
};

// ─── Tests ─────────────────────────────────────────────────────────

describe('entryDecoder', () => {
  describe('expandPath', () => {
    it('prepends sgf/ and appends .sgf', () => {
      expect(expandPath('0001/1e9b57de9becd05f')).toBe(
        'sgf/0001/1e9b57de9becd05f.sgf'
      );
    });

    it('handles nested batch dirs', () => {
      expect(expandPath('0042/abc123')).toBe('sgf/0042/abc123.sgf');
    });

    it('throws on empty input', () => {
      expect(() => expandPath('')).toThrow('compactPath must not be empty');
    });

    it('throws on whitespace-only input', () => {
      expect(() => expandPath('   ')).toThrow('compactPath must not be empty');
    });
  });

  describe('decodePuzzleRow', () => {
    it('reconstructs path from batch + hash', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.path).toBe('sgf/0001/1e9b57de9becd05f.sgf');
    });

    it('resolves level ID to slug', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.level).toBe('beginner');
    });

    it('decodes complexity metrics', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.complexity).toEqual({
        depth: 1,
        refutations: 2,
        solutionLength: 25,
        uniqueResponses: 1,
      });
    });

    it('decodes quality slug', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.quality).toBeDefined();
    });

    it('decodes content type slug', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.contentType).toBeDefined();
    });

    it('returns empty tags and collections', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.tags).toEqual([]);
      expect(decoded.collections).toEqual([]);
    });

    it('decodes ac (analysis completeness) field', () => {
      const decoded = decodePuzzleRow(SAMPLE_ROW);
      expect(decoded.ac).toBe(0);
    });

    it('decodes non-zero ac values', () => {
      const enrichedRow: PuzzleRow = { ...SAMPLE_ROW, ac: 2 };
      const decoded = decodePuzzleRow(enrichedRow);
      expect(decoded.ac).toBe(2);
    });
  });
});
