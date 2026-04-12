/**
 * Progress Analytics Service
 * @module services/progressAnalytics
 *
 * Computes technique-level and difficulty-level analytics by joining
 * localStorage progress data with SQLite puzzle_tags.
 * Read-only — does not modify progress or database state.
 */

import type { PuzzleCompletion } from '../models/progress';
import { loadProgress } from './progressTracker';
import { query } from './sqliteService';
import { getTagsConfig } from './tagsService';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TechniqueStats {
  readonly tagId: number;
  readonly tagSlug: string;
  readonly tagName: string;
  readonly correct: number;
  readonly total: number;
  readonly accuracy: number; // correct/total * 100, 0 if total=0
  readonly avgTimeMs: number;
  readonly trend30d: number; // accuracy delta vs 30+ days ago (-100 to +100)
  readonly lowData: boolean; // total < 10
}

export interface DifficultyStats {
  readonly levelId: number;
  readonly levelName: string;
  readonly correct: number;
  readonly total: number;
  readonly accuracy: number;
}

export interface ProgressSummary {
  readonly totalSolved: number;
  readonly overallAccuracy: number;
  readonly currentStreak: number;
  readonly longestStreak: number;
  readonly avgTimeMs: number;
  readonly techniques: readonly TechniqueStats[];
  readonly difficulties: readonly DifficultyStats[];
  readonly activityDays: ReadonlyMap<string, number>; // YYYY-MM-DD -> count
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Difficulty level names by ID. Matches config/puzzle-levels.json. */
const LEVEL_NAMES: ReadonlyMap<number, string> = new Map([
  [110, 'Novice'],
  [120, 'Beginner'],
  [130, 'Elementary'],
  [140, 'Intermediate'],
  [150, 'Upper-Intermediate'],
  [160, 'Advanced'],
  [200, 'Low-Dan'],
  [210, 'High-Dan'],
  [230, 'Expert'],
]);

/** Split an array into chunks of at most `size`. */
function chunk<T>(arr: readonly T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size));
  }
  return result;
}

