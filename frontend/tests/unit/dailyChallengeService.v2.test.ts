/**
 * Daily Challenge Service v2.0 Format Tests
 * @module tests/unit/dailyChallengeService.v2.test
 *
 * Tests for v2.0 daily format support (spec 035 FT-001).
 * T116: v2 format parsing
 * T117: v1 backward compatibility
 * T118: by_tag challenge loading
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  detectDailyVersion,
  normalizeDailyChallenge,
  getPuzzleCount,
  getModePuzzles,
  getTagPuzzles,
  getAvailableTags,
  getTimedSetsInfo,
} from '../../src/services/dailyChallengeService';
import type { DailyIndex } from '../../src/types/indexes';

// ============================================================================
// Test Data Fixtures
// ============================================================================

/** Sample v1 format daily challenge */
const sampleV1Daily: DailyIndex = {
  indexVersion: '1.0',
  date: '2026-01-28',
  generatedAt: '2026-01-28T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'std-1', level: 'beginner', path: 'sgf/beginner/std-1.sgf' },
      { id: 'std-2', level: 'beginner', path: 'sgf/beginner/std-2.sgf' },
      { id: 'std-3', level: 'intermediate', path: 'sgf/intermediate/std-3.sgf' },
    ],
    total: 3,
    technique_of_day: 'snapback',
  },
  timed: {
    queue: [
      { id: 'timed-1', level: 'beginner', path: 'sgf/beginner/timed-1.sgf' },
      { id: 'timed-2', level: 'intermediate', path: 'sgf/intermediate/timed-2.sgf' },
    ],
    queue_size: 2,
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
    tag: 'ladder',
    puzzles: [
      { id: 'tag-1', level: 'beginner', path: 'sgf/beginner/tag-1.sgf' },
    ],
    total: 1,
  },
};

/** Sample v2.0 format daily challenge */
const sampleV2Daily: DailyIndex = {
  version: '2.0',
  date: '2026-01-28',
  generated_at: '2026-01-28T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'std-1', level: 'novice', path: 'sgf/novice/std-1.sgf' },
      { id: 'std-2', level: 'beginner', path: 'sgf/beginner/std-2.sgf' },
      { id: 'std-3', level: 'elementary', path: 'sgf/elementary/std-3.sgf' },
      { id: 'std-4', level: 'intermediate', path: 'sgf/intermediate/std-4.sgf' },
    ],
    total: 4,
    technique_of_day: 'ko',
    distribution: {
      novice: 1,
      beginner: 1,
      elementary: 1,
      intermediate: 1,
    },
  },
  timed: {
    sets: [
      {
        set_number: 1,
        puzzles: [
          { id: 'set1-1', level: 'beginner', path: 'sgf/beginner/set1-1.sgf' },
          { id: 'set1-2', level: 'beginner', path: 'sgf/beginner/set1-2.sgf' },
        ],
      },
      {
        set_number: 2,
        puzzles: [
          { id: 'set2-1', level: 'intermediate', path: 'sgf/intermediate/set2-1.sgf' },
          { id: 'set2-2', level: 'intermediate', path: 'sgf/intermediate/set2-2.sgf' },
          { id: 'set2-3', level: 'intermediate', path: 'sgf/intermediate/set2-3.sgf' },
        ],
      },
      {
        set_number: 3,
        puzzles: [
          { id: 'set3-1', level: 'advanced', path: 'sgf/advanced/set3-1.sgf' },
        ],
      },
    ],
    set_count: 3,
    puzzles_per_set: 50,
    suggested_durations: [180, 300, 600, 900],
    scoring: {
      novice: 5,
      beginner: 10,
      elementary: 15,
      intermediate: 25,
      advanced: 50,
    },
  },
  by_tag: {
    ladder: {
      puzzles: [
        { id: 'ladder-1', level: 'beginner', path: 'sgf/beginner/ladder-1.sgf' },
        { id: 'ladder-2', level: 'beginner', path: 'sgf/beginner/ladder-2.sgf' },
      ],
      total: 2,
    },
    ko: {
      puzzles: [
        { id: 'ko-1', level: 'intermediate', path: 'sgf/intermediate/ko-1.sgf' },
      ],
      total: 1,
    },
    snapback: {
      puzzles: [
        { id: 'snap-1', level: 'elementary', path: 'sgf/elementary/snap-1.sgf' },
        { id: 'snap-2', level: 'elementary', path: 'sgf/elementary/snap-2.sgf' },
        { id: 'snap-3', level: 'elementary', path: 'sgf/elementary/snap-3.sgf' },
      ],
      total: 3,
    },
  },
  weekly_ref: '2026-W05',
};

