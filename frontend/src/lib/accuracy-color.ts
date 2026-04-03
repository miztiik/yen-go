/**
 * Accuracy 3-tier semantic color system (T068)
 *
 * Provides consistent accuracy-based coloring across all pages:
 * - >=70%: success (green)
 * - >=50%: warning (amber)
 * - <50%: error (red)
 */

/**
 * Get the semantic color CSS variable class for an accuracy percentage.
 * @param accuracy - Accuracy percentage (0-100)
 * @returns Tailwind text color class using semantic color tokens
 */
export function getAccuracyColorClass(accuracy: number): string {
  if (accuracy >= 70) return 'text-[--color-success]';
  if (accuracy >= 50) return 'text-[--color-warning]';
  return 'text-[--color-error]';
}

/**
 * Get the semantic color CSS variable for an accuracy percentage.
 * @param accuracy - Accuracy percentage (0-100)
 * @returns CSS custom property string (e.g., 'var(--color-success)')
 */
export function getAccuracyColor(accuracy: number): string {
  if (accuracy >= 70) return 'var(--color-success)';
  if (accuracy >= 50) return 'var(--color-warning)';
  return 'var(--color-error)';
}
