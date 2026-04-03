/**
 * useHints Hook
 * @module hooks/useHints
 *
 * React hook for managing hint state and progressive disclosure.
 * Supports 3-tier YH hint progression with board marker placement.
 *
 * Covers: FR-032 to FR-035, US4, US5
 * Spec 125, Task T079
 */

import { useState, useCallback, useMemo } from 'preact/hooks';
import type { RefObject } from 'preact';
import type { Puzzle } from '../types/puzzle';
import type { GobanInstance } from './useGoban';

/** Maximum hint tiers (defined by YH property format) */
const MAX_HINT_TIERS = 3;

/** Hint state */
export interface HintState {
  /** Hints that have been revealed so far */
  readonly revealedHints: readonly string[];
  /** Index of the next hint to reveal (0-based) */
  readonly nextHintIndex: number;
  /** Whether more hints are available */
  readonly hasMoreHints: boolean;
  /** Total number of hints available */
  readonly totalHints: number;
  /** Number of hints used */
  readonly hintsUsed: number;
  /** Current tier (1-3 or 0 if no hints used) */
  readonly currentTier: number;
}

/** Hint actions */
export interface HintActions {
  /** Request the next hint */
  requestHint: () => string | null;
  /** Reset hints to initial state */
  resetHints: () => void;
  /** Get hint by index (for review mode) */
  getHintByIndex: (index: number) => string | null;
  /** Get all hints (for review mode) */
  getAllHints: () => readonly string[];
}

/** Return type of useHints hook */
export interface UseHintsResult extends HintState, HintActions {}

/**
 * Options for useHints hook
 */
export interface UseHintsOptions {
  /** Whether hints are enabled (default: true) */
  enabled?: boolean;
  /** Goban ref for placing hint markers on board */
  gobanRef?: RefObject<GobanInstance | null>;
}

/**
 * Hook for managing puzzle hints with progressive disclosure.
 *
 * Supports two modes:
 * 1. Puzzle-based: Extracts hint from puzzle.hint
 * 2. Array-based: Accepts hints array directly (e.g., from YH metadata)
 *
 * @param puzzleOrHints - Puzzle object or hints array from YH property
 * @param options - Configuration options
 * @returns Hint state and actions
 *
 * @example
 * ```tsx
 * // With puzzle object
 * const { revealedHints, requestHint, hasMoreHints } = useHints(puzzle);
 *
 * // With hints array from metadata
 * const { revealedHints, requestHint } = useHints(metadata.hints, {
 *   gobanRef, // For placing markers on board
 * });
 *
 * return (
 *   <div>
 *     {revealedHints.map((hint, i) => <p key={i}>{hint}</p>)}
 *     {hasMoreHints && (
 *       <button onClick={() => requestHint()}>Get Hint</button>
 *     )}
 *   </div>
 * );
 * ```
 */
