/**
 * SGF Pre-processor for YenGo custom properties.
 *
 * Extracts YenGo metadata from raw SGF using a proper tree parser (NOT regex).
 * The raw SGF is also converted to a PuzzleObject via `sgfToPuzzle()` in
 * the useGoban hook before being passed to goban.
 *
 * Architecture (OGS-native format):
 *   Raw SGF → sgfToPuzzle() → PuzzleObject → goban   (board, stones, tree, puzzle mechanics)
 *   Raw SGF → parseSgfToTree() → metadata            (this module — sidebar display only)
 *
 * Validation (FR-039): Levels and tags are validated against boot-loaded config
 * via `getBootConfigs()`. Unrecognized values produce clear error messages.
 *
 * @module sgf-preprocessor
 */

import type { YenGoMetadata, PreprocessedPuzzle } from '../types/goban';
import { isValidLevel, type LevelSlug } from '@/lib/levels/config';
import { FALLBACK_LEVEL } from '@/lib/levels/level-defaults';
import { getBootConfigs } from '../boot';
import { parseSgfToTree, extractMetadataFromTree } from './sgf-metadata';

// ---------------------------------------------------------------------------
// Helpers (kept for validation; parsing moved to sgf-metadata.ts)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Boot Config Validation (FR-039)
// ---------------------------------------------------------------------------

/**
 * Validate a level slug against boot-loaded puzzle levels config.
 * Throws with clear error listing valid alternatives if unrecognized.
 */
export function validateSgfLevel(
  level: string,
  validLevels: ReadonlyArray<{ slug: string }>
): void {
  const validSlugs = validLevels.map((l) => l.slug);
  if (!validSlugs.includes(level)) {
    throw new Error(`Unrecognized level "${level}". Valid levels: ${validSlugs.join(', ')}`);
  }
}

/**
 * Validate tags against boot-loaded tags config.
 * Throws with clear error listing valid alternatives if any tag is unrecognized.
 */
export function validateSgfTags(
  tags: readonly string[],
  validTags: ReadonlyArray<{ slug: string }>
): void {
  const validIds = new Set(validTags.map((t) => t.slug));
  for (const tag of tags) {
    if (!validIds.has(tag)) {
      throw new Error(`Unrecognized tag "${tag}". Valid tags: ${[...validIds].join(', ')}`);
    }
  }
}

/**
 * Validate extracted metadata against boot-loaded config.
 * Non-fatal: logs warnings instead of throwing, since puzzles should
 * still render even if config is stale.
 *
 * @returns true if valid, false if any validation failed
 */