/** Sample v2.0 detected by structure (no explicit version field) */
const sampleV2ByStructure: DailyIndex = {
  date: '2026-01-29',
  generated_at: '2026-01-29T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'std-1', level: 'beginner', path: 'sgf/beginner/std-1.sgf' },
    ],
    total: 1,
  },
  timed: {
    sets: [
      {
        set_number: 1,
        puzzles: [
          { id: 'timed-1', level: 'beginner', path: 'sgf/beginner/timed-1.sgf' },
        ],
      },
    ],
    set_count: 1,
    puzzles_per_set: 50,
    suggested_durations: [180],
    scoring: { beginner: 10 },
  },
  by_tag: {},
};

// ============================================================================
// T116: Version Detection Tests
// ============================================================================

describe('T116: detectDailyVersion', () => {
  it('should detect v2.0 from explicit version field', () => {
    expect(detectDailyVersion(sampleV2Daily)).toBe('2.0');
  });

  it('should detect v2.0 from timed.sets structure', () => {
    expect(detectDailyVersion(sampleV2ByStructure)).toBe('2.0');
  });

  it('should detect v1.0 for legacy format', () => {
    expect(detectDailyVersion(sampleV1Daily)).toBe('1.0');
  });

  it('should detect v2.0 from by_tag presence', () => {
    const daily: DailyIndex = {
      date: '2026-01-30',
      standard: { puzzles: [], total: 0 },
      by_tag: { ladder: { puzzles: [], total: 0 } },
    };
    expect(detectDailyVersion(daily)).toBe('2.0');
  });

  it('should default to v1.0 for minimal structure', () => {
    const minimal: DailyIndex = {
      date: '2026-01-30',
    };
    expect(detectDailyVersion(minimal)).toBe('1.0');
  });
});

// ============================================================================
// T116: v2.0 Format Parsing Tests
// ============================================================================

describe('T116: normalizeDailyChallenge (v2.0)', () => {
  it('should normalize v2.0 challenge correctly', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.originalVersion).toBe('2.0');
    expect(normalized.date).toBe('2026-01-28');
    expect(normalized.generatedAt).toBe('2026-01-28T00:00:00Z');
  });

  it('should extract standard puzzles from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.standardPuzzles).toHaveLength(4);
    expect(normalized.standardPuzzles[0]).toEqual({
      id: 'std-1',
      level: 'novice',
      path: 'sgf/novice/std-1.sgf',
    });
  });

  it('should extract timed sets from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.timedSets).toHaveLength(3);
    expect(normalized.timedSets[0]?.set_number).toBe(1);
    expect(normalized.timedSets[0]?.puzzles).toHaveLength(2);
    expect(normalized.timedSets[1]?.puzzles).toHaveLength(3);
    expect(normalized.timedSets[2]?.puzzles).toHaveLength(1);
  });

  it('should extract by_tag challenges from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(Object.keys(normalized.byTag)).toEqual(['ladder', 'ko', 'snapback']);
    expect(normalized.byTag['ladder']?.puzzles).toHaveLength(2);
    expect(normalized.byTag['ko']?.total).toBe(1);
    expect(normalized.byTag['snapback']?.puzzles).toHaveLength(3);
  });

  it('should extract technique of day from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.techniqueOfDay).toBe('ko');
  });

  it('should extract distribution from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.distribution).toEqual({
      novice: 1,
      beginner: 1,
      elementary: 1,
      intermediate: 1,
    });
  });

  it('should extract timed scoring from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.timedScoring).toEqual({
      novice: 5,
      beginner: 10,
      elementary: 15,
      intermediate: 25,
      advanced: 50,
    });
  });

  it('should extract suggested durations from v2.0', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);

    expect(normalized.suggestedDurations).toEqual([180, 300, 600, 900]);
  });
});

