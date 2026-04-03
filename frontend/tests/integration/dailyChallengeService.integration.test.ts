/**
 * Integration test: Daily challenge data flow from SQL → DailyIndex.
 *
 * Verifies that buildDailyIndexFromDb correctly maps real DB row shapes
 * into DailyIndex objects with populated puzzle entries — the critical
 * path for rendering daily challenge pages (AC10).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// --- Mock sqliteService (same pattern as dailyQueryService.test.ts) ---
const mockQuery = vi.fn();

vi.mock('@services/sqliteService', () => ({
  query: (...args: unknown[]) => mockQuery(...args) as unknown,
}));

import { getChallenge } from '@services/dailyChallengeService';
import type { DailyIndex, DailyPuzzleEntry, DailyTimedV2 } from '@/types/indexes';

// --- Fixtures ---

const SCHEDULE_ROW = {
  date: '2026-03-15',
  version: '3.0',
  generated_at: '2026-03-15T06:00:00Z',
  technique_of_day: 'life-and-death',
  attrs: '{}',
};

const PUZZLE_ROWS = [
  // standard section
  { date: '2026-03-15', content_hash: 'aaa1111111111111', section: 'standard', position: 0, batch: '0001', level_id: 120 },
  { date: '2026-03-15', content_hash: 'bbb2222222222222', section: 'standard', position: 1, batch: '0001', level_id: 140 },
  { date: '2026-03-15', content_hash: 'ccc3333333333333', section: 'standard', position: 2, batch: '0002', level_id: 160 },
  // timed_blitz section
  { date: '2026-03-15', content_hash: 'ddd4444444444444', section: 'timed_blitz', position: 0, batch: '0001', level_id: 110 },
  { date: '2026-03-15', content_hash: 'eee5555555555555', section: 'timed_blitz', position: 1, batch: '0001', level_id: 130 },
  // by_tag section
  { date: '2026-03-15', content_hash: 'fff6666666666666', section: 'by_tag', position: 0, batch: '0003', level_id: 150 },
];

/**
 * Helper: configure mockQuery to return schedule + puzzle rows
 * for the standard daily query pattern.
 */
function setupMocks(
  schedule: typeof SCHEDULE_ROW | null = SCHEDULE_ROW,
  puzzles: typeof PUZZLE_ROWS = PUZZLE_ROWS,
) {
  mockQuery.mockImplementation((sql: string) => {
    if (sql.includes('daily_schedule')) return schedule ? [schedule] : [];
    if (sql.includes('daily_puzzles')) return puzzles;
    return [];
  });
}

// --- Tests ---

describe('dailyChallengeService integration (AC10)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('builds DailyIndex with correct top-level fields from DB rows', () => {
    setupMocks();
    const result = getChallenge('2026-03-15');

    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    expect(daily.date).toBe('2026-03-15');
    expect(daily.version).toBe('3.0');
    expect(daily.generated_at).toBe('2026-03-15T06:00:00Z');
    expect(daily.technique_of_day).toBe('life-and-death');
  });

  it('populates standard.puzzles with correct path and level', () => {
    setupMocks();
    const result = getChallenge('2026-03-15');

    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    const standard = daily.standard;
    expect(standard).toBeDefined();

    const puzzles = standard!.puzzles as DailyPuzzleEntry[];
    expect(puzzles).toHaveLength(3);

    // Verify path construction: sgf/{batch}/{content_hash}.sgf
    expect(puzzles[0]!.path).toBe('sgf/0001/aaa1111111111111.sgf');
    expect(puzzles[1]!.path).toBe('sgf/0001/bbb2222222222222.sgf');
    expect(puzzles[2]!.path).toBe('sgf/0002/ccc3333333333333.sgf');

    // Verify level slug resolution from numeric level_id
    expect(puzzles[0]!.level).toBeTruthy();
    expect(typeof puzzles[0]!.level).toBe('string');
    for (const p of puzzles) {
      expect(p.level).toBeTruthy();
      expect(p.path).toMatch(/^sgf\/\d{4}\/[a-f0-9]+\.sgf$/);
    }
  });

  it('populates timed.sets from timed_blitz rows', () => {
    setupMocks();
    const result = getChallenge('2026-03-15');

    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    const timed = daily.timed as DailyTimedV2 | undefined;
    expect(timed).toBeDefined();
    expect(timed!.sets).toHaveLength(1);

    const blitzSet = timed!.sets[0]!;
    expect(blitzSet.set_number).toBe(1);
    expect(blitzSet.puzzles).toHaveLength(2);
    expect(blitzSet.puzzles[0]!.path).toBe('sgf/0001/ddd4444444444444.sgf');
    expect(blitzSet.puzzles[0]!.level).toBeTruthy();
  });

  it('populates by_tag using technique_of_day as key', () => {
    setupMocks();
    const result = getChallenge('2026-03-15');

    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    expect(daily.by_tag).toBeDefined();
    const byTagEntry = daily.by_tag!['life-and-death']!;
    expect(byTagEntry.puzzles).toHaveLength(1);
    expect(byTagEntry.total).toBe(1);

    const tagPuzzle = byTagEntry.puzzles[0] as DailyPuzzleEntry;
    expect(tagPuzzle.path).toBe('sgf/0003/fff6666666666666.sgf');
    expect(tagPuzzle.level).toBeTruthy();
  });

  it('returns error for a date with no schedule', () => {
    setupMocks(null);
    const result = getChallenge('2099-01-01');

    expect(result.success).toBe(false);
    if (result.success) return;
    expect(result.error).toBe('not_found');
  });

  it('handles standard-only challenge (no timed, no by_tag)', () => {
    const standardOnly = PUZZLE_ROWS.filter(r => r.section === 'standard');
    setupMocks(SCHEDULE_ROW, standardOnly);

    const result = getChallenge('2026-03-15');
    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    expect((daily.standard!.puzzles as DailyPuzzleEntry[]).length).toBe(3);
    expect(daily.timed).toBeUndefined();
  });

  it('handles empty puzzle rows for a date (schedule exists, no puzzles)', () => {
    setupMocks(SCHEDULE_ROW, []);

    const result = getChallenge('2026-03-15');
    expect(result.success).toBe(true);
    if (!result.success) return;

    const daily = result.data as DailyIndex;
    expect((daily.standard!.puzzles as DailyPuzzleEntry[]).length).toBe(0);
  });

  it('rejects future dates', () => {
    const result = getChallenge('2099-12-31');
    expect(result.success).toBe(false);
    if (result.success) return;
    expect(result.error).toBe('not_found');
    // sqliteService should never be queried for future dates
    expect(mockQuery).not.toHaveBeenCalled();
  });
});