function validateAgainstBootConfig(metadata: YenGoMetadata): boolean {
  try {
    const bootConfigs = getBootConfigs();
    if (!bootConfigs) return true; // Boot hasn't completed — skip validation

    validateSgfLevel(metadata.level, bootConfigs.levels);
    validateSgfTags(metadata.tags, bootConfigs.tags);
    return true;
  } catch (err) {
    console.warn('[sgf-preprocessor] Validation warning:', (err as Error).message);
    return false;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Extract all YenGo custom properties from raw SGF text.
 *
 * Properties that are absent or contain empty/invalid values fall back to
 * sensible defaults so callers always receive a fully-populated
 * {@link YenGoMetadata} object.
 *
 * @param rawSgf - The original SGF string, potentially containing YenGo
 *   custom properties (`YG`, `YT`, `YH`, `YK`, `YO`).
 * @returns Fully-populated metadata with defaults for missing properties.
 *
 * @example
 * ```ts
 * const meta = extractYenGoProperties(
 *   '(;FF[4]GM[1]SZ[9]YG[intermediate]YT[ko,ladder]YH[Look at corner|Try atari])'
 * );
 * // meta.level === 'intermediate'
 * // meta.tags  === ['ko', 'ladder']
 * // meta.hints === ['Look at corner', 'Try atari']
 * ```
 */
export function extractYenGoProperties(rawSgf: string): YenGoMetadata {
  // Use proper tree parser instead of regex (Phase 0 fix)
  const rootNode = parseSgfToTree(rawSgf);
  if (!rootNode) {
    // Fallback: return defaults if SGF is unparseable
    return {
      level: FALLBACK_LEVEL,
      tags: [],
      hints: [],
      koContext: 'none',
      moveOrder: 'flexible',
      collections: [],
      collectionMemberships: [],
      firstCorrectMove: null,
      quality: 0,
      contentType: 'practice',
    };
  }

  const meta = extractMetadataFromTree(rootNode);

  // Validate level against generated types
  const level: LevelSlug = isValidLevel(meta.level) ? meta.level : FALLBACK_LEVEL;

  return {
    level,
    tags: meta.tags,
    hints: meta.hints,
    koContext: meta.koContext as YenGoMetadata['koContext'],
    moveOrder: meta.moveOrder as YenGoMetadata['moveOrder'],
    collections: meta.collections,
    collectionMemberships: meta.collectionMemberships,
    firstCorrectMove: meta.firstCorrectMove,
    quality: meta.quality,
    contentType: meta.contentType,
  };
}

/**
 * Pre-process raw SGF text for use with the goban library.
 *
 * Extracts YenGo metadata via tree parser. The SGF is returned UNCHANGED
 * as `cleanedSgf` — goban ignores unknown properties per SGF FF[4] spec.
 * No regex stripping needed.
 *
 * @param rawSgf - The original SGF string.
 * @returns Pre-processed result with metadata and original SGF.
 *
 * @example
 * ```ts
 * const result = preprocessSgf(rawSgfText);
 * // result.cleanedSgf === rawSgfText  (no stripping!)
 * // result.metadata.level === 'intermediate'
 * ```
 */
export function preprocessSgf(rawSgf: string): PreprocessedPuzzle {
  const metadata = extractYenGoProperties(rawSgf);

  // FR-039: Validate against boot-loaded config (non-fatal — logs warnings)
  validateAgainstBootConfig(metadata);

  return {
    // Pass raw SGF unchanged — goban ignores unknown properties per SGF FF[4] spec
    cleanedSgf: rawSgf,
    metadata,
    originalSgf: rawSgf,
  };
}

// ---------------------------------------------------------------------------
// Transform Settings (US2) - Re-export from types for convenience
// ---------------------------------------------------------------------------

// Import TransformSettings from types/goban.ts
import type { TransformSettings as ImportedTransformSettings } from '../types/goban';

// Re-export for convenience
export type TransformSettings = ImportedTransformSettings;

/**
 * Default transform settings (all disabled).
 */
export const DEFAULT_TRANSFORM_SETTINGS: TransformSettings = {
  flipH: false,
  flipV: false,
  flipDiag: false,
  rotation: 0,
  swapColors: false,
};

// ---------------------------------------------------------------------------
// Coordinate Transform Functions (T055)
// ---------------------------------------------------------------------------

/**
 * Transform a numeric board coordinate (0-18) according to transform settings.
 *
 * Rotation is applied first, then mirror flips. This order ensures that
 * flips are always relative to the board axes, not the rotated axes.
 *
 * @param x - X coordinate (0-based)
 * @param y - Y coordinate (0-based)
 * @param boardSize - Board dimension (default 19)
 * @param settings - Transform settings to apply
 * @returns Transformed [x, y] coordinates
 */
export function transformCoordinate(
  x: number,
  y: number,
  boardSize: number,
  settings: TransformSettings
): [number, number] {
  let tx = x;
  let ty = y;
  const max = boardSize - 1;

  // Apply rotation first (clockwise)
  switch (settings.rotation) {
    case 90:
      [tx, ty] = [max - ty, tx];
      break;
    case 180:
      [tx, ty] = [max - tx, max - ty];
      break;
    case 270:
      [tx, ty] = [ty, max - tx];
      break;
    // case 0: no-op
  }

  // Apply diagonal flip (matrix transposition: swap x,y)
  if (settings.flipDiag) {
    [tx, ty] = [ty, tx];
  }

  // Apply horizontal flip (mirror left-right)
  if (settings.flipH) {
    tx = max - tx;
  }

  // Apply vertical flip (mirror top-bottom)
  if (settings.flipV) {
    ty = max - ty;
  }

  return [tx, ty];
}

/**
 * Transform an SGF coordinate string (e.g., "dd") according to transform settings.
 *
 * SGF coordinates use 'a'-'s' for 1-19, where 'a' = 0.
 *
 * @param coord - SGF coordinate string (2 characters, e.g., "dd")
 * @param boardSize - Board dimension (default 19)
 * @param settings - Transform settings to apply
 * @returns Transformed SGF coordinate string
 */
export function transformSgfCoordinate(
  coord: string,
  boardSize: number,
  settings: TransformSettings
): string {
  if (coord.length !== 2) {
    return coord; // Invalid coordinate, return unchanged
  }

  const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
  const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);

  // Validate coordinates
  if (x < 0 || x >= boardSize || y < 0 || y >= boardSize) {
    return coord; // Out of bounds, return unchanged
  }

  const [tx, ty] = transformCoordinate(x, y, boardSize, settings);

  return String.fromCharCode('a'.charCodeAt(0) + tx) + String.fromCharCode('a'.charCodeAt(0) + ty);
}

/**
 * Apply color transformation to SGF content.
 *
 * Swaps B[] ↔ W[] moves and AB[] ↔ AW[] setup stones.
 * Also swaps PL[] player-to-move property.
 *
 * Uses negative lookbehind to prevent B[] swap from matching inside AB[],
 * and swaps AB/AW separately to avoid double-swap.
 *
 * @param sgf - SGF content
 * @param swapColors - Whether to apply color swap
 * @returns SGF with colors swapped if enabled
 */
export function applyColorTransform(sgf: string, swapColors: boolean): string {
  if (!swapColors) {
    return sgf;
  }

  // Use placeholders to avoid double-swap within each group.
  // Placeholders use strings that cannot appear in valid SGF content.

  // --- 1. Swap setup properties: AB ↔ AW ---
  // Must be done FIRST so that B/W swap below doesn't collide with AB/AW.
  const PLACEHOLDER_AB = '@@YENGO_ADD_BLACK@@';
  let result = sgf;
  result = result.replace(/AB\[/g, PLACEHOLDER_AB);
  result = result.replace(/AW\[/g, 'AB[');
  result = result.split(PLACEHOLDER_AB).join('AW[');

  // --- 2. Swap move properties: B ↔ W ---
  // Use negative lookbehind (?<!A) to skip AB[ and AW[ (already swapped above).
  const PLACEHOLDER_B = '@@YENGO_BLACK@@';
  result = result.replace(/(?<!A)B\[/g, PLACEHOLDER_B);
  result = result.replace(/(?<!A)W\[/g, 'B[');
  result = result.split(PLACEHOLDER_B).join('W[');

  // --- 3. Swap player-to-move: PL[B] ↔ PL[W] ---
  const PLACEHOLDER_PL_B = '@@YENGO_PL_BLACK@@';
  result = result.replace(/PL\[B\]/g, PLACEHOLDER_PL_B);
  result = result.replace(/PL\[W\]/g, 'PL[B]');
  result = result.split(PLACEHOLDER_PL_B).join('PL[W]');

  return result;
}

/**
 * Apply coordinate transforms to all move and position coordinates in SGF.
 *
 * Transforms: B[], W[], AB[], AW[], AE[], TR[], SQ[], CR[], MA[], LB[], etc.
 *
 * Handles SGF multi-value properties correctly:
 *   AB[aa][bb][cc] — all three coordinates are transformed
 *   B[dd]          — single-value move properties also transformed
 *
 * @param sgf - SGF content
 * @param boardSize - Board dimension
 * @param settings - Transform settings
 * @returns SGF with transformed coordinates
 */
function transformAllCoordinates(
  sgf: string,
  boardSize: number,
  settings: TransformSettings
): string {
  // If no coordinate transforms are active, return unchanged
  if (!settings.flipH && !settings.flipV && !settings.flipDiag && settings.rotation === 0) {
    return sgf;
  }

  // Multi-value properties (AB, AW, AE, TR, SQ, CR, MA, TB, TW) can have
  // multiple bracketed values: AB[aa][bb][cc]. We match the property name
  // followed by ALL consecutive bracket groups.
  const multiValueRe = /(AB|AW|AE|TR|SQ|CR|MA|TB|TW)((?:\[[a-s]{2}\])+)/g;

  let result = sgf.replace(multiValueRe, (_match, prop: string, values: string) => {
    // values is like "[aa][bb][cc]" — transform each coordinate
    const transformed = values.replace(/\[([a-s]{2})\]/g, (_m: string, coord: string) => {
      return `[${transformSgfCoordinate(coord, boardSize, settings)}]`;
    });
    return `${prop}${transformed}`;
  });

  // Single-value move properties (B, W) — always exactly one value.
  // Negative lookbehind (?<!A) ensures we don't re-match B[ inside AB[ or W[ inside AW[.
  const singleValueRe = /(?<!A)(B|W)\[([a-s]{2})\]/g;
  result = result.replace(singleValueRe, (_match, prop: string, coord: string) => {
    const transformed = transformSgfCoordinate(coord, boardSize, settings);
    return `${prop}[${transformed}]`;
  });

  // Handle LB (label) property: LB[coord:text]
  const labelRe = /LB\[([a-s]{2}):([^\]]*)\]/g;
  result = result.replace(labelRe, (_match, coord: string, text: string) => {
    const transformed = transformSgfCoordinate(coord, boardSize, settings);
    return `LB[${transformed}:${text}]`;
  });

  return result;
}

/**
 * Transform entire puzzle SGF according to transform settings.
 *
 * Applies coordinate transformations (flip H/V/diagonal) and color swaps
 * to all moves and positions in the SGF.
 *
 * @param sgf - Original SGF content
 * @param settings - Transform settings to apply
 * @param boardSize - Board dimension (default 19, auto-detected from SZ property)
 * @returns Transformed SGF
 */
export function transformPuzzleSgf(
  sgf: string,
  settings: TransformSettings,
  boardSize?: number
): string {
  // Auto-detect board size from SZ property if not provided
  let size = boardSize;
  if (size === undefined) {
    const szMatch = /SZ\[(\d+)\]/.exec(sgf);
    size = szMatch?.[1] !== undefined ? parseInt(szMatch[1], 10) : 19;
  }

  let result = sgf;

  // Apply coordinate transforms
  result = transformAllCoordinates(result, size, settings);

  // Apply color transform
  result = applyColorTransform(result, settings.swapColors);

  return result;
}

// ---------------------------------------------------------------------------
// Auto-Zoom Bounds Computation (T056)
// ---------------------------------------------------------------------------

/**
 * Bounds for partial board display (auto-zoom).
 * Coordinates are 0-indexed. `right` and `bottom` are inclusive.
 */
export interface GobanBounds {
  top: number;
  left: number;
  bottom: number;
  right: number;
}

/**
 * Extract setup stone positions from the SGF root node only.
 *
 * Only extracts AB[] (add black) and AW[] (add white) setup properties
 * from the root node of the SGF. Ignores B[] and W[] solution tree moves
 * to avoid the bounding box expanding to cover the entire solution tree,
 * which would defeat the purpose of auto-zoom on corner tsumego.
 *
 * Handles SGF multi-value format: AB[aa][bb][cc] extracts all three.
 *
 * @param sgf - SGF content
 * @returns Array of [x, y] coordinates from setup stones
 */
function extractSetupPositions(sgf: string): Array<[number, number]> {
  const positions: Array<[number, number]> = [];

  // Extract the root node: from the first '(;' to the next ';' or '('
  // which marks the start of a child node / variation.
  // Must be bracket-depth-aware to skip ';' inside property values.
  const rootStart = sgf.indexOf('(;');
  if (rootStart === -1) return positions;

  let rootEnd = sgf.length;
  let depth = 0;
  for (let i = rootStart + 2; i < sgf.length; i++) {
    const ch = sgf[i];
    if (ch === '\\') {
      i++;
      continue;
    } // skip escaped char
    if (ch === '[') {
      depth++;
      continue;
    }
    if (ch === ']') {
      depth = Math.max(0, depth - 1);
      continue;
    }
    if (depth === 0 && (ch === ';' || ch === '(')) {
      rootEnd = i;
      break;
    }
  }
  const rootNode = sgf.substring(rootStart, rootEnd);

  // Match AB or AW followed by one or more [xy] groups (multi-value SGF format).
  // Example: AB[bb][db][eb] matches the whole sequence.
  const setupGroupRe = /(?:AB|AW)((?:\[[a-s]{2}\])+)/g;
  let groupMatch;

  while ((groupMatch = setupGroupRe.exec(rootNode)) !== null) {
    const brackets = groupMatch[1];
    if (!brackets) continue;
    // Extract each individual coordinate from the bracket group
    const coordRe = /\[([a-s]{2})\]/g;
    let coordMatch;
    while ((coordMatch = coordRe.exec(brackets)) !== null) {
      const coord = coordMatch[1];
      if (coord !== undefined) {
        const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
        const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);
        positions.push([x, y]);
      }
    }
  }

  // If no setup stones found, fall back to all positions (some puzzles
  // might not use AB/AW)
  if (positions.length === 0) {
    return extractAllPositions(sgf);
  }

  return positions;
}

/**
 * Extract all stone positions from SGF setup and moves.
 * Handles multi-value format: AB[aa][bb][cc].
 *
 * @param sgf - SGF content
 * @returns Array of [x, y] coordinates
 */
function extractAllPositions(sgf: string): Array<[number, number]> {
  const positions: Array<[number, number]> = [];

  // Multi-value properties: AB[aa][bb], AW[aa][bb], AE[aa][bb], etc.
  const multiValueRe = /(?:AB|AW|AE|TR|SQ|CR|MA)((?:\[[a-s]{2}\])+)/g;
  let groupMatch;
  while ((groupMatch = multiValueRe.exec(sgf)) !== null) {
    const brackets = groupMatch[1];
    if (!brackets) continue;
    const coordRe = /\[([a-s]{2})\]/g;
    let coordMatch;
    while ((coordMatch = coordRe.exec(brackets)) !== null) {
      const coord = coordMatch[1];
      if (coord !== undefined) {
        const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
        const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);
        positions.push([x, y]);
      }
    }
  }

  // Single-value move properties: B[aa], W[bb]
  const moveRe = /(?<!A)(B|W)\[([a-s]{2})\]/g;
  let moveMatch;
  while ((moveMatch = moveRe.exec(sgf)) !== null) {
    const coord = moveMatch[2];
    if (coord !== undefined) {
      const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
      const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);
      positions.push([x, y]);
    }
  }

  return positions;
}

/**
 * Compute optimal bounds for auto-zoom display.
 *
 * Analyzes stone positions in the SGF and computes a bounding box that
 * includes all stones plus a configurable padding margin.
 *
 * Edge-snapping: When a bound edge is within `snapThreshold` rows/cols of
 * the real board edge, it snaps to that edge. This ensures coordinate labels
 * are anchored to a real board edge (making at least 2 axes visible).
 *
 * @param sgf - SGF content
 * @param boardSize - Board dimension (default 19)
 * @param padding - Number of empty intersections to add around stones (default 2)
 * @returns Computed bounds, or null if zoom is not beneficial
 */
export function computeBounds(
  sgf: string,
  boardSize: number = 19,
  padding: number = 2
): GobanBounds | null {
  const positions = extractSetupPositions(sgf);

  if (positions.length === 0) {
    return null; // No positions found, can't compute bounds
  }

  // Find bounding box of all positions
  let minX = boardSize;
  let maxX = 0;
  let minY = boardSize;
  let maxY = 0;

  for (const [x, y] of positions) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }

  // Add padding
  let left = Math.max(0, minX - padding);
  let right = Math.min(boardSize - 1, maxX + padding);
  let top = Math.max(0, minY - padding);
  let bottom = Math.min(boardSize - 1, maxY + padding);

  // Edge-snap: if a bound is within snapThreshold of the board edge,
  // extend it to the edge. This ensures coordinate labels are anchored
  // to a real board edge, keeping at least 2 axes of labels visible.
  const snapThreshold = 3;
  if (left <= snapThreshold) left = 0;
  if (top <= snapThreshold) top = 0;
  if (right >= boardSize - 1 - snapThreshold) right = boardSize - 1;
  if (bottom >= boardSize - 1 - snapThreshold) bottom = boardSize - 1;

  // Calculate zoomed area size
  const zoomWidth = right - left + 1;
  const zoomHeight = bottom - top + 1;

  // Don't zoom if the area is too large (> 75% of board in both dimensions)
  const threshold = boardSize * 0.75;
  if (zoomWidth >= threshold && zoomHeight >= threshold) {
    return null; // Zoom not beneficial
  }

  // Minimum zoom size: at least 5x5 to be useful
  if (zoomWidth < 5 || zoomHeight < 5) {
    // Expand to minimum 5x5
    const centerX = (left + right) / 2;
    const centerY = (top + bottom) / 2;
    const halfMin = 2;

    return {
      left: Math.max(0, Math.floor(centerX - halfMin)),
      right: Math.min(boardSize - 1, Math.ceil(centerX + halfMin)),
      top: Math.max(0, Math.floor(centerY - halfMin)),
      bottom: Math.min(boardSize - 1, Math.ceil(centerY + halfMin)),
    };
  }

  return { top, left, bottom, right };
}