// ============================================================================
// T117: v1 Backward Compatibility Tests
// ============================================================================

describe('T117: normalizeDailyChallenge (v1 backward compatibility)', () => {
  it('should normalize v1 challenge correctly', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.originalVersion).toBe('1.0');
    expect(normalized.date).toBe('2026-01-28');
    expect(normalized.generatedAt).toBe('2026-01-28T00:00:00Z');
  });

  it('should extract standard puzzles from v1', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.standardPuzzles).toHaveLength(3);
    expect(normalized.standardPuzzles[0]).toEqual({
      id: 'std-1',
      level: 'beginner',
      path: 'sgf/beginner/std-1.sgf',
    });
  });

  it('should convert v1 timed queue to single set', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.timedSets).toHaveLength(1);
    expect(normalized.timedSets[0]?.set_number).toBe(1);
    expect(normalized.timedSets[0]?.puzzles).toHaveLength(2);
  });

  it('should convert v1 tag to by_tag format', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(Object.keys(normalized.byTag)).toEqual(['ladder']);
    expect(normalized.byTag['ladder']?.puzzles).toHaveLength(1);
    expect(normalized.byTag['ladder']?.total).toBe(1);
  });

  it('should extract technique of day from v1 standard', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.techniqueOfDay).toBe('snapback');
  });

  it('should have undefined distribution for v1', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.distribution).toBeUndefined();
  });

  it('should extract timed scoring from v1', () => {
    const normalized = normalizeDailyChallenge(sampleV1Daily);

    expect(normalized.timedScoring).toEqual({
      beginner: 10,
      basic: 15,
      intermediate: 25,
      advanced: 40,
      expert: 60,
    });
  });
});

describe('T117: getPuzzleCount backward compatibility', () => {
  it('should get standard count from v1', () => {
    expect(getPuzzleCount(sampleV1Daily, 'standard')).toBe(3);
  });

  it('should get timed count from v1', () => {
    expect(getPuzzleCount(sampleV1Daily, 'timed')).toBe(2);
  });

  it('should get standard count from v2', () => {
    expect(getPuzzleCount(sampleV2Daily, 'standard')).toBe(4);
  });

  it('should get total timed count from v2', () => {
    // 2 + 3 + 1 = 6
    expect(getPuzzleCount(sampleV2Daily, 'timed')).toBe(6);
  });

  it('should get specific timed set count from v2', () => {
    expect(getPuzzleCount(sampleV2Daily, 'timed', 1)).toBe(2);
    expect(getPuzzleCount(sampleV2Daily, 'timed', 2)).toBe(3);
    expect(getPuzzleCount(sampleV2Daily, 'timed', 3)).toBe(1);
  });
});

describe('T117: getModePuzzles backward compatibility', () => {
  it('should get standard puzzles from v1', () => {
    const puzzles = getModePuzzles(sampleV1Daily, 'standard');
    expect(puzzles).toHaveLength(3);
    expect(puzzles[0]?.id).toBe('std-1');
  });

  it('should get timed puzzles from v1', () => {
    const puzzles = getModePuzzles(sampleV1Daily, 'timed');
    expect(puzzles).toHaveLength(2);
    expect(puzzles[0]?.id).toBe('timed-1');
  });

  it('should get standard puzzles from v2', () => {
    const puzzles = getModePuzzles(sampleV2Daily, 'standard');
    expect(puzzles).toHaveLength(4);
    expect(puzzles[0]?.id).toBe('std-1');
  });

  it('should get all timed puzzles from v2 (no set specified)', () => {
    const puzzles = getModePuzzles(sampleV2Daily, 'timed');
    expect(puzzles).toHaveLength(6);
  });

  it('should get specific timed set puzzles from v2', () => {
    const set1Puzzles = getModePuzzles(sampleV2Daily, 'timed', 1);
    expect(set1Puzzles).toHaveLength(2);
    expect(set1Puzzles[0]?.id).toBe('set1-1');

    const set2Puzzles = getModePuzzles(sampleV2Daily, 'timed', 2);
    expect(set2Puzzles).toHaveLength(3);
    expect(set2Puzzles[0]?.id).toBe('set2-1');
  });
});

// ============================================================================
// T118: by_tag Challenge Loading Tests
// ============================================================================

