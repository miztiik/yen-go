/**
 * Data recovery for corrupted or invalid progress data.
 * @module lib/progress/recovery
 */

import type { UserProgress } from '../../types/progress';
import { createDefaultProgress } from '../../types/progress';
import type { StorageResult } from './storage';
import { migrateProgress, validateProgress, ensureComplete } from './migrations';

/**
 * Recovery action taken.
 */
export type RecoveryAction =
  | 'none' // No recovery needed
  | 'migrated' // Data was migrated to new version
  | 'repaired' // Data was partially repaired
  | 'reset' // Data was reset to defaults
  | 'created'; // Fresh data created (no existing data)

/**
 * Recovery result with details.
 */
export interface RecoveryResult {
  readonly success: boolean;
  readonly progress: UserProgress;
  readonly action: RecoveryAction;
  readonly message: string;
  readonly warnings: readonly string[];
}

/**
 * Try to parse JSON safely.
 *
 * @param json - JSON string to parse
 * @returns Parsed object or null on error
 */
export function safeJsonParse(json: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(json);
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Attempt to recover user progress from raw data.
 * Tries multiple strategies in order:
 * 1. Parse and validate as-is
 * 2. Migrate if version is old
 * 3. Repair if fields are missing
 * 4. Reset to defaults if unrecoverable
 *
 * @param rawData - Raw string from storage
 * @returns Recovery result with recovered progress
 */
export function recoverProgress(rawData: string | null): RecoveryResult {
  const warnings: string[] = [];

  // No data - create fresh
  if (rawData === null || rawData === '') {
    return {
      success: true,
      progress: createDefaultProgress(),
      action: 'created',
      message: 'Created new progress data.',
      warnings: [],
    };
  }

  // Try to parse
  const parsed = safeJsonParse(rawData);
  if (!parsed) {
    warnings.push('Data was corrupted and could not be parsed. Progress has been reset.');
    return {
      success: true,
      progress: createDefaultProgress(),
      action: 'reset',
      message: 'Progress data was corrupted. Starting fresh.',
      warnings,
    };
  }

  // Check if already valid
  const validationResult = validateProgress(parsed);
  if (validationResult.success) {
    // Check if migration needed
    const currentVersion = typeof parsed.version === 'number' ? parsed.version : 0;
    if (currentVersion < 1) {
      const migrationResult = migrateProgress(parsed);
      if (migrationResult.success && migrationResult.progress) {
        return {
          success: true,
          progress: migrationResult.progress,
          action: 'migrated',
          message: `Progress migrated from v${currentVersion} to v1.`,
          warnings: [],
        };
      }
    }

    // Valid as-is
    return {
      success: true,
      progress: parsed as unknown as UserProgress,
      action: 'none',
      message: 'Progress loaded successfully.',
      warnings: [],
    };
  }

  // Try migration
  const migrationResult = migrateProgress(parsed);
  if (migrationResult.success && migrationResult.progress) {
    if (migrationResult.migrationsApplied.length > 0) {
      return {
        success: true,
        progress: migrationResult.progress,
        action: 'migrated',
        message: `Progress migrated through versions: ${migrationResult.migrationsApplied.join(' → ')}.`,
        warnings: [],
      };
    }

    return {
      success: true,
      progress: migrationResult.progress,
      action: 'none',
      message: 'Progress loaded successfully.',
      warnings: [],
    };
  }

  // Try repair (fill in missing fields)
  try {
    const repaired = ensureComplete(parsed as Partial<UserProgress>);
    const repairedValidation = validateProgress(repaired as unknown as Record<string, unknown>);

    if (repairedValidation.success) {
      warnings.push('Some progress data was missing and has been set to defaults.');
      return {
        success: true,
        progress: repaired,
        action: 'repaired',
        message: 'Progress data was partially recovered.',
        warnings,
      };
    }
  } catch {
    // Repair failed
  }

  // Last resort - reset to defaults
  warnings.push('Progress data was severely corrupted. All progress has been reset.');
  return {
    success: true,
    progress: createDefaultProgress(),
    action: 'reset',
    message: 'Progress has been reset due to unrecoverable data.',
    warnings,
  };
}

/**
 * Recovery result for storage operations.
 */
export interface StorageRecoveryResult extends StorageResult<UserProgress> {
  readonly action: RecoveryAction;
  readonly warnings: readonly string[];
}

/**
 * Load and recover progress from storage.
 * Combines storage read with recovery logic.
 *
 * @param getRaw - Function to get raw data from storage
 * @returns Storage recovery result
 */
export function loadAndRecoverProgress(getRaw: () => string | null): StorageRecoveryResult {
  try {
    const rawData = getRaw();
    const recoveryResult = recoverProgress(rawData);

    const result: StorageRecoveryResult = {
      success: recoveryResult.success,
      data: recoveryResult.progress,
      action: recoveryResult.action,
      warnings: recoveryResult.warnings,
    };

    if (!recoveryResult.success) {
      return { ...result, error: recoveryResult.message };
    }

    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return {
      success: false,
      action: 'reset',
      warnings: ['Failed to access storage. Using default progress.'],
      error: `Storage error: ${message}`,
      data: createDefaultProgress(),
    };
  }
}

/**
 * Create backup of current progress data.
 *
 * @param progress - Progress to backup
 * @returns Backup string with metadata
 */
export function createBackup(progress: UserProgress): string {
  const backup = {
    _backup: {
      version: 1,
      createdAt: new Date().toISOString(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    },
    progress,
  };
  return JSON.stringify(backup, null, 2);
}

/**
 * Restore progress from backup.
 *
 * @param backupJson - Backup JSON string
 * @returns Restored progress or null on error
 */
export function restoreFromBackup(backupJson: string): RecoveryResult {
  const parsed = safeJsonParse(backupJson);
  if (!parsed) {
    return {
      success: false,
      progress: createDefaultProgress(),
      action: 'reset',
      message: 'Backup data could not be parsed.',
      warnings: ['Invalid backup format.'],
    };
  }

  // Check if it's a backup format or raw progress
  if ('_backup' in parsed && 'progress' in parsed) {
    const progressData = parsed.progress as Record<string, unknown>;
    return recoverProgress(JSON.stringify(progressData));
  }

  // Try as raw progress
  return recoverProgress(backupJson);
}

/**
 * Validate progress data integrity.
 *
 * @param progress - Progress to validate
 * @returns Array of integrity issues found
 */
export function checkDataIntegrity(progress: UserProgress): readonly string[] {
  const issues: string[] = [];

  // Check completedPuzzles integrity
  const completionCount = Object.keys(progress.completedPuzzles).length;
  if (completionCount !== progress.statistics.totalPuzzlesSolved) {
    issues.push(
      `Completion count mismatch: ${completionCount} completions but stats show ${progress.statistics.totalPuzzlesSolved}`
    );
  }

  // Check for invalid completion records
  for (const [id, completion] of Object.entries(progress.completedPuzzles)) {
    if (id !== completion.puzzleId) {
      issues.push(`Puzzle ID mismatch: key "${id}" but record shows "${completion.puzzleId}"`);
    }
    if (completion.timeSpentMs < 0) {
      issues.push(`Negative time for puzzle ${id}: ${completion.timeSpentMs}ms`);
    }
    if (completion.attempts < 0) {
      issues.push(`Negative attempts for puzzle ${id}: ${completion.attempts}`);
    }
  }

  // Check streak data integrity
  if (progress.streakData.currentStreak > progress.streakData.longestStreak) {
    issues.push(
      `Current streak (${progress.streakData.currentStreak}) exceeds longest streak (${progress.streakData.longestStreak})`
    );
  }

  return issues;
}

/**
 * Repair data integrity issues.
 *
 * @param progress - Progress to repair
 * @returns Repaired progress
 */
export function repairDataIntegrity(progress: UserProgress): UserProgress {
  let repaired = { ...progress };

  // Fix completion count in stats
  const completionCount = Object.keys(progress.completedPuzzles).length;
  if (completionCount !== progress.statistics.totalPuzzlesSolved) {
    repaired = {
      ...repaired,
      statistics: {
        ...repaired.statistics,
        totalPuzzlesSolved: completionCount,
      },
    };
  }

  // Fix puzzle ID mismatches
  const fixedCompletions: Record<string, (typeof progress.completedPuzzles)[string]> = {};
  for (const [id, completion] of Object.entries(progress.completedPuzzles)) {
    fixedCompletions[id] = {
      ...completion,
      puzzleId: id,
      timeSpentMs: Math.max(0, completion.timeSpentMs),
      attempts: Math.max(0, completion.attempts),
      hintsUsed: Math.max(0, completion.hintsUsed),
    };
  }
  repaired = { ...repaired, completedPuzzles: fixedCompletions };

  // Fix streak data
  if (progress.streakData.currentStreak > progress.streakData.longestStreak) {
    repaired = {
      ...repaired,
      streakData: {
        ...repaired.streakData,
        longestStreak: progress.streakData.currentStreak,
      },
    };
  }

  return repaired;
}
