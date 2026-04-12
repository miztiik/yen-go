/**
 * Unified Coordinate Type (Besogo Gold Standard)
 * @module types/coordinate
 *
 * Single source of truth for coordinate representation.
 * All board/puzzle coordinates should use this type.
 *
 * Spec 122 - Phase 4, T4.1 (Besogo Gold Standard)
 *
 * CRITICAL: 1-indexed coordinates (Besogo pattern)
 * - x=1 is left edge, x=19 is right edge (for 19x19)
 * - y=1 is top edge, y=19 is bottom edge (for 19x19)
 * - NEVER subtract 1 for grid access - grids are pre-padded
 *
 * Constitution Compliance:
 * - VI. Type Safety: Consistent type definitions
 * - III. Single Source of Truth: One coordinate definition
 */

/**
 * Board coordinate using 1-indexed values (Besogo convention).
 *
 * @property x - Column (1 = left edge, 19 = right edge for 19x19)
 * @property y - Row (1 = top edge, 19 = bottom edge for 19x19)
 *
 * IMPORTANT: This is 1-indexed, NOT 0-indexed.
 *
 * Besogo reference: charToNum('a') = 1, not 0
 */
export interface Coord {
  readonly x: number;
  readonly y: number;
}

/**
 * @deprecated Use Coord instead. Legacy 0-indexed type for backward compatibility.
 * This will be removed - migrate to Coord.
 */
export type Coordinate = Coord;

/**
 * Check if two coordinates are equal
 */
export function coordEqual(a: Coord, b: Coord): boolean {
  return a.x === b.x && a.y === b.y;
}

/**
 * Create a coordinate from x, y values (1-indexed)
 */
export function coord(x: number, y: number): Coord {
  return { x, y };
}

/**
 * Convert 1-indexed coordinate to SGF format (aa-ss).
 *
 * Besogo pattern: numToChar = charCode 96 + x (where x is 1-indexed)
 * 'a'.charCodeAt(0) = 97, so 96 + 1 = 97 = 'a' ✓
 *
 * @param c - Board coordinate (1-indexed)
 * @returns SGF coordinate string (e.g., "aa", "dp", "ss")
 *
 * @example
 * coordToSgf({ x: 1, y: 1 }) // "aa"
 * coordToSgf({ x: 4, y: 16 }) // "dp"
 */
export function coordToSgf(c: Coord): string {
  // Besogo: numToChar would be charCode 96 + x (where x is 1-indexed)
  return String.fromCharCode(96 + c.x) + String.fromCharCode(96 + c.y);
}

/**
 * Convert SGF coordinate to 1-indexed coordinate.
 *
 * Besogo charToNum: c.charCodeAt(0) - 'a'.charCodeAt(0) + 1
 * Since 'a'.charCodeAt(0) = 97, this equals charCodeAt - 96
 *
 * @param sgf - SGF coordinate string (e.g., "aa", "dp")
 * @returns Board coordinate (1-indexed)
 * @throws Error if SGF string is invalid
 *
 * @example
 * sgfToCoord("aa") // { x: 1, y: 1 }   // 'a'=97, 97-96=1
 * sgfToCoord("dp") // { x: 4, y: 16 }  // 'd'=100, 100-96=4
 */
export function sgfToCoord(sgf: string): Coord {
  if (!sgf || sgf.length < 2) {
    throw new Error(`Invalid SGF coordinate: ${sgf}`);
  }

  // Besogo: charToNum returns charCodeAt(0) - 'a'.charCodeAt(0) + 1
  // Which equals charCodeAt(0) - 97 + 1 = charCodeAt(0) - 96
  const x = sgf.charCodeAt(0) - 96; // 'a'(97) - 96 = 1
  const y = sgf.charCodeAt(1) - 96; // 'a'(97) - 96 = 1

  // Valid range for 1-indexed: 1 to 19 (for standard boards)
  if (x < 1 || x > 19 || y < 1 || y > 19) {
    throw new Error(`SGF coordinate out of range: ${sgf}`);
  }

  return { x, y };
}

/**
 * Convert coordinate to human-readable format (A1-T19).
 * Column letters skip 'I' (Go convention).
 * Row numbers count from bottom (1) to top (size).
 *
 * @param c - Board coordinate (1-indexed)
 * @param boardSize - Board size (default 19)
 * @returns Human-readable string (e.g., "A1", "D16", "Q4")
 *
 * @example
 * coordToDisplay({ x: 1, y: 19 }, 19) // "A1" (bottom-left)
 * coordToDisplay({ x: 4, y: 4 }, 19) // "D16"
 */
