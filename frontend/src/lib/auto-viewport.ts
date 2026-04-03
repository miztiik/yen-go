/**
 * Auto-Viewport Utility — YC property-based board auto-zoom.
 *
 * Reads YC (corner position) from SGF metadata and returns
 * viewport bounds for goban's setBounds() API.
 *
 * Spec 132, US18, Tasks T195–T198
 * @module lib/auto-viewport
 */

/**
 * YC corner position values from SGF schema v10.
 * TL = Top-Left, TR = Top-Right, BL = Bottom-Left, BR = Bottom-Right
 * C = Center, E = Edge — no zoom for these.
 */
export type CornerPosition = 'TL' | 'TR' | 'BL' | 'BR' | 'C' | 'E';

/**
 * Viewport bounds for goban setBounds().
 * Coordinates are 0-indexed, representing the visible region of the board.
 */
export interface ViewportBounds {
  top: number;
  left: number;
  bottom: number;
  right: number;
}

/**
 * Parse YC property from raw SGF string.
 * Returns undefined if YC is not present.
 */
export function parseYCProperty(sgf: string): CornerPosition | undefined {
  const match = /YC\[([^\]]*)\]/.exec(sgf);
  if (!match || !match[1]) return undefined;
  const value = match[1].trim().toUpperCase();
  if (['TL', 'TR', 'BL', 'BR', 'C', 'E'].includes(value)) {
    return value as CornerPosition;
  }
  // Warn about unrecognized values (e.g. old T/B/L/R before canonical mapping)
  console.warn(`[auto-viewport] Unrecognized YC value "${match[1]}", ignoring`);
  return undefined;
}

/**
 * Transform a YC corner position through active board transforms.
 *
 * The YC property in the SGF is not updated by coordinate transforms,
 * so we must map it manually: rotation maps corners clockwise,
 * flipH swaps left/right, flipV swaps top/bottom.
 *
 * @param corner - Original YC corner position from SGF
 * @param transforms - Active transform settings
 * @returns Transformed corner position
 */
export function transformCornerPosition(
  corner: CornerPosition | undefined,
  transforms: { flipH?: boolean; flipV?: boolean; rotation?: 0 | 90 | 180 | 270 },
): CornerPosition | undefined {
  if (!corner || corner === 'C' || corner === 'E') return corner;

  let result = corner;

  // Apply rotation first (clockwise): TL→TR→BR→BL→TL
  const rotation = transforms.rotation ?? 0;
  const steps = rotation / 90;
  const cwOrder: ('TL' | 'TR' | 'BR' | 'BL')[] = ['TL', 'TR', 'BR', 'BL'];
  if (steps > 0) {
    const idx = cwOrder.indexOf(result);
    if (idx >= 0) {
      result = cwOrder[(idx + steps) % 4]!;
    }
  }

  if (transforms.flipH) {
    // Swap left ↔ right: TL↔TR, BL↔BR
    result = result === 'TL' ? 'TR' : result === 'TR' ? 'TL'
           : result === 'BL' ? 'BR' : 'BL';
  }

  if (transforms.flipV) {
    // Swap top ↔ bottom: TL↔BL, TR↔BR
    result = result === 'TL' ? 'BL' : result === 'BL' ? 'TL'
           : result === 'TR' ? 'BR' : 'TR';
  }

  return result;
}

/**
 * Map YC corner position to viewport bounds for a given board size.
 *
 * Returns undefined for C, E, or missing YC — use full board view.
 * For corners, returns roughly 60% of the board focused on that quadrant
 * (overlapping slightly to show context).
 *
 * @param corner - YC corner position
 * @param boardSize - Board size (typically 9, 13, or 19)
 */
export function getCornerBounds(
  corner: CornerPosition | undefined,
  boardSize: number = 19,
): ViewportBounds | undefined {
  if (!corner || corner === 'C' || corner === 'E') return undefined;

  // Show ~60% of the board (11 lines on a 19×19)
  const extent = Math.ceil(boardSize * 0.6);
  const max = boardSize - 1;

  switch (corner) {
    case 'TL':
      return { top: 0, left: 0, bottom: extent, right: extent };
    case 'TR':
      return { top: 0, left: max - extent, bottom: extent, right: max };
    case 'BL':
      return { top: max - extent, left: 0, bottom: max, right: extent };
    case 'BR':
      return { top: max - extent, left: max - extent, bottom: max, right: max };
    default:
      return undefined;
  }
}
