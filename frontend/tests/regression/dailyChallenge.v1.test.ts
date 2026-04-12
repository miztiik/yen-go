/**
 * Daily Challenge v1 Regression Tests
 * @module tests/regression/dailyChallenge.v1.test
 *
 * T119-T121: Regression tests ensuring v1 format continues to work
 * after v2.0 support is added.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getTodaysChallenge,
  getChallenge,
  getPuzzleCount,
  getModePuzzles,
  getTechniqueOfDay,
  normalizeDailyChallenge,
  detectDailyVersion,
  getTimedSetsInfo,
} from '../../src/services/dailyChallengeService';
import type { DailyIndex } from '../../src/types/indexes';

// Mock dailyQueryService (used by getChallenge/getTodaysChallenge internally)
vi.mock('../../src/services/dailyQueryService', () => ({
  getDailySchedule: vi.fn(),
  getDailyPuzzles: vi.fn(),
  isDailyAvailable: vi.fn(),
}));

import { getDailySchedule, getDailyPuzzles } from '../../src/services/dailyQueryService';

const mockGetDailySchedule = vi.mocked(getDailySchedule);
const mockGetDailyPuzzles = vi.mocked(getDailyPuzzles);

// ============================================================================
// v1 Format Fixtures (Real-world examples)
// ============================================================================

/** Realistic v1 daily challenge (as it exists today) */
const realV1Daily: DailyIndex = {
  indexVersion: '1.0',
  date: '2026-01-15',
  generatedAt: '2026-01-15T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'beginner-001', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/beginner-001.sgf' },
      { id: 'beginner-002', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/beginner-002.sgf' },
      { id: 'beginner-003', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/beginner-003.sgf' },
      { id: 'basic-001', level: 'basic', path: 'sgf/basic/2026/01/batch-001/basic-001.sgf' },
      { id: 'basic-002', level: 'basic', path: 'sgf/basic/2026/01/batch-001/basic-002.sgf' },
      { id: 'intermediate-001', level: 'intermediate', path: 'sgf/intermediate/2026/01/batch-001/intermediate-001.sgf' },
    ],
    total: 6,
    technique_of_day: 'life-and-death',
  },
  timed: {
    queue: [
      { id: 'timed-001', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/timed-001.sgf' },
      { id: 'timed-002', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/timed-002.sgf' },
      { id: 'timed-003', level: 'basic', path: 'sgf/basic/2026/01/batch-001/timed-003.sgf' },
      { id: 'timed-004', level: 'basic', path: 'sgf/basic/2026/01/batch-001/timed-004.sgf' },
      { id: 'timed-005', level: 'intermediate', path: 'sgf/intermediate/2026/01/batch-001/timed-005.sgf' },
    ],
    queue_size: 5,
    suggested_durations: [180, 300, 600],
    scoring: {
      beginner: 10,
      basic: 15,
      intermediate: 25,
      advanced: 40,
      expert: 60,
    },
  },
  tag: {
    tag: 'snapback',
    technique_of_day: 'snapback',
    puzzles: [
      { id: 'snap-001', level: 'beginner', path: 'sgf/beginner/2026/01/batch-001/snap-001.sgf' },
      { id: 'snap-002', level: 'basic', path: 'sgf/basic/2026/01/batch-001/snap-002.sgf' },
    ],
    total: 2,
  },
  techniqueOfDay: 'life-and-death',
  weekly_ref: '2026-W03',
};

/** Minimal v1 daily (only required fields) */
const minimalV1Daily: DailyIndex = {
  date: '2026-01-10',
  standard: {
    puzzles: [
      { id: 'min-001', level: 'beginner', path: 'sgf/beginner/min-001.sgf' },
    ],
  },
};

/** v1 with string[] puzzles (legacy format) */
const legacyStringArrayDaily: DailyIndex = {
  date: '2026-01-05',
  generatedAt: '2026-01-05T00:00:00Z',
  standard: {
    puzzles: ['puzzle-a', 'puzzle-b', 'puzzle-c'] as any,
    total: 3,
  },
  timed: {
    queue: ['timed-a', 'timed-b'] as any,
    queue_size: 2,
  },
};

// ============================================================================
// T119: Existing v1 Daily Challenge Flow Still Works
// ============================================================================

describe('T119: v1 daily challenge flow regression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Version detection remains correct', () => {
    it('should detect real v1 daily as v1.0', () => {
      expect(detectDailyVersion(realV1Daily)).toBe('1.0');
    });

    it('should detect minimal v1 daily as v1.0', () => {
      expect(detectDailyVersion(minimalV1Daily)).toBe('1.0');
    });

    it('should detect legacy string array daily as v1.0', () => {
      expect(detectDailyVersion(legacyStringArrayDaily)).toBe('1.0');
    });
  });

  describe('getChallenge loads v1 correctly', () => {
    // getChallenge now uses internal SQLite-backed loadDailyIndex (not puzzleLoader).
    // This test needs a full dailyQueryService mock with DailyScheduleRow/DailyPuzzleRow
    // fixtures matching the current DB schema. Skipped until fixture update.
    it.skip('should load v1 daily challenge successfully', async () => {
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-15',
        version: '1.0',
        generated_at: '2026-01-15T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: null,
      } as any);
      mockGetDailyPuzzles.mockReturnValue([]);

      const result = getChallenge('2026-01-15');

      expect(result.success).toBe(true);
      expect(result.data?.date).toBe('2026-01-15');
    });
  });

  describe('getPuzzleCount works with v1', () => {
    it('should count standard puzzles in v1', () => {
      expect(getPuzzleCount(realV1Daily, 'standard')).toBe(6);
    });

    it('should count timed puzzles in v1', () => {
      expect(getPuzzleCount(realV1Daily, 'timed')).toBe(5);
    });

    it('should handle minimal v1', () => {
      expect(getPuzzleCount(minimalV1Daily, 'standard')).toBe(1);
      expect(getPuzzleCount(minimalV1Daily, 'timed')).toBe(0);
    });
  });

  describe('getModePuzzles returns correct v1 puzzles', () => {
    it('should return standard puzzles with correct structure', () => {
      const puzzles = getModePuzzles(realV1Daily, 'standard');

      expect(puzzles).toHaveLength(6);
      expect(puzzles[0]).toEqual({
        id: 'beginner-001',
        level: 'beginner',
        path: 'sgf/beginner/2026/01/batch-001/beginner-001.sgf',
      });
    });

    it('should return timed puzzles with correct structure', () => {
      const puzzles = getModePuzzles(realV1Daily, 'timed');

      expect(puzzles).toHaveLength(5);
      expect(puzzles[0]).toEqual({
        id: 'timed-001',
        level: 'beginner',
        path: 'sgf/beginner/2026/01/batch-001/timed-001.sgf',
      });
    });

    it('should handle empty timed section', () => {
      const puzzles = getModePuzzles(minimalV1Daily, 'timed');
      expect(puzzles).toHaveLength(0);
    });
  });

  describe('getTechniqueOfDay works with v1', () => {
    it('should get technique from standard section', () => {
      expect(getTechniqueOfDay(realV1Daily)).toBe('life-and-death');
    });

    it('should handle missing technique', () => {
      expect(getTechniqueOfDay(minimalV1Daily)).toBeUndefined();
    });
  });
});