export function coordToDisplay(c: Coord, boardSize = 19): string {
  const LETTERS = 'ABCDEFGHJKLMNOPQRST'; // No 'I'
  const col = LETTERS[c.x - 1] ?? '?'; // x=1 → index 0 → 'A'
  const row = boardSize - c.y + 1; // y=1 (top) → row=size, y=size (bottom) → row=1
  return `${col}${row}`;
}

/**
 * Convert human-readable coordinate to board coordinate (1-indexed)
 *
 * @param display - Human-readable string (e.g., "A1", "D16")
 * @param boardSize - Board size (default 19)
 * @returns Board coordinate (1-indexed)
 * @throws Error if string is invalid
 */
export function displayToCoord(display: string, boardSize = 19): Coord {
  if (!display || display.length < 2) {
    throw new Error(`Invalid coordinate: ${display}`);
  }

  const LETTERS = 'ABCDEFGHJKLMNOPQRST';
  const colLetter = display.charAt(0).toUpperCase();
  const rowStr = display.slice(1);

  const colIndex = LETTERS.indexOf(colLetter);
  if (colIndex === -1) {
    throw new Error(`Invalid column: ${colLetter}`);
  }

  const row = parseInt(rowStr, 10);
  if (isNaN(row) || row < 1 || row > boardSize) {
    throw new Error(`Invalid row: ${rowStr}`);
  }

  const x = colIndex + 1; // 1-indexed
  const y = boardSize - row + 1; // Convert from display row to y
  return { x, y };
}

/**
 * Check if coordinate is within board bounds (1-indexed).
 *
 * Besogo bounds: x >= 1 && y >= 1 && x <= size && y <= size
 *
 * @param c - Coordinate to check
 * @param boardSize - Board size (default 19)
 * @returns true if valid
 */
export function isValidCoord(c: Coord, boardSize = 19): boolean {
  return c.x >= 1 && c.x <= boardSize && c.y >= 1 && c.y <= boardSize;
}

/**
 * Check if x,y values are within board bounds (1-indexed).
 *
 * Besogo bounds: x >= 1 && y >= 1 && x <= size && y <= size
 */
export function isValidXY(x: number, y: number, boardSize = 19): boolean {
  return x >= 1 && x <= boardSize && y >= 1 && y <= boardSize;
}

/**
 * Convert coordinate to linear array index (Besogo fromXY pattern).
 * Useful for markup/hover layer indexing.
 *
 * Besogo: (x - 1) * sizeY + (y - 1) — converts 1-indexed to 0-based array
 *
 * @example
 * coordToLinear({ x: 1, y: 1 }, 19) // 0   (top-left)
 * coordToLinear({ x: 2, y: 1 }, 19) // 19  (second column, first row)
 * coordToLinear({ x: 1, y: 2 }, 19) // 1   (first column, second row)
 */
export function coordToLinear(c: Coord, sizeY: number): number {
  return (c.x - 1) * sizeY + (c.y - 1); // Besogo fromXY exact pattern
}

/**
 * Get adjacent coordinates (up, down, left, right)
 *
 * @param c - Center coordinate (1-indexed)
 * @param boardSize - Board size (default 19)
 * @returns Array of valid adjacent coordinates
 */
export function getAdjacentCoords(c: Coord, boardSize = 19): Coord[] {
  const adjacent: Coord[] = [];

  const directions = [
    { x: 0, y: -1 }, // up
    { x: 0, y: 1 }, // down
    { x: -1, y: 0 }, // left
    { x: 1, y: 0 }, // right
  ];

  for (const dir of directions) {
    const newCoord = { x: c.x + dir.x, y: c.y + dir.y };
    if (isValidCoord(newCoord, boardSize)) {
      adjacent.push(newCoord);
    }
  }

  return adjacent;
}

/**
 * Convert coordinate to unique key for Map/Set usage
 */
export function coordKey(c: Coord): string {
  return `${c.x},${c.y}`;
}

/**
 * Parse coordinate key back to coordinate
 */
export function keyToCoord(key: string): Coord {
  const parts = key.split(',').map(Number);
  const x = parts[0] ?? 1;
  const y = parts[1] ?? 1;
  return { x, y };
}
