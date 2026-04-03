/**
 * puzzleRushService — Data loading and puzzle selection for Rush mode.
 * @module services/puzzleRushService
 *
 * Extracted from app.tsx (Phase A, T2).
 * Provides: getNextRushPuzzle, loadLevelIndex, loadRushTagEntries.
 */

import type { RushPuzzle } from '../types/goban';
import { SKILL_LEVELS } from '../models/collection';
import { levelIdToSlug, levelSlugToId } from './configService';
import { init as initDb } from './sqliteService';
import { getPuzzlesByLevel, getPuzzlesByTag, getPuzzlesFiltered } from './puzzleQueryService';
import { puzzleRowToEntry } from './puzzleLoaders';
import { extractPuzzleIdFromPath } from '../lib/puzzle/utils';

/** Load tag page entries for tag-only Rush filtering. */
export async function loadRushTagEntries(tagId: number): Promise<readonly { path: string; level: string }[]> {
  try {
    await initDb();
    return getPuzzlesByTag(tagId).map(row => {
      const entry = puzzleRowToEntry(row);
      return { path: entry.path, level: entry.level };
    });
  } catch {
    return [];
  }
}

/** Load level view entries from SQLite database. */
export async function loadLevelIndex(levelSlug: string): Promise<{ success: boolean; data?: { entries: readonly { path: string; tags: readonly string[]; level: string }[] } }> {
  try {
    const levelId = levelSlugToId(levelSlug);
    if (levelId === undefined) return { success: false };
    await initDb();
    const entries = getPuzzlesByLevel(levelId).map(row => {
      const entry = puzzleRowToEntry(row);
      return { path: entry.path, tags: entry.tags, level: entry.level };
    });
    return { success: true, data: { entries } };
  } catch {
    return { success: false };
  }
}

/**
 * Select the next puzzle for Rush mode from available entries.
 *
 * @param rushLevelId - Selected level ID filter, or null for random level
 * @param rushTagId - Selected tag ID filter, or null for no tag filter
 * @param usedPuzzleIds - Set of already-used puzzle IDs to avoid repeats
 * @param setUsedPuzzleIds - Callback to update used IDs set
 * @returns The next RushPuzzle, or null if none available
 */
export async function getNextRushPuzzle(
  rushLevelId: number | null,
  rushTagId: number | null,
  usedPuzzleIds: Set<string>,
  setUsedPuzzleIds: (updater: (prev: Set<string>) => Set<string>) => void,
): Promise<RushPuzzle | null> {
  try {
    let levelSlug: string;
    let entries: readonly { path: string; tags?: readonly string[]; level?: string }[];

    if (rushLevelId !== null) {
      levelSlug = levelIdToSlug(rushLevelId);
      await initDb();
      const rows = rushTagId !== null
        ? getPuzzlesFiltered({ levelId: rushLevelId, tagIds: [rushTagId] })
        : getPuzzlesByLevel(rushLevelId);
      if (rows.length === 0) {
        console.error(`[PuzzleRush] Failed to load level index for ${levelSlug}`);
        return null;
      }
      entries = rows.map(puzzleRowToEntry);
    } else if (rushTagId !== null) {
      const tagEntries = await loadRushTagEntries(rushTagId);
      if (tagEntries.length === 0) {
        console.error(`[PuzzleRush] No puzzles found for tag ${rushTagId}`);
        return null;
      }
      levelSlug = tagEntries[0]?.level ?? SKILL_LEVELS[0]!.slug;
      entries = tagEntries;
    } else {
      // No filter: query all puzzles from the database.
      // Picking a random level would fail for levels with 0 published puzzles.
      await initDb();
      const rows = getPuzzlesFiltered({}, 2000);
      if (rows.length === 0) {
        console.error('[PuzzleRush] No puzzles found in database');
        return null;
      }
      entries = rows.map(puzzleRowToEntry);
      levelSlug = entries[0]?.level ?? SKILL_LEVELS[0]!.slug;
    }

    if (entries.length === 0) {
      console.error('[PuzzleRush] No puzzles found for current filters');
      return null;
    }

    // Filter out already used puzzles
    const available = entries.filter(e => {
      const puzzleId = extractPuzzleIdFromPath(e.path);
      return !usedPuzzleIds.has(puzzleId);
    });

    let entry: typeof entries[number];
    if (available.length === 0) {
      console.log(`[PuzzleRush] All ${entries.length} puzzles used, resetting pool`);
      setUsedPuzzleIds(() => new Set());
      const randomIndex = Math.floor(Math.random() * entries.length);
      entry = entries[randomIndex]!;
    } else {
      const randomIndex = Math.floor(Math.random() * available.length);
      entry = available[randomIndex]!;
    }

    const puzzleId = extractPuzzleIdFromPath(entry.path);
    setUsedPuzzleIds(prev => new Set(prev).add(puzzleId));

    const puzzleLevel = ('level' in entry && typeof entry.level === 'string') ? entry.level : levelSlug;

    return {
      id: puzzleId,
      path: entry.path,
      level: puzzleLevel,
      tags: 'tags' in entry && Array.isArray(entry.tags) ? [...entry.tags] : [],
    };
  } catch (error) {
    console.error('[PuzzleRush] Error fetching puzzle:', error);
    return null;
  }
}
