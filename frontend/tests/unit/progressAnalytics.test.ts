/**
 * Tests for progressAnalytics service
 * @module tests/unit/progressAnalytics.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock dependencies before importing module under test
vi.mock('@services/progressTracker', () => ({
  loadProgress: vi.fn(),
}));

vi.mock('@services/sqliteService', () => ({
  query: vi.fn(),
}));

vi.mock('@services/tagsService', () => ({
  getTagsConfig: vi.fn(),
}));

import { computeProgressSummary, getWeakestTechniques } from '@services/progressAnalytics';
import { loadProgress } from '@services/progressTracker';
import { query } from '@services/sqliteService';
import { getTagsConfig } from '@services/tagsService';
import type { PuzzleCompletion } from '@models/progress';

const mockLoadProgress = vi.mocked(loadProgress);
const mockQuery = vi.mocked(query);
const mockGetTagsConfig = vi.mocked(getTagsConfig);

function makeCompletion(id: string, overrides: Partial<PuzzleCompletion> = {}): PuzzleCompletion {
  return {
    puzzleId: id,
    completedAt: '2026-03-01T12:00:00Z',
    timeSpentMs: 5000,
    attempts: 1,
    hintsUsed: 0,
    perfectSolve: true,
    ...overrides,
  };
}

const DEFAULT_TAGS_CONFIG = {
  version: '8.0',
  description: 'Test tags',
  last_updated: '2026-01-01',
  tags: {
    ladder: { id: 1, slug: 'ladder', name: 'Ladder', category: 'technique' as const, description: '', aliases: [] },
    snapback: { id: 2, slug: 'snapback', name: 'Snapback', category: 'technique' as const, description: '', aliases: [] },
    ko: { id: 3, slug: 'ko', name: 'Ko', category: 'technique' as const, description: '', aliases: [] },
  },
};

describe('progressAnalytics', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockLoadProgress.mockReset();
    mockQuery.mockReset();
    mockGetTagsConfig.mockReset();
    mockGetTagsConfig.mockResolvedValue(DEFAULT_TAGS_CONFIG);
  });

  describe('computeProgressSummary', () => {
    it('returns empty summary when progress load fails', async () => {
      mockLoadProgress.mockReturnValue({ success: false, error: 'parse_error', message: 'No data' });
      const summary = await computeProgressSummary();
      expect(summary.totalSolved).toBe(0);
      expect(summary.techniques).toEqual([]);
      expect(summary.difficulties).toEqual([]);
    });

    it('returns empty summary for zero completions', async () => {
      mockLoadProgress.mockReturnValue({
        success: true,
        data: {
          version: 1,
          completedPuzzles: {},
          unlockedLevels: [],
          statistics: { totalSolved: 0, totalTimeMs: 0, totalAttempts: 0, totalHintsUsed: 0, perfectSolves: 0, byDifficulty: { beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 } }, rushHighScores: [] },
          streakData: { currentStreak: 0, longestStreak: 0, lastPlayedDate: null, streakStartDate: null },
          achievements: [],
          preferences: { hintsEnabled: true, soundEnabled: true, theme: 'system' as const, boardStyle: 'classic' as const },
          lastUpdated: new Date().toISOString(),
        },
      });

      const summary = await computeProgressSummary();
      expect(summary.totalSolved).toBe(0);
      expect(summary.techniques).toEqual([]);
    });

    it('computes technique stats from puzzle_tags join', async () => {
      const completions = {
        'abc1': makeCompletion('abc1', { attempts: 1, timeSpentMs: 3000 }),
        'abc2': makeCompletion('abc2', { attempts: 3, timeSpentMs: 8000 }),
        'abc3': makeCompletion('abc3', { attempts: 1, timeSpentMs: 4000 }),
      };

      mockLoadProgress.mockReturnValue({
        success: true,
        data: {
          version: 1,
          completedPuzzles: completions,
          unlockedLevels: [],
          statistics: { totalSolved: 3, totalTimeMs: 15000, totalAttempts: 5, totalHintsUsed: 0, perfectSolves: 2, byDifficulty: { beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 } }, rushHighScores: [] },
          streakData: { currentStreak: 2, longestStreak: 5, lastPlayedDate: null, streakStartDate: null },
          achievements: [],
          preferences: { hintsEnabled: true, soundEnabled: true, theme: 'system' as const, boardStyle: 'classic' as const },
          lastUpdated: new Date().toISOString(),
        },
      });

      // First query: puzzle_tags
      mockQuery.mockImplementation((sql: string) => {
        if (sql.includes('puzzle_tags')) {
          return [
            { content_hash: 'abc1', tag_id: 1 },
            { content_hash: 'abc2', tag_id: 1 },
            { content_hash: 'abc3', tag_id: 2 },
          ];
        }
        if (sql.includes('puzzles')) {
          return [
            { content_hash: 'abc1', level_id: 120 },
            { content_hash: 'abc2', level_id: 120 },
            { content_hash: 'abc3', level_id: 140 },
          ];
        }
        return [];
      });

      const summary = await computeProgressSummary();
      expect(summary.totalSolved).toBe(3);
      expect(summary.currentStreak).toBe(2);
      expect(summary.longestStreak).toBe(5);

      // Ladder: 2 completions, 1 correct (attempts<=1), 1 wrong
      const ladder = summary.techniques.find(t => t.tagSlug === 'ladder');
      expect(ladder).toBeDefined();
      expect(ladder?.total).toBe(2);
      expect(ladder?.correct).toBe(1);
      expect(ladder?.accuracy).toBe(50);
      expect(ladder?.lowData).toBe(true);

      // Difficulty stats
      const beginner = summary.difficulties.find(d => d.levelId === 120);
      expect(beginner).toBeDefined();
      expect(beginner?.total).toBe(2);

      // Activity days
      expect(summary.activityDays.get('2026-03-01')).toBe(3);
    });

    it('handles batch chunking for >500 IDs', async () => {
      const completions: Record<string, PuzzleCompletion> = {};
      for (let i = 0; i < 600; i++) {
        completions[`p${i}`] = makeCompletion(`p${i}`);
      }

      mockLoadProgress.mockReturnValue({
        success: true,
        data: {
          version: 1,
          completedPuzzles: completions,
          unlockedLevels: [],
          statistics: { totalSolved: 600, totalTimeMs: 3000000, totalAttempts: 600, totalHintsUsed: 0, perfectSolves: 600, byDifficulty: { beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 } }, rushHighScores: [] },
          streakData: { currentStreak: 0, longestStreak: 0, lastPlayedDate: null, streakStartDate: null },
          achievements: [],
          preferences: { hintsEnabled: true, soundEnabled: true, theme: 'system' as const, boardStyle: 'classic' as const },
          lastUpdated: new Date().toISOString(),
        },
      });

      // Track number of query calls to verify batching
      let queryCallCount = 0;
      mockQuery.mockImplementation(() => {
        queryCallCount++;
        return [];
      });

      await computeProgressSummary();
      // 2 batches (500 + 100) x 2 queries (puzzle_tags + puzzles) = 4 calls
      expect(queryCallCount).toBe(4);
    });
  });

  describe('getWeakestTechniques', () => {
    it('returns weakest techniques sorted by accuracy ascending', async () => {
      const completions: Record<string, PuzzleCompletion> = {};
      // Create enough data so lowData = false for some techniques
      for (let i = 0; i < 30; i++) {
        completions[`p${i}`] = makeCompletion(`p${i}`, {
          attempts: i < 20 ? 1 : 3,
          timeSpentMs: 5000,
        });
      }

      mockLoadProgress.mockReturnValue({
        success: true,
        data: {
          version: 1,
          completedPuzzles: completions,
          unlockedLevels: [],
          statistics: { totalSolved: 30, totalTimeMs: 150000, totalAttempts: 50, totalHintsUsed: 0, perfectSolves: 20, byDifficulty: { beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 }, advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 } }, rushHighScores: [] },
          streakData: { currentStreak: 0, longestStreak: 0, lastPlayedDate: null, streakStartDate: null },
          achievements: [],
          preferences: { hintsEnabled: true, soundEnabled: true, theme: 'system' as const, boardStyle: 'classic' as const },
          lastUpdated: new Date().toISOString(),
        },
      });

      // ladder: 15 completions (10 correct = 66.7%)
      // snapback: 15 completions (10 correct = 66.7%)
      mockQuery.mockImplementation((sql: string) => {
        if (sql.includes('puzzle_tags')) {
          const results = [];
          for (let i = 0; i < 15; i++) {
            results.push({ content_hash: `p${i}`, tag_id: 1 });
          }
          for (let i = 15; i < 30; i++) {
            results.push({ content_hash: `p${i}`, tag_id: 2 });
          }
          return results;
        }
        return [];
      });

      const weakest = await getWeakestTechniques(2);
      expect(weakest).toHaveLength(2);
      // Both should be present, sorted by accuracy
      expect(weakest[0]?.accuracy).toBeLessThanOrEqual(weakest[1]?.accuracy ?? Infinity);
    });

    it('returns empty for no progress', async () => {
      mockLoadProgress.mockReturnValue({ success: false, error: 'parse_error', message: 'No data' });
      const weakest = await getWeakestTechniques(3);
      expect(weakest).toEqual([]);
    });
  });
});
