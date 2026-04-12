/**
 * Daily Challenge types for daily puzzle features
 * @module models/dailyChallenge
 *
 * Covers: FR-030 to FR-041 (Daily Challenge)
 *
 * Supports both v1 (legacy) and v2.0 (spec 035) daily formats.
 * v2.0 introduces: timed.sets[], by_tag{}, structured standard section
 */

import type { SkillLevel } from './collection';

// ============================================================================
// v2.0 Types (T108-T111 - spec 035 daily format)
// ============================================================================

/**
 * T108: A single timed set within a timed challenge (v2.0)
 * Each set contains a fixed number of puzzles for timed practice.
 */
export interface TimedSet {
  /** Set number (1-based) */
  readonly set_number: number;
  /** Puzzles in this set */
  readonly puzzles: readonly DailyPuzzleEntry[];
}

/**
 * T109: Timed challenge structure (v2.0)
 * Contains multiple timed sets with scoring configuration.
 */
export interface TimedChallenge {
  /** Array of timed sets (typically 3) */
  readonly sets: readonly TimedSet[];
  /** Number of sets */
  readonly set_count: number;
  /** Puzzles per set */
  readonly puzzles_per_set: number;
  /** Suggested time limits in seconds (e.g., [180, 300, 600, 900]) */
  readonly suggested_durations: readonly number[];
  /** Scoring points by difficulty level */
  readonly scoring: Readonly<Record<string, number>>;
}

/**
 * T110: By-tag challenge entry (v2.0)
 * Puzzles grouped by a specific technique tag.
 */
export interface ByTagChallengeEntry {
  /** Puzzles for this tag */
  readonly puzzles: readonly DailyPuzzleEntry[];
  /** Total count */
  readonly total: number;
}

/**
 * T110: By-tag challenges object (v2.0)
 * Maps tag names to their puzzle sets.
 */
export type ByTagChallenge = Readonly<Record<string, ByTagChallengeEntry>>;

/**
 * Standard daily challenge section (v2.0)
 * The main 30-puzzle daily challenge.
 */
export interface StandardDailyChallenge {
  /** Puzzles for standard daily */
  readonly puzzles: readonly DailyPuzzleEntry[];
  /** Total count */
  readonly total: number;
  /** Featured technique for this day */
  readonly technique_of_day?: string;
  /** Distribution by level (e.g., { "novice": 10, "beginner": 9 }) */
  readonly distribution?: Readonly<Record<string, number>>;
}

/**
 * T111: Daily challenge v2.0/v2.1 format (spec 035, spec 112)
 * New structured format with standard, timed, and by_tag sections.
 * v2.1 adds technique_of_day at root level.
 */
export interface DailyChallengeV2 {
  /** Schema version - "2.0" or "2.1" */
  readonly version: '2.0' | '2.1';
  /** Challenge date (YYYY-MM-DD) */
  readonly date: string;
  /** Generation timestamp */
  readonly generated_at: string;
  /** Standard daily challenge (30 puzzles) */
  readonly standard: StandardDailyChallenge;
  /** Timed challenge with sets */
  readonly timed: TimedChallenge;
  /** Challenges by tag/technique */
  readonly by_tag: ByTagChallenge;
  /** Week reference (e.g., "2026-W05") */
  readonly weekly_ref?: string;
  /** Config snapshot used for generation */
  readonly config_used?: Readonly<Record<string, unknown>>;
  /** Featured technique of the day at root level (v2.1, spec 112) */
  readonly technique_of_day?: string;
}

// ============================================================================
// v1 Types (Legacy - backward compatibility)
// ============================================================================

/**
 * Summary of a daily challenge for list/card display
 */
export interface DailyChallengeSummary {
  /** Date of the challenge (YYYY-MM-DD) */
  readonly date: string;
  /** Human-readable date (e.g., "January 28, 2026") */
  readonly displayDate: string;
  /** Number of puzzles */
  readonly puzzleCount: number;
  /** Difficulty breakdown */
  readonly byLevel: Readonly<Record<SkillLevel, number>>;
  /** Whether this is today's challenge */
  readonly isToday: boolean;
  /** Relative path to challenge JSON */
  readonly path: string;
}

/**
 * Puzzle entry within a daily challenge
 */
export interface DailyPuzzleEntry {
  /** Unique puzzle ID */
  readonly id: string;
  /** Relative path to SGF file */
  readonly path: string;
  /** Difficulty level */
  readonly level: SkillLevel;
  /** Optional technique tags */
  readonly tags?: readonly string[];
}

/**
 * Full daily challenge with puzzle list (v1 - legacy format)
 * @deprecated Use DailyChallengeV2 for new implementations
 */
