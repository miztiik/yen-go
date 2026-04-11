/**
 * Daily Challenge Service
 * @module services/dailyChallengeService
 *
 * Responsible for loading daily challenge data and calculating countdowns.
 * Uses existing puzzleLoader.ts for actual data fetching.
 *
 * Covers: FR-030 to FR-041 (Daily Challenge)
 * 
 * Supports both v1 (legacy) and v2.0 (spec 035) daily formats.
 * T112-T114: Version detection and backward compatibility.
 */

import type { 
  DailyIndex, 
  DailyPuzzleEntry,
  DailyTimedV2,
  DailyByTag,
  DailyStandardV2,
} from '@/types/indexes';
import type { LoaderResult, LoaderError } from '@/types/common';
import { getDailySchedule, getDailyPuzzles, isDailyAvailable } from '@/services/dailyQueryService';
import type { DailyScheduleRow, DailyPuzzleRow } from '@/services/dailyQueryService';
import { getLevelSlug } from '@/lib/levels/config';
import { DEFAULT_LEVEL } from '@/lib/levels/level-defaults';
import type { 
  DailyCountdown, 
  DailyChallengeMode,
} from '@/models/dailyChallenge';

// ============================================================================
// Local Types for v2.0 Support
// ============================================================================

/**
 * Timed set (local version for service).
 */
interface TimedSet {
  set_number: number;
  puzzles: DailyPuzzleEntry[];
}

/**
 * By-tag challenge entry (local version).
 */
interface ByTagChallengeEntry {
  puzzles: DailyPuzzleEntry[];
  total: number;
}

/**
 * By-tag challenges (local version).
 */
type ByTagChallenge = Record<string, ByTagChallengeEntry>;

/**
 * Normalized daily challenge (internal representation).
 * Converts both v1 and v2 formats to a common structure.
 */
export interface NormalizedDailyChallenge {
  originalVersion: string;
  date: string;
  generatedAt: string;
  standardPuzzles: DailyPuzzleEntry[];
  timedSets: TimedSet[];
  byTag: ByTagChallenge;
  techniqueOfDay: string | undefined;
  distribution: Record<string, number> | undefined;
  timedScoring: Record<string, number> | undefined;
  suggestedDurations: number[] | undefined;
}

// ============================================================================
// Types
// ============================================================================

/**
 * Daily challenge status
 */
export type DailyChallengeStatus =
  | 'not-started'
  | 'in-progress'
  | 'completed'
  | 'expired';

/**
 * Summary for daily challenge history view
 */
export interface DailyChallengeSummary {
  /** Challenge date (YYYY-MM-DD) */
  date: string;
  /** User's completion status */
  status: DailyChallengeStatus;
  /** Puzzles completed */
  completedCount: number;
  /** Total puzzles in challenge */
  totalCount: number;
  /** Technique of the day (if any) */
  techniqueOfDay?: string;
  /** User's performance (if completed) */
  performance?: DailyPerformance;
}

/**
 * User's performance on a daily challenge
 */