/** Build SQL IN-clause placeholders for `n` values. */
function placeholders(n: number): string {
  return new Array(n).fill('?').join(',');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Compute a full progress summary by joining localStorage completions
 * with SQLite puzzle_tags data.
 */
export async function computeProgressSummary(): Promise<ProgressSummary> {
  const progressResult = loadProgress();
  if (!progressResult.success || !progressResult.data) {
    return emptySummary();
  }

  const progress = progressResult.data;
  const completions = progress.completedPuzzles;
  const puzzleIds = Object.keys(completions);

  if (puzzleIds.length === 0) {
    return emptySummary();
  }

  // Build tag lookup from cached tags config
  const tagsConfig = await getTagsConfig();
  const tagLookup = new Map<number, { slug: string; name: string }>();
  for (const tag of Object.values(tagsConfig.tags)) {
    tagLookup.set(tag.id, { slug: tag.slug, name: tag.name });
  }

  // Query puzzle_tags in batches of 500
  const tagMap = new Map<number, PuzzleCompletion[]>();
  const batches = chunk(puzzleIds, 500);

  for (const batch of batches) {
    const rows = query<{ content_hash: string; tag_id: number }>(
      `SELECT content_hash, tag_id FROM puzzle_tags WHERE content_hash IN (${placeholders(batch.length)})`,
      batch
    );

    for (const row of rows) {
      const completion = completions[row.content_hash];
      if (!completion) continue;
      const existing = tagMap.get(row.tag_id);
      if (existing) {
        existing.push(completion);
      } else {
        tagMap.set(row.tag_id, [completion]);
      }
    }
  }

  // Query difficulty levels from puzzles table
  const diffMap = new Map<number, { correct: number; total: number }>();
  for (const batch of batches) {
    const rows = query<{ content_hash: string; level_id: number }>(
      `SELECT content_hash, level_id FROM puzzles WHERE content_hash IN (${placeholders(batch.length)})`,
      batch
    );

    for (const row of rows) {
      const completion = completions[row.content_hash];
      if (!completion) continue;
      const existing = diffMap.get(row.level_id) ?? { correct: 0, total: 0 };
      existing.total += 1;
      if (completion.attempts <= 1) existing.correct += 1;
      diffMap.set(row.level_id, existing);
    }
  }

  // Compute per-tag technique stats
  const now = Date.now();
  const thirtyDaysAgo = now - 30 * 24 * 60 * 60 * 1000;

  const techniques: TechniqueStats[] = [];
  for (const [tagId, completionList] of tagMap) {
    const info = tagLookup.get(tagId);
    if (!info) continue;

    const total = completionList.length;
    const correct = completionList.filter((c) => c.attempts <= 1).length;
    const accuracy = total > 0 ? (correct / total) * 100 : 0;
    const avgTimeMs =
      total > 0 ? completionList.reduce((sum, c) => sum + c.timeSpentMs, 0) / total : 0;

    // 30-day trend: compare recent vs older accuracy
    const recent = completionList.filter((c) => new Date(c.completedAt).getTime() >= thirtyDaysAgo);
    const older = completionList.filter((c) => new Date(c.completedAt).getTime() < thirtyDaysAgo);
    const recentAcc =
      recent.length > 0 ? (recent.filter((c) => c.attempts <= 1).length / recent.length) * 100 : 0;
    const olderAcc =
      older.length > 0 ? (older.filter((c) => c.attempts <= 1).length / older.length) * 100 : 0;
    const trend30d = older.length > 0 ? recentAcc - olderAcc : 0;

    techniques.push({
      tagId,
      tagSlug: info.slug,
      tagName: info.name,
      correct,
      total,
      accuracy: Math.round(accuracy * 100) / 100,
      avgTimeMs: Math.round(avgTimeMs),
      trend30d: Math.round(trend30d * 100) / 100,
      lowData: total < 10,
    });
  }

  techniques.sort((a, b) => b.total - a.total);

  // Build difficulty stats
  const difficulties: DifficultyStats[] = [];
  for (const [levelId, stats] of diffMap) {
    const levelName = LEVEL_NAMES.get(levelId) ?? `Level ${levelId}`;
    difficulties.push({
      levelId,
      levelName,
      correct: stats.correct,
      total: stats.total,
      accuracy: stats.total > 0 ? Math.round((stats.correct / stats.total) * 10000) / 100 : 0,
    });
  }
  difficulties.sort((a, b) => a.levelId - b.levelId);

  // Build activity days map
  const activityDays = new Map<string, number>();
  for (const completion of Object.values(completions)) {
    const day = completion.completedAt.slice(0, 10); // YYYY-MM-DD
    activityDays.set(day, (activityDays.get(day) ?? 0) + 1);
  }

  // Overall stats
  const allCompletions = Object.values(completions);
  const totalSolved = allCompletions.length;
  const overallCorrect = allCompletions.filter((c) => c.attempts <= 1).length;
  const overallAccuracy =
    totalSolved > 0 ? Math.round((overallCorrect / totalSolved) * 10000) / 100 : 0;
  const avgTimeMs =
    totalSolved > 0
      ? Math.round(allCompletions.reduce((sum, c) => sum + c.timeSpentMs, 0) / totalSolved)
      : 0;

  return {
    totalSolved,
    overallAccuracy,
    currentStreak: progress.streakData.currentStreak,
    longestStreak: progress.streakData.longestStreak,
    avgTimeMs,
    techniques,
    difficulties,
    activityDays,
  };
}

/**
 * Get the N weakest techniques by accuracy (ascending), filtering out low-data.
 * Falls back to including low-data if insufficient high-data techniques exist.
 */
export async function getWeakestTechniques(n: number): Promise<TechniqueStats[]> {
  const summary = await computeProgressSummary();
  const highData = summary.techniques.filter((t) => !t.lowData);
  const sorted = (highData.length >= n ? highData : [...summary.techniques])
    .slice()
    .sort((a, b) => a.accuracy - b.accuracy);
  return sorted.slice(0, n);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function emptySummary(): ProgressSummary {
  return {
    totalSolved: 0,
    overallAccuracy: 0,
    currentStreak: 0,
    longestStreak: 0,
    avgTimeMs: 0,
    techniques: [],
    difficulties: [],
    activityDays: new Map(),
  };
}