export interface DailyChallenge {
  /** Schema version */
  readonly version: string;
  /** Challenge date (YYYY-MM-DD) */
  readonly date: string;
  /** Generation timestamp */
  readonly generatedAt: string;
  /** Ordered list of puzzles (v1 flat structure) */
  readonly puzzles: readonly DailyPuzzleEntry[];
}

/**
 * Union type for any daily challenge format (v1 or v2)
 */
export type AnyDailyChallenge = DailyChallenge | DailyChallengeV2;

/**
 * Type guard to check if a challenge is v2.x format (2.0 or 2.1)
 */
export function isDailyChallengeV2(challenge: AnyDailyChallenge): challenge is DailyChallengeV2 {
  return (
    (challenge.version === '2.0' || challenge.version === '2.1') &&
    'standard' in challenge &&
    'timed' in challenge
  );
}

/**
 * Normalized daily challenge (internal representation)
 * Converts both v1 and v2 formats to a common structure.
 */
export interface NormalizedDailyChallenge {
  /** Original version */
  readonly originalVersion: string;
  /** Challenge date */
  readonly date: string;
  /** Generation timestamp */
  readonly generatedAt: string;
  /** Standard puzzles (from v1.puzzles or v2.standard.puzzles) */
  readonly standardPuzzles: readonly DailyPuzzleEntry[];
  /** Timed sets (v2 only, empty for v1) */
  readonly timedSets: readonly TimedSet[];
  /** By-tag challenges (v2 only, empty for v1) */
  readonly byTag: ByTagChallenge;
  /** Technique of day */
  readonly techniqueOfDay?: string;
  /** Level distribution */
  readonly distribution?: Readonly<Record<string, number>>;
  /** Timed scoring */
  readonly timedScoring?: Readonly<Record<string, number>>;
  /** Suggested durations for timed mode */
  readonly suggestedDurations?: readonly number[];
}

/**
 * Countdown time until next daily challenge
 */
export interface DailyCountdown {
  /** Hours remaining */
  readonly hours: number;
  /** Minutes remaining */
  readonly minutes: number;
  /** Seconds remaining */
  readonly seconds: number;
  /** Total milliseconds remaining */
  readonly totalMs: number;
  /** Whether countdown has ended (new challenge available) */
  readonly isReady: boolean;
}

/**
 * Daily challenge mode selection
 */
export type DailyChallengeMode = 'standard' | 'timed';

/**
 * User's progress on a specific daily challenge
 */
export interface DailyProgress {
  /** Challenge date (YYYY-MM-DD) */
  readonly date: string;
  /** IDs of completed puzzles */
  readonly completed: readonly string[];
  /** Current puzzle index (standard mode) */
  readonly currentIndex: number;
  /** When user started */
  readonly startedAt: string;
  /** Last activity */
  readonly lastActivity: string;
  /** Performance metrics */
  readonly performance?: DailyPerformanceData;
}

/**
 * Performance data for daily challenge
 */
export interface DailyPerformanceData {
  /** Accuracy by level: { "beginner": { correct: 5, total: 6 } } */
  readonly accuracyByLevel: Readonly<Record<string, { correct: number; total: number }>>;
  /** Total time in milliseconds */
  readonly totalTimeMs: number;
  /** Timed mode high score */
  readonly timedHighScore?: number;
}

/**
 * Daily challenge completion result
 */
export interface DailyChallengeResult {
  /** Challenge date */
  readonly date: string;
  /** Total puzzles attempted */
  readonly totalPuzzles: number;
  /** Puzzles solved correctly */
  readonly correctCount: number;
  /** Overall accuracy percentage (0-100) */
  readonly accuracy: number;
  /** Total time spent (milliseconds) */
  readonly totalTimeMs: number;
  /** Performance by level */
  readonly byLevel: Readonly<Record<string, { correct: number; total: number }>>;
  /** Mode played */
  readonly mode: DailyChallengeMode;
}

/**
 * Daily challenge status for UI display
 */
export type DailyStatus = 'not-started' | 'in-progress' | 'completed';

/**
 * Get status from progress
 */
export function getDailyStatus(
  progress: DailyProgress | undefined,
  totalPuzzles: number
): DailyStatus {
  if (!progress) return 'not-started';
  if (progress.completed.length >= totalPuzzles) return 'completed';
  return 'in-progress';
}

/**
 * Format date for display (e.g., "January 28, 2026")
 */
export function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Get today's date in YYYY-MM-DD format
 */
export function getTodayDateString(): string {
  const now = new Date();
  return now.toISOString().split('T')[0] as string;
}

/**
 * Calculate countdown until next daily challenge (midnight UTC)
 */
export function calculateCountdown(): DailyCountdown {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  tomorrow.setUTCHours(0, 0, 0, 0);

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