export function useHints(
  puzzleOrHints: Puzzle | readonly string[] | null,
  options: UseHintsOptions | boolean = true
): UseHintsResult {
  // Normalize options
  const opts: UseHintsOptions = typeof options === 'boolean'
    ? { enabled: options }
    : options;
  const enabled = opts.enabled !== false;
  const gobanRef = opts.gobanRef;

  // Track which hints have been revealed
  const [revealedCount, setRevealedCount] = useState(0);

  // Get hints array from puzzle or direct array
  const hints = useMemo(() => {
    if (!enabled) return [];
    if (puzzleOrHints === null) return [];

    // If it's an array, use directly (from YH metadata)
    if (Array.isArray(puzzleOrHints)) {
      return puzzleOrHints.slice(0, MAX_HINT_TIERS);
    }

    // If it's a Puzzle object, extract hint
    const puzzle = puzzleOrHints as Puzzle;
    if (!puzzle.hint) return [];
    return [puzzle.hint];
  }, [puzzleOrHints, enabled]);

  // Compute derived state
  const revealedHints = useMemo(
    () => hints.slice(0, revealedCount),
    [hints, revealedCount]
  );

  const hasMoreHints = revealedCount < hints.length;
  const totalHints = hints.length;
  const hintsUsed = revealedCount;
  const currentTier = revealedCount; // Same as revealedCount

  /**
   * Place a hint marker on the board if hint contains coordinate.
   */
  const placeHintMarker = useCallback((hintText: string): void => {
    const goban = gobanRef?.current;
    if (goban === null || goban === undefined) return;

    // Parse coordinate from hint text (e.g., "Focus on D4" or "cg")
    // Look for patterns like "D4", "Q16", or "ab" (SGF coords)
    const coordMatch = hintText.match(/\b([A-HJ-T])(\d{1,2})\b/i); // Skip 'I'
    const sgfMatch = hintText.match(/\b([a-s]{2})\b/);

    let col: number | null = null;
    let row: number | null = null;

    if (coordMatch !== null && coordMatch[1] !== undefined && coordMatch[2] !== undefined) {
      // Convert display coord to numeric (D4 → [3, 3])
      const letter = coordMatch[1].toUpperCase();
      // Skip 'I' in Go coordinates (A-H, J-T)
      let colNum = letter.charCodeAt(0) - 65;
      if (letter > 'I') colNum--; // Adjust for skipped 'I'
      col = colNum;
      row = parseInt(coordMatch[2], 10) - 1;
    } else if (sgfMatch !== null && sgfMatch[1] !== undefined) {
      // Convert SGF coord to numeric (aa → [0, 0])
      const sgfCoord = sgfMatch[1];
      col = sgfCoord.charCodeAt(0) - 97;
      row = sgfCoord.charCodeAt(1) - 97;
    }

    if (col !== null && row !== null && col >= 0 && row >= 0) {
      // Use goban's setMarks API if available
      // Mark format: { 'dd': 'circle' } or similar
      if (typeof goban.setMarks === 'function') {
        const move = String.fromCharCode(97 + col) + String.fromCharCode(97 + row);
        goban.setMarks({
          [move]: 'circle', // Use circle mark type for hint
        });
      }
    }
  }, [gobanRef]);

  /**
   * Clear all hint markers from the board.
   */
  const clearHintMarkers = useCallback((): void => {
    const goban = gobanRef?.current;
    if (goban === null || goban === undefined) return;

    if (typeof goban.setMarks === 'function') {
      goban.setMarks({});
    }
  }, [gobanRef]);

  /**
   * Request the next hint.
   * @returns The next hint text, or null if no more hints
   */
  const requestHint = useCallback((): string | null => {
    if (!enabled || revealedCount >= hints.length) {
      return null;
    }

    const nextHint = hints[revealedCount];
    setRevealedCount((prev) => prev + 1);

    // Place marker on board if hint contains coordinate
    if (nextHint !== undefined) {
      placeHintMarker(nextHint);
    }

    return nextHint ?? null;
  }, [enabled, hints, revealedCount, placeHintMarker]);

  /**
   * Reset hints to initial state.
   */
  const resetHints = useCallback((): void => {
    setRevealedCount(0);
    clearHintMarkers();
  }, [clearHintMarkers]);

  /**
   * Get a specific hint by index (for review mode).
   * @param index - The hint index (0-based)
   * @returns The hint text, or null if invalid index
   */
  const getHintByIndex = useCallback(
    (index: number): string | null => {
      if (index < 0 || index >= hints.length) {
        return null;
      }
      return hints[index] ?? null;
    },
    [hints]
  );

  /**
   * Get all hints (for review mode).
   * @returns All hint texts
   */
  const getAllHints = useCallback((): readonly string[] => {
    return hints;
  }, [hints]);

  return {
    // State
    revealedHints,
    nextHintIndex: revealedCount,
    hasMoreHints,
    totalHints,
    hintsUsed,
    currentTier,
    // Actions
    requestHint,
    resetHints,
    getHintByIndex,
    getAllHints,
  };
}

export default useHints;