export interface DailyPerformance {
  /** Total time taken (milliseconds) */
  totalTimeMs: number;
  /** Accuracy by level */
  accuracyByLevel: Record<string, { correct: number; total: number }>;
  /** Overall accuracy percentage (0-100) */
  overallAccuracy: number;
  /** Timed mode score (if played) */
  timedScore?: number;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a success result
 */
function success<T>(data: T): LoaderResult<T> {
  return { success: true, data };
}

/**
 * Create an error result
 */
function error<T>(errorType: LoaderError, message: string): LoaderResult<T> {
  return { success: false, error: errorType, message };
}

/**
 * Build a DailyIndex from SQL database rows.
 * Constructs the same shape that was previously loaded from JSON files.
 */
function buildDailyIndexFromDb(
  schedule: DailyScheduleRow,
  puzzleRows: DailyPuzzleRow[],
): DailyIndex {
  // Group puzzle rows by section
  const bySection = new Map<string, DailyPuzzleRow[]>();
  for (const row of puzzleRows) {
    const arr = bySection.get(row.section) ?? [];
    arr.push(row);
    bySection.set(row.section, arr);
  }

  const toEntry = (row: DailyPuzzleRow): DailyPuzzleEntry => ({
    level: getLevelSlug(row.level_id) ?? DEFAULT_LEVEL,
    path: `sgf/${row.batch}/${row.content_hash}.sgf`,
  });

  // Build standard section
  const standardRows = bySection.get('standard') ?? [];
  const standardPuzzles = standardRows.map(toEntry);

  // Build timed sets
  const timedSections = ['timed_blitz', 'timed_sprint', 'timed_endurance'];
  const timedSets = timedSections
    .map((section, idx) => {
      const rows = bySection.get(section) ?? [];
      if (rows.length === 0) return null;
      return {
        set_number: idx + 1,
        puzzles: rows.map(toEntry),
      };
    })
    .filter((s): s is NonNullable<typeof s> => s !== null);

  // Build by_tag section
  const byTagRows = bySection.get('by_tag') ?? [];
  const byTag: DailyByTag = {};
  if (byTagRows.length > 0 && schedule.technique_of_day) {
    byTag[schedule.technique_of_day] = {
      puzzles: byTagRows.map(toEntry),
      total: byTagRows.length,
    };
  }

  return {
    version: schedule.version,
    date: schedule.date,
    generated_at: schedule.generated_at,
    standard: {
      puzzles: standardPuzzles,
      total: standardPuzzles.length,
      ...(schedule.technique_of_day ? { technique_of_day: schedule.technique_of_day } : {}),
    },
    ...(timedSets.length > 0
      ? {
          timed: {
            sets: timedSets,
            set_count: timedSets.length,
            puzzles_per_set: timedSets[0]?.puzzles.length ?? 0,
            suggested_durations: [180, 300, 600, 900],
            scoring: {},
          },
        }
      : {}),
    ...(Object.keys(byTag).length > 0 ? { by_tag: byTag } : {}),
    ...(schedule.technique_of_day ? { technique_of_day: schedule.technique_of_day } : {}),
  };
}

/**
 * Load daily challenge from the SQLite database.
 * Replaces the old JSON fetch approach.
 */
function loadDailyIndex(date: string): LoaderResult<DailyIndex> {
  const schedule = getDailySchedule(date);
  if (!schedule) {
    return error('not_found', `No daily challenge found for ${date}`);
  }
  const puzzleRows = getDailyPuzzles(date);
  return success(buildDailyIndexFromDb(schedule, puzzleRows));
}

/**
 * Get today's date in YYYY-MM-DD format
 */
export function getTodayDateString(): string {
  const now = new Date();
  return now.toISOString().split('T')[0] as string;
}

/**
 * Check if a date is in the future
 */
export function isFutureDate(date: string): boolean {
  const today = getTodayDateString();
  return date > today;
}

/**
 * Calculate countdown to midnight (next daily challenge)
 */
export function calculateCountdown(): DailyCountdown {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0);

  const totalMs = Math.max(0, tomorrow.getTime() - now.getTime());
  const totalSeconds = Math.floor(totalMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return {
    hours,
    minutes,
    seconds,
    totalMs,
    isReady: totalMs === 0,
  };
}

/**
 * Format countdown for display (e.g., "5h 23m")
 */
export function formatCountdown(countdown: DailyCountdown): string {
  if (countdown.isReady) {
    return 'Ready!';
  }
  
  const parts: string[] = [];
  if (countdown.hours > 0) {
    parts.push(`${countdown.hours}h`);
  }
  if (countdown.minutes > 0 || countdown.hours > 0) {
    parts.push(`${countdown.minutes}m`);
  }
  if (countdown.hours === 0) {
    parts.push(`${countdown.seconds}s`);
  }
  
  return parts.join(' ');
}

// ============================================================================
// Daily Challenge Loading
// ============================================================================

/**
 * Get today's daily challenge.
 */
export function getTodaysChallenge(): LoaderResult<DailyIndex> {
  const today = getTodayDateString();
  return loadDailyIndex(today);
}

/**
 * Get daily challenge for a specific date.
 */
export function getChallenge(date: string): LoaderResult<DailyIndex> {
  // Don't allow future dates
  if (isFutureDate(date)) {
    return error('not_found', `Daily challenge for ${date} is not yet available`);
  }
  
  return loadDailyIndex(date);
}

/**
 * Get countdown to next daily challenge.
 */
export function getCountdownToNext(): DailyCountdown {
  return calculateCountdown();
}

/**
 * Get list of available daily challenges (history).
 */
export function getAvailableChallenges(
  limit: number = 7
): LoaderResult<string[]> {
  const dates: string[] = [];
  const today = new Date();
  
  for (let i = 0; i < limit; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0] as string;
    
    if (isDailyAvailable(dateStr)) {
      dates.push(dateStr);
    }
  }
  
