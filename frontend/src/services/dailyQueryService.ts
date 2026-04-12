/**
 * Daily challenge query service.
 *
 * Queries daily_schedule and daily_puzzles tables from the in-memory
 * yengo-search.db via sqliteService. No additional network requests needed.
 */

import { query } from './sqliteService';

// --- Types ---

export interface DailyScheduleRow {
  date: string;
  version: string;
  generated_at: string;
  technique_of_day: string;
  attrs: string; // JSON string
}

export interface DailyPuzzleRow {
  date: string;
  content_hash: string;
  section: string;
  position: number;
  batch: string;
  level_id: number;
}

// --- Queries ---

/**
 * Get the daily schedule for a specific date.
 * Returns null if no schedule exists for that date.
 */
export function getDailySchedule(date: string): DailyScheduleRow | null {
  const rows = query<DailyScheduleRow>('SELECT * FROM daily_schedule WHERE date = ?', [date]);
  return rows[0] ?? null;
}

/**
 * Get daily puzzles for a date, optionally filtered by section.
 * Joins with puzzles table to get batch and level_id for path reconstruction.
 */
export function getDailyPuzzles(date: string, section?: string): DailyPuzzleRow[] {
  if (section) {
    return query<DailyPuzzleRow>(
      `SELECT dp.date, dp.content_hash, dp.section, dp.position,
              p.batch, p.level_id
       FROM daily_puzzles dp
       JOIN puzzles p ON dp.content_hash = p.content_hash
       WHERE dp.date = ? AND dp.section = ?
       ORDER BY dp.position`,
      [date, section]
    );
  }
  return query<DailyPuzzleRow>(
    `SELECT dp.date, dp.content_hash, dp.section, dp.position,
            p.batch, p.level_id
     FROM daily_puzzles dp
     JOIN puzzles p ON dp.content_hash = p.content_hash
     WHERE dp.date = ?
     ORDER BY dp.section, dp.position`,
    [date]
  );
}

/**
 * Check if a daily schedule exists for a given date.
 */
export function isDailyAvailable(date: string): boolean {
  const rows = query<{ c: number }>('SELECT COUNT(*) as c FROM daily_schedule WHERE date = ?', [
    date,
  ]);
  return (rows[0]?.c ?? 0) > 0;
}