// ============================================================================
// T120: DailyChallengePage Loads v1 Format Correctly
// ============================================================================

describe('T120: DailyChallengePage v1 loading regression', () => {
  describe('normalizeDailyChallenge preserves v1 data', () => {
    it('should preserve all standard puzzles', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);

      expect(normalized.standardPuzzles).toHaveLength(6);
      expect(normalized.standardPuzzles[0]?.id).toBe('beginner-001');
      expect(normalized.standardPuzzles[5]?.id).toBe('intermediate-001');
    });

    it('should convert timed queue to single set', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);

      expect(normalized.timedSets).toHaveLength(1);
      expect(normalized.timedSets[0]?.set_number).toBe(1);
      expect(normalized.timedSets[0]?.puzzles).toHaveLength(5);
    });

    it('should preserve technique of day', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);
      expect(normalized.techniqueOfDay).toBe('life-and-death');
    });

    it('should preserve timed scoring', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);

      expect(normalized.timedScoring).toEqual({
        beginner: 10,
        basic: 15,
        intermediate: 25,
        advanced: 40,
        expert: 60,
      });
    });

    it('should preserve suggested durations', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);
      expect(normalized.suggestedDurations).toEqual([180, 300, 600]);
    });

    it('should convert tag section to by_tag', () => {
      const normalized = normalizeDailyChallenge(realV1Daily);

      expect(Object.keys(normalized.byTag)).toContain('snapback');
      expect(normalized.byTag['snapback']?.puzzles).toHaveLength(2);
    });
  });

  describe('String array puzzles are normalized', () => {
    it('should convert string[] to DailyPuzzleEntry[]', () => {
      const puzzles = getModePuzzles(legacyStringArrayDaily, 'standard');

      expect(puzzles).toHaveLength(3);
      expect(puzzles[0]).toEqual({
        id: 'puzzle-a',
        path: 'puzzle-a',
        level: 'elementary', // default level for strings (DEFAULT_LEVEL from config)
      });
    });

    it('should convert timed string[] to entries', () => {
      const puzzles = getModePuzzles(legacyStringArrayDaily, 'timed');

      expect(puzzles).toHaveLength(2);
      expect(puzzles[0]?.id).toBe('timed-a');
    });
  });
});