  return success(dates);
}

/**
 * Check if a challenge is available (not in future).
 */
export function isChallengeAvailable(date: string): boolean {
  return !isFutureDate(date);
}

// ============================================================================
// T112: Version Detection
// ============================================================================

/**
 * Detect the version of a daily challenge index.
 * T112: Version detection for v1 vs v2.0 formats.
 */
export function detectDailyVersion(challenge: DailyIndex): '1.0' | '2.0' {
  // Explicit version field
  if (challenge.version === '2.0') {
    return '2.0';
  }
  
  // Check for v2.0 structure: timed.sets array
  if (challenge.timed && 'sets' in challenge.timed && Array.isArray(challenge.timed.sets)) {
    return '2.0';
  }
  
  // Check for v2.0 structure: by_tag object
  if (challenge.by_tag && typeof challenge.by_tag === 'object') {
    return '2.0';
  }
  
  return '1.0';
}

/**
 * Check if timed section is v2.0 format (has sets array).
 */
function isTimedV2Format(timed: DailyIndex['timed']): boolean {
  return timed !== undefined && 'sets' in timed && Array.isArray(timed.sets);
}

// ============================================================================
// T113: Backward Compatibility Layer
// ============================================================================

/**
 * Normalize a DailyIndex to common internal structure.
 * T113: Converts both v1 and v2.0 formats to NormalizedDailyChallenge.
 */
export function normalizeDailyChallenge(challenge: DailyIndex): NormalizedDailyChallenge {
  const version = detectDailyVersion(challenge);
  const generatedAt = challenge.generatedAt ?? challenge.generated_at ?? '';
  
  if (version === '2.0') {
    // v2.0 format
    const standard = challenge.standard;
    const timed = challenge.timed;
    const byTag = challenge.by_tag ?? {};
    
    // Extract timed sets from v2.0 structure
    const timedSets: TimedSet[] = isTimedV2Format(timed) 
      ? (timed as DailyTimedV2).sets.map(s => ({
          set_number: s.set_number,
          puzzles: normalizePuzzleList(s.puzzles),
        }))
      : [];
    
    // Extract scoring
    const timedScoring = isTimedV2Format(timed) 
      ? (timed as DailyTimedV2).scoring 
      : timed?.scoring;
    
    const suggestedDurations = isTimedV2Format(timed)
      ? (timed as DailyTimedV2).suggested_durations
      : timed?.suggested_durations;
    
    return {
      originalVersion: '2.0',
      date: challenge.date,
      generatedAt,
      standardPuzzles: normalizePuzzleList(standard?.puzzles ?? []),
      timedSets,
      byTag: normalizeByTag(byTag),
      techniqueOfDay: standard?.technique_of_day ?? challenge.techniqueOfDay,
      distribution: 'distribution' in (standard ?? {}) 
        ? (standard as DailyStandardV2).distribution 
        : undefined,
      timedScoring: timedScoring as Record<string, number> | undefined,
      suggestedDurations,
    };
  } else {
    // v1 format - convert to normalized structure
    const standard = challenge.standard;
    const timed = challenge.timed;
    
    // For v1, create a single "set" from the queue for backward compat
    // Cast to v1 type to access queue property
    const timedV1 = timed as { queue?: (DailyPuzzleEntry | string)[]; scoring?: Record<string, number>; suggested_durations?: number[] } | undefined;
    const timedPuzzles = timedV1?.queue 
      ? normalizePuzzleList(timedV1.queue) 
      : [];
    const timedSets: TimedSet[] = timedPuzzles.length > 0 
      ? [{ set_number: 1, puzzles: timedPuzzles }] 
      : [];
    
    // Convert v1 tag challenge to by_tag format
    const byTag: ByTagChallenge = {};
    if (challenge.tag) {
      byTag[challenge.tag.tag] = {
        puzzles: normalizePuzzleList(challenge.tag.puzzles),
        total: challenge.tag.total ?? challenge.tag.puzzles.length,
      };
    }
    
    return {
      originalVersion: '1.0',
      date: challenge.date,
      generatedAt,
      standardPuzzles: normalizePuzzleList(standard?.puzzles ?? []),
      timedSets,
      byTag,
      techniqueOfDay: standard?.technique_of_day ?? challenge.tag?.technique_of_day ?? challenge.techniqueOfDay,
      distribution: undefined,
      timedScoring: timedV1?.scoring,
      suggestedDurations: timedV1?.suggested_durations,
    };
  }
}

