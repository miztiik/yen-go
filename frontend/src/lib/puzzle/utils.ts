/**
 * Puzzle utilities.
 * @module lib/puzzle/utils
 *
 * Spec 119: View Schema Simplification - utility functions for path-based ID extraction.
 */

/**
 * Extract puzzle ID from SGF file path.
 *
 * The puzzle ID is the filename without the .sgf extension.
 * This allows views to omit the redundant `id` field since it's
 * always derivable from the path.
 *
 * @param path - Relative path to SGF file (e.g., "sgf/beginner/batch-0001/abc123def456.sgf")
 * @returns Puzzle ID (e.g., "abc123def456")
 *
 * @example
 * ```ts
 * extractPuzzleIdFromPath("sgf/beginner/batch-0001/abc123def456.sgf")
 * // Returns: "abc123def456"
 *
 * extractPuzzleIdFromPath("abc123.sgf")
 * // Returns: "abc123"
 * ```
 */
export function extractPuzzleIdFromPath(path: string): string {
  const filename = path.split('/').pop() ?? '';
  return filename.replace(/\.sgf$/, '');
}

/**
 * Extract level from SGF file path.
 *
 * The level is the first path segment after "sgf/".
 *
 * @param path - Relative path to SGF file
 * @returns Level slug (e.g., "beginner", "intermediate") or empty string if not found
 *
 * @example
 * ```ts
 * extractLevelFromPath("sgf/beginner/batch-0001/abc123.sgf")
 * // Returns: "beginner"
 * ```
 */
export function extractLevelFromPath(path: string): string {
  const parts = path.split('/');
  const sgfIndex = parts.indexOf('sgf');
  if (sgfIndex >= 0 && sgfIndex + 1 < parts.length) {
    return parts[sgfIndex + 1] ?? '';
  }
  return '';
}
