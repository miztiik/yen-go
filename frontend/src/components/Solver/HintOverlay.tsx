/**
 * HintOverlay — 3-level progressive hints for puzzle solving.
 *
 * Levels:
 * - Level 0: No hints shown
 * - Level 1: Textual hint from YH property (or coordinate if no YH)
 * - Level 2: Board area quadrant highlight
 * - Level 3: Exact coordinate marker via setColoredCircles
 *
 * This component is display-only — the hint trigger button lives in SolverView's
 * sidebar. The `currentLevel` prop controls which hint tier is shown.
 *
 * Spec 127: FR-040, FR-041, US5, contracts/solver.ts
 * @module components/Solver/HintOverlay
 */

import type { VNode } from 'preact';
import { HintIcon } from '../shared/icons';

// ============================================================================
// Types
// ============================================================================

export interface HintState {
  level: 0 | 1 | 2 | 3;
  maxLevel: 1 | 2 | 3;
  textHint: string | null;
  areaHighlight: { quadrant: string } | null;
  coordinateMarker: { x: number; y: number } | null;
}

export interface HintOverlayProps {
  /** YH hints from SGF (pipe-delimited, max 3). */
  hints: string[];
  /** Correct move coordinate for the current position. */
  correctMove: { x: number; y: number } | null;
  /** Board size for quadrant calculation. */
  boardSize?: number;
  /** Callback to place colored circle on board. */
  onPlaceMarker?: (x: number, y: number) => void;
  /** Current hint level (driven by parent). 0 = no hints shown. */
  currentLevel?: number;
  /** Human-readable corner label derived from YC property (e.g. "top-left corner"). Defaults to "board". */
  cornerLabel?: string;
}

// ============================================================================
// Helpers
// ============================================================================

function getQuadrant(x: number, y: number, size: number): string {
  const mid = Math.floor(size / 2);
  const row = y <= mid ? 'top' : 'bottom';
  const col = x <= mid ? 'left' : 'right';
  return `${row}-${col}`;
}

function getMaxLevel(hints: string[]): 1 | 2 | 3 {
  // Dynamic tier count: authored text hints + board marker
  // 3 hints → 3 text tiers (marker at tier 3)
  // 2 hints → 2 text tiers (marker at tier 2)
  // 1 hint  → 1 text tier  (marker at tier 1)
  // 0 hints → marker only   (maxLevel = 1)
  const count = Math.min(hints.length, 3);
  return Math.max(count, 1) as 1 | 2 | 3;
}

/**
 * Map a YC corner position code to a human-readable label.
 * Exported for unit testing.
 */
export function cornerPositionToLabel(corner?: string): string {
  switch (corner) {
    case 'TL': return 'top-left corner';
    case 'TR': return 'top-right corner';
    case 'BL': return 'bottom-left corner';
    case 'BR': return 'bottom-right corner';
    case 'C':  return 'center';
    case 'E':  return 'edge';
    default:   return 'board';
  }
}

/**
 * Map hint tier (1-N) to display content based on available hint texts.
 *
 * No filler padding — if the backend provides fewer than 3 hints,
 * show fewer text tiers. The board marker is always the final action.
 *
 * Tier mapping (dynamic based on hint count):
 *   0 texts → no text tiers (board marker only)
 *   1 text  → T1: hints[0]
 *   2 texts → T1: hints[0] | T2: hints[1]
 *   3 texts → T1: hints[0] | T2: hints[1] | T3: hints[2]
 *
 * Exported for unit testing.
 */
export function computeHintDisplay(
  tier: number,
  hints: string[],
  _cornerLabel: string
): { text: string; isGenerated: boolean } {
  const count = hints.length;
  const idx = tier - 1;

  if (idx < count) {
    return { text: hints[idx], isGenerated: false };
  }

  // Beyond available hints — should not be called, but safe fallback
  return { text: 'No further hints available', isGenerated: true };
}

// ============================================================================
// Component
// ============================================================================

export function HintOverlay({
  hints,
  correctMove,
  boardSize: _boardSize = 19,
  currentLevel = 0,
  cornerLabel = 'board',
}: HintOverlayProps): VNode | null {
  const maxLevel = getMaxLevel(hints);
  const level = Math.min(currentLevel, maxLevel) as 0 | 1 | 2 | 3;

  // Build progressive hint displays for tiers 1..level using computeHintDisplay
  const hintDisplays: { text: string; isGenerated: boolean }[] = [];
  for (let tier = 1; tier <= level; tier++) {
    // Only show text tiers that have actual hints
    if (tier <= hints.length) {
      hintDisplays.push(computeHintDisplay(tier, hints, cornerLabel));
    }
  }

  // Board marker shown at the final level (maxLevel), which is
  // hints.length for 1-3 hints, or 1 for 0 hints
  const coordinateMarker = level >= maxLevel && correctMove ? correctMove : null;

  // Nothing to show
  if (level === 0) return null;

  return (
    <div className="flex flex-col gap-1.5" data-component="hint-overlay">
      {/* Progressive hint tiers — rendered via computeHintDisplay */}
      {hintDisplays.map((display, i) => {
        // The last hint gets accent styling when the board marker is active
        const isCoordinateHint = coordinateMarker != null && i === hintDisplays.length - 1;
        return (
          <div
            key={i}
            className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${
              isCoordinateHint
                ? 'bg-[var(--color-accent)]/20 text-[var(--color-accent)] font-semibold'
                : display.isGenerated
                  ? 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)]'
                  : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)]'
            }`}
          >
            <HintIcon size={14} className="mt-0.5 flex-shrink-0 text-[var(--color-accent)]" />
            <span>{display.text}</span>
          </div>
        );
      })}
    </div>
  );
}

export { getQuadrant, getMaxLevel };
export type { HintOverlayProps as HintOverlayPropsExport };
export default HintOverlay;