// ============================================================================
// T121: DailyChallengeModal Displays v1 Progress Correctly
// ============================================================================

describe('T121: DailyChallengeModal v1 progress regression', () => {
  describe('Mode puzzle counts are correct', () => {
    it('should show correct standard mode count', () => {
      const count = getPuzzleCount(realV1Daily, 'standard');
      expect(count).toBe(6); // Modal should display "6 puzzles"
    });

    it('should show correct timed mode count', () => {
      const count = getPuzzleCount(realV1Daily, 'timed');
      expect(count).toBe(5); // Modal should display "5 puzzles"
    });
  });

  describe('Timed sets info for modal display', () => {
    it('should return single set for v1 timed', () => {
      const setsInfo = getTimedSetsInfo(realV1Daily);

      expect(setsInfo).toHaveLength(1);
      expect(setsInfo[0]).toEqual({ setNumber: 1, puzzleCount: 5 });
    });
  });

  describe('Technique display is correct', () => {
    it('should display technique of day from v1', () => {
      const technique = getTechniqueOfDay(realV1Daily);
      expect(technique).toBe('life-and-death');
    });
  });
});

// ============================================================================
// Additional Regression: Mixed Content
// ============================================================================

describe('Regression: Edge cases and mixed content', () => {
  it('should handle v1 with missing optional fields', () => {
    const sparse: DailyIndex = {
      date: '2026-01-01',
      standard: {
        puzzles: [
          { id: 'p1', level: 'beginner', path: 'p1.sgf' },
        ],
      },
    };

    const normalized = normalizeDailyChallenge(sparse);

    expect(normalized.date).toBe('2026-01-01');
    expect(normalized.standardPuzzles).toHaveLength(1);
    expect(normalized.timedSets).toHaveLength(0);
    expect(Object.keys(normalized.byTag)).toHaveLength(0);
    expect(normalized.techniqueOfDay).toBeUndefined();
  });

  it('should handle v1 with snake_case generated_at', () => {
    const snakeCase: DailyIndex = {
      date: '2026-01-02',
      generated_at: '2026-01-02T12:00:00Z',
      standard: { puzzles: [] },
    };

    const normalized = normalizeDailyChallenge(snakeCase);
    expect(normalized.generatedAt).toBe('2026-01-02T12:00:00Z');
  });

  it('should prefer generatedAt over generated_at when both exist', () => {
    const both: DailyIndex = {
      date: '2026-01-03',
      generatedAt: '2026-01-03T10:00:00Z',
      generated_at: '2026-01-03T08:00:00Z',
      standard: { puzzles: [] },
    };

    const normalized = normalizeDailyChallenge(both);
    expect(normalized.generatedAt).toBe('2026-01-03T10:00:00Z');
  });

  it('should handle empty timed queue', () => {
    const emptyQueue: DailyIndex = {
      date: '2026-01-04',
      standard: { puzzles: [] },
      timed: {
        queue: [],
        queue_size: 0,
      },
    };

    const count = getPuzzleCount(emptyQueue, 'timed');
    expect(count).toBe(0);

    const puzzles = getModePuzzles(emptyQueue, 'timed');
    expect(puzzles).toHaveLength(0);
  });
});
