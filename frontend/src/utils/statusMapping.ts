/**
 * Status mapping utilities for type-safe status conversions.
 * @module utils/statusMapping
 *
 * Eliminates `as any` casts by providing explicit type-safe mapping
 * between the different status systems used across the app.
 *
 * Spec 129, T108 — FR-011
 */

// ============================================================================
// ProblemNav status mapping
// ============================================================================

/** ProblemNav uses 'solved' | 'failed' | 'unsolved' */
export type ProblemNavStatus = 'solved' | 'failed' | 'unsolved';

/**
 * Map completion state to ProblemNav status.
 */
export function toProblemNavStatus(
  completed: boolean,
  failed: boolean,
): ProblemNavStatus {
  if (failed) return 'failed';
  if (completed) return 'solved';
  return 'unsolved';
}

// ============================================================================
// Carousel status mapping
// ============================================================================

/** Carousel uses 'correct' | 'incorrect' | 'current' | 'unsolved' */
export type CarouselStatus = 'correct' | 'incorrect' | 'current' | 'unsolved';

/**
 * Map puzzle index + sets to carousel indicator status.
 */
export function toCarouselStatus(
  index: number,
  currentIndex: number,
  completedIndexes: ReadonlySet<number>,
  failedIndexes: ReadonlySet<number>,
): CarouselStatus {
  if (index === currentIndex) return 'current';
  if (failedIndexes.has(index)) return 'incorrect';
  if (completedIndexes.has(index)) return 'correct';
  return 'unsolved';
}
