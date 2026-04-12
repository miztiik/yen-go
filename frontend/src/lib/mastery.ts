/**
 * Mastery System — Shared mastery level logic for Training, Collections, Technique.
 * @module lib/mastery
 *
 * Single source of truth for:
 * - MasteryLevel type
 * - Display labels
 * - Accuracy-based mastery calculation
 *
 * Mastery is based on SKILL (accuracy) not just completion:
 * - accuracy = (correct / attempted) * 100
 * - Volume thresholds ensure we have enough data to judge
 *
 * All pages (Training, Collections, Technique) use accuracy-based mastery.
 */

// ============================================================================
// Types
// ============================================================================

export type MasteryLevel = 'new' | 'started' | 'learning' | 'practiced' | 'proficient' | 'mastered';

// ============================================================================
// Constants
// ============================================================================

/** Display labels for each mastery level */
export const MASTERY_LABELS: Record<MasteryLevel, string> = {
  new: 'Begin',
  started: 'Continue',
  learning: 'Learning',
  practiced: 'Practiced',
  proficient: 'Proficient',
  mastered: 'Mastered',
};

/** Accuracy thresholds (percentage) */
export const MASTERY_THRESHOLDS = {
  learning: 50, // < 50% accuracy = struggling
  practiced: 70, // 50-69% = getting better
  proficient: 85, // 70-84% = good
  mastered: 85, // ≥ 85% + volume = mastered
} as const;

/** Minimum volume thresholds */
export const VOLUME_THRESHOLDS = {
  minForJudgment: 5, // Need at least 5 attempts to judge skill
  minForMastery: 10, // Need at least 10 for mastery (or 50% of total if less available)
} as const;

// ============================================================================
// Functions
// ============================================================================

/**
 * Calculate mastery level from accuracy and volume.
 *
 * @param accuracy Accuracy percentage (0-100): (correct / attempted) * 100
 * @param attempted Number of puzzles attempted
 * @param total Total puzzles available (for coverage check)
 * @returns MasteryLevel based on accuracy thresholds
 *
 * Algorithm:
 * - 0 attempts → 'new' (Begin)
 * - < 5 attempts → 'started' (Continue) — not enough data to judge
 * - < 50% accuracy → 'learning'
 * - < 70% accuracy → 'practiced'
 * - < 85% accuracy → 'proficient'
 * - ≥ 85% accuracy + sufficient volume → 'mastered'
 */
export function getMasteryFromAccuracy(
  accuracy: number,
  attempted: number,
  total: number
): MasteryLevel {
  if (attempted === 0) return 'new';
  if (attempted < VOLUME_THRESHOLDS.minForJudgment) return 'started';
  if (accuracy < MASTERY_THRESHOLDS.learning) return 'learning';
  if (accuracy < MASTERY_THRESHOLDS.practiced) return 'practiced';
  if (accuracy < MASTERY_THRESHOLDS.proficient) return 'proficient';

  // For mastery, require sufficient volume:
  // Either 10+ puzzles, or 50% of available puzzles (whichever is lower)
  const minForMastery = Math.min(VOLUME_THRESHOLDS.minForMastery, Math.ceil(total * 0.5));
  if (attempted < minForMastery) return 'proficient';

  return 'mastered';
}

/**
 * Calculate mastery from progress object with accuracy.
 * This is the primary interface for Training and Collections.
 *
 * @param progress Object with completed count, total, and accuracy percentage
 */
export function getMasteryFromProgress(
  progress: { completed: number; total: number; accuracy?: number | undefined } | undefined
): MasteryLevel {
  if (!progress || progress.total === 0) return 'new';
  // If accuracy is provided, use accuracy-based calculation
  // Otherwise, assume 100% accuracy (completed = correct)
  const accuracy = progress.accuracy ?? 100;
  return getMasteryFromAccuracy(accuracy, progress.completed, progress.total);
}

/**
 * Legacy: Calculate mastery from percentage (completion-based).
 * DEPRECATED: Use getMasteryFromAccuracy for accuracy-based mastery.
 * Kept for backward compatibility during migration.
 */
export function getMasteryFromPercent(pct: number, hasAnyProgress: boolean): MasteryLevel {
  if (!hasAnyProgress) return 'new';
  // Convert completion % to approximate mastery using same thresholds
  // This assumes 100% accuracy, just measuring coverage
  if (pct >= 100) return 'mastered';
  if (pct >= 75) return 'proficient';
  if (pct >= 50) return 'practiced';
  if (pct >= 25) return 'learning';
  return 'started';
}