describe('T118: getTagPuzzles', () => {
  it('should get tag puzzles from v2 by_tag', () => {
    const ladderPuzzles = getTagPuzzles(sampleV2Daily, 'ladder');
    expect(ladderPuzzles).toHaveLength(2);
    expect(ladderPuzzles[0]?.id).toBe('ladder-1');
  });

  it('should get different tags from v2', () => {
    const koPuzzles = getTagPuzzles(sampleV2Daily, 'ko');
    expect(koPuzzles).toHaveLength(1);
    expect(koPuzzles[0]?.id).toBe('ko-1');

    const snapbackPuzzles = getTagPuzzles(sampleV2Daily, 'snapback');
    expect(snapbackPuzzles).toHaveLength(3);
  });

  it('should fallback to v1 tag section', () => {
    const ladderPuzzles = getTagPuzzles(sampleV1Daily, 'ladder');
    expect(ladderPuzzles).toHaveLength(1);
    expect(ladderPuzzles[0]?.id).toBe('tag-1');
  });

  it('should return empty for missing tag', () => {
    const missingTag = getTagPuzzles(sampleV2Daily, 'nonexistent');
    expect(missingTag).toHaveLength(0);
  });
});

describe('T118: getAvailableTags', () => {
  it('should list all tags from v2 by_tag', () => {
    const tags = getAvailableTags(sampleV2Daily);
    expect(tags).toEqual(['ladder', 'ko', 'snapback']);
  });

  it('should list single tag from v1', () => {
    const tags = getAvailableTags(sampleV1Daily);
    expect(tags).toEqual(['ladder']);
  });

  it('should return empty for no tags', () => {
    const daily: DailyIndex = { date: '2026-01-30' };
    const tags = getAvailableTags(daily);
    expect(tags).toEqual([]);
  });
});

describe('T118: getTimedSetsInfo', () => {
  it('should get timed sets info from v2', () => {
    const setsInfo = getTimedSetsInfo(sampleV2Daily);

    expect(setsInfo).toHaveLength(3);
    expect(setsInfo[0]).toEqual({ setNumber: 1, puzzleCount: 2 });
    expect(setsInfo[1]).toEqual({ setNumber: 2, puzzleCount: 3 });
    expect(setsInfo[2]).toEqual({ setNumber: 3, puzzleCount: 1 });
  });

  it('should return single set info for v1', () => {
    const setsInfo = getTimedSetsInfo(sampleV1Daily);

    expect(setsInfo).toHaveLength(1);
    expect(setsInfo[0]).toEqual({ setNumber: 1, puzzleCount: 2 });
  });

  it('should return empty for no timed section', () => {
    const daily: DailyIndex = { date: '2026-01-30' };
    const setsInfo = getTimedSetsInfo(daily);
    expect(setsInfo).toEqual([]);
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe('Edge cases', () => {
  it('should handle empty puzzles arrays', () => {
    const emptyDaily: DailyIndex = {
      version: '2.0',
      date: '2026-01-30',
      standard: { puzzles: [], total: 0 },
      timed: {
        sets: [],
        set_count: 0,
        puzzles_per_set: 50,
        suggested_durations: [180],
        scoring: {},
      },
      by_tag: {},
    };

    const normalized = normalizeDailyChallenge(emptyDaily);
    expect(normalized.standardPuzzles).toHaveLength(0);
    expect(normalized.timedSets).toHaveLength(0);
    expect(Object.keys(normalized.byTag)).toHaveLength(0);
  });

  it('should handle string[] puzzle format (legacy)', () => {
    const legacyDaily: DailyIndex = {
      date: '2026-01-30',
      standard: {
        puzzles: ['puzzle-1', 'puzzle-2'] as any,
        total: 2,
      },
    };

    const puzzles = getModePuzzles(legacyDaily, 'standard');
    expect(puzzles).toHaveLength(2);
    expect(puzzles[0]).toEqual({
      id: 'puzzle-1',
      path: 'puzzle-1',
      level: 'intermediate', // default
    });
  });

  it('should use generated_at when generatedAt is missing', () => {
    const normalized = normalizeDailyChallenge(sampleV2Daily);
    expect(normalized.generatedAt).toBe('2026-01-28T00:00:00Z');
  });
});
