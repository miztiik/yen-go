/**
 * Tests for dailyQueryService — SQL-based daily challenge queries.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock sqliteService before importing the module under test
const mockQuery = vi.fn();

vi.mock('@services/sqliteService', () => ({
  query: (...args: unknown[]) => mockQuery(...args) as unknown,
}));

import {
  getDailySchedule,
  getDailyPuzzles,
  isDailyAvailable,
} from '@services/dailyQueryService';

describe('dailyQueryService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getDailySchedule', () => {
    it('returns schedule row when date exists', () => {
      const row = {
        date: '2026-03-15',
        version: '3.0',
        generated_at: '2026-03-15T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '{}',
      };
      mockQuery.mockReturnValue([row]);

      const result = getDailySchedule('2026-03-15');
      expect(result).toEqual(row);
      expect(mockQuery).toHaveBeenCalledWith(
        'SELECT * FROM daily_schedule WHERE date = ?',
        ['2026-03-15'],
      );
    });

    it('returns null when date does not exist', () => {
      mockQuery.mockReturnValue([]);

      const result = getDailySchedule('2099-01-01');
      expect(result).toBeNull();
    });
  });

  describe('getDailyPuzzles', () => {
    it('returns all puzzles for a date', () => {
      const rows = [
        { date: '2026-03-15', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
        { date: '2026-03-15', content_hash: 'def456', section: 'standard', position: 1, batch: '0001', level_id: 130 },
      ];
      mockQuery.mockReturnValue(rows);

      const result = getDailyPuzzles('2026-03-15');
      expect(result).toHaveLength(2);
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('WHERE dp.date = ?'),
        ['2026-03-15'],
      );
    });

    it('filters by section when provided', () => {
      mockQuery.mockReturnValue([]);

      getDailyPuzzles('2026-03-15', 'timed_blitz');
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('AND dp.section = ?'),
        ['2026-03-15', 'timed_blitz'],
      );
    });
  });

  describe('isDailyAvailable', () => {
    it('returns true when date has schedule', () => {
      mockQuery.mockReturnValue([{ c: 1 }]);
      expect(isDailyAvailable('2026-03-15')).toBe(true);
    });

    it('returns false when date has no schedule', () => {
      mockQuery.mockReturnValue([{ c: 0 }]);
      expect(isDailyAvailable('2099-01-01')).toBe(false);
    });
  });
});