/**
 * Normalize puzzle list to DailyPuzzleEntry[] (handles string[] or DailyPuzzleEntry[]).
 */
function normalizePuzzleList(
  puzzles: (DailyPuzzleEntry | string)[] | readonly (DailyPuzzleEntry | string)[]
): DailyPuzzleEntry[] {
  return puzzles.map((p): DailyPuzzleEntry => {
    if (typeof p === 'string') {
      return { id: p, path: p, level: DEFAULT_LEVEL };
    }
    return p;
  });
}

/**
 * Normalize by_tag to ByTagChallenge format.
 */
function normalizeByTag(byTag: DailyByTag): ByTagChallenge {
  const result: Record<string, ByTagChallengeEntry> = {};
  for (const [tag, entry] of Object.entries(byTag)) {
    result[tag] = {
      puzzles: normalizePuzzleList(entry.puzzles),
      total: entry.total,
    };
  }
  return result;
}

// ============================================================================
// T114: Updated Mode Functions
// ============================================================================

/**
 * Get puzzle count for a challenge mode.
 * T114: Updated to support both v1 and v2.0 formats.
 */
export function getPuzzleCount(
  challenge: DailyIndex,
  mode: DailyChallengeMode,
  timedSetNumber?: number
): number {
  const version = detectDailyVersion(challenge);
  
  if (mode === 'standard') {
    const standard = challenge.standard;
    if (standard?.puzzles) {
      return standard.puzzles.length;
    }
    return standard?.total ?? 0;
  } else {
    // Timed mode
    const timed = challenge.timed;
    if (!timed) return 0;
    
    if (version === '2.0' && isTimedV2Format(timed)) {
      // v2.0: Get puzzles from specific set or total
      const timedV2 = timed as DailyTimedV2;
      if (timedSetNumber !== undefined) {
        const set = timedV2.sets.find(s => s.set_number === timedSetNumber);
        return set?.puzzles.length ?? 0;
      }
      // Return total across all sets
      return timedV2.sets.reduce((sum, s) => sum + s.puzzles.length, 0);
    } else {
      // v1: Use queue
      const timedV1 = timed as { queue?: (DailyPuzzleEntry | string)[]; queue_size?: number };
      if (timedV1.queue) {
        return timedV1.queue.length;
      }
      return timedV1.queue_size ?? 0;
    }
  }
}

/**
 * Get puzzles for a mode (normalizes string[] to DailyPuzzleEntry[]).
 * T114: Updated to support both v1 and v2.0 formats.
 */
export function getModePuzzles(
  challenge: DailyIndex,
  mode: DailyChallengeMode,
  timedSetNumber?: number
): DailyPuzzleEntry[] {
  const version = detectDailyVersion(challenge);
  
  if (mode === 'standard') {
    return normalizePuzzleList(challenge.standard?.puzzles ?? []);
  } else {
    // Timed mode
    const timed = challenge.timed;
    if (!timed) return [];
    
    if (version === '2.0' && isTimedV2Format(timed)) {
      // v2.0: Get puzzles from specific set or all sets
      const timedV2 = timed as DailyTimedV2;
      if (timedSetNumber !== undefined) {
        const set = timedV2.sets.find(s => s.set_number === timedSetNumber);
        return normalizePuzzleList(set?.puzzles ?? []);
      }
      // Return all puzzles from all sets
      return timedV2.sets.flatMap(s => normalizePuzzleList(s.puzzles));
    } else {
      // v1: Use queue
      const timedV1 = timed as { queue?: (DailyPuzzleEntry | string)[] };
      return normalizePuzzleList(timedV1.queue ?? []);
    }
  }
}

/**
 * Get puzzles for a specific tag (v2.0 by_tag support).
 * T114: New function for v2.0 by_tag challenges.
 */
export function getTagPuzzles(
  challenge: DailyIndex,
  tag: string
): DailyPuzzleEntry[] {
  const version = detectDailyVersion(challenge);
  
  if (version === '2.0' && challenge.by_tag) {
    const tagEntry = challenge.by_tag[tag];
    if (tagEntry) {
      return normalizePuzzleList(tagEntry.puzzles);
    }
  }
  
  // v1 fallback: check tag section
  if (challenge.tag && challenge.tag.tag === tag) {
    return normalizePuzzleList(challenge.tag.puzzles);
  }
  
  return [];
}

/**
 * Get available tags from a challenge.
 * T114: Get tag names from by_tag (v2.0) or tag (v1).
 */
export function getAvailableTags(challenge: DailyIndex): string[] {
  const version = detectDailyVersion(challenge);
  
  if (version === '2.0' && challenge.by_tag) {
    return Object.keys(challenge.by_tag);
  }
  
  // v1: Single tag
  if (challenge.tag) {
    return [challenge.tag.tag];
  }
  
  return [];
}

/**
 * Get timed sets info (v2.0).
 * T114: For UI to show set selection.
 */
export function getTimedSetsInfo(challenge: DailyIndex): { setNumber: number; puzzleCount: number }[] {
  const version = detectDailyVersion(challenge);
  
  if (version === '2.0' && challenge.timed && isTimedV2Format(challenge.timed)) {
    const timedV2 = challenge.timed as DailyTimedV2;
    return timedV2.sets.map(s => ({
      setNumber: s.set_number,
      puzzleCount: s.puzzles.length,
    }));
  }
  
  // v1: Single "set" with all queue puzzles
  const timed = challenge.timed as { queue?: (DailyPuzzleEntry | string)[] } | undefined;
  if (timed?.queue) {
    return [{ setNumber: 1, puzzleCount: timed.queue.length }];
  }
  
  return [];
}

/**
 * Get technique of the day (if any)
 */
export function getTechniqueOfDay(challenge: DailyIndex): string | undefined {
  return challenge.standard?.technique_of_day ?? challenge.techniqueOfDay;
}

// ============================================================================
// Export Service Interface
// ============================================================================

/**
 * Daily Challenge Service (object-based interface)
 */
export const dailyChallengeService = {
  getTodaysChallenge,
  getChallenge,
  getCountdownToNext,
  getAvailableChallenges,
  isChallengeAvailable,
  getPuzzleCount,
  getModePuzzles,
  getTechniqueOfDay,
  // v2.0 functions (T112-T114)
  detectDailyVersion,
  normalizeDailyChallenge,
  getTagPuzzles,
  getAvailableTags,
  getTimedSetsInfo,
  // Utility functions
  getTodayDateString,
  calculateCountdown,
  formatCountdown,
  isFutureDate,
};

export default dailyChallengeService;
