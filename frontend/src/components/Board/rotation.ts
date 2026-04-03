/**
 * Board Rotation Transforms
 * @module components/Board/rotation
 *
 * Provides coordinate transformation for board rotation (0°, 90°, 180°, 270°).
 * Used to display puzzles from different viewing angles.
 *
 * Constitution Compliance:
 * - V. No Browser AI: Pure mathematical transform only
 * - VII. Deterministic: Same input always produces same output
 */

import type { Position } from '@/types/puzzle-internal';

// ============================================================================
// Types
// ============================================================================

/**
 * Valid board rotation angles in degrees.
 */
export type BoardRotation = 0 | 90 | 180 | 270;

/**
 * All valid rotation values for iteration.
 */
export const ROTATION_VALUES: readonly BoardRotation[] = [0, 90, 180, 270] as const;

// ============================================================================
// Coordinate Rotation
// ============================================================================

/**
 * Rotate a coordinate pair by the specified degrees on a square board.
 *
 * The coordinate system assumes:
 * - (0, 0) is top-left corner
 * - x increases to the right
 * - y increases downward
 *
 * Rotation is clockwise:
 * - 90°: right edge becomes top
 * - 180°: board is upside down
 * - 270°: left edge becomes top
 *
 * @param x - X coordinate (column), 0-indexed from left
 * @param y - Y coordinate (row), 0-indexed from top
 * @param size - Board size (e.g., 9, 13, 19)
 * @param degrees - Rotation angle (0, 90, 180, 270)
 * @returns Transformed [x, y] coordinates
 *
 * @example
 * // On a 9x9 board, rotate (0, 0) by 90° → (8, 0)
 * rotateCoordinate(0, 0, 9, 90);  // returns [8, 0]
 */
export function rotateCoordinate(
  x: number,
  y: number,
  size: number,
  degrees: BoardRotation
): [number, number] {
  const max = size - 1;

  switch (degrees) {
    case 90:
      // Clockwise 90°: (x, y) → (max - y, x)
      return [max - y, x];
    case 180:
      // 180°: (x, y) → (max - x, max - y)
      return [max - x, max - y];
    case 270:
      // Clockwise 270° (or counter-clockwise 90°): (x, y) → (y, max - x)
      return [y, max - x];
    case 0:
    default:
      // No rotation
      return [x, y];
  }
}

/**
 * Rotate a Position object by the specified degrees.
 *
 * @param position - Position with x, y coordinates
 * @param size - Board size (e.g., 9, 13, 19)
 * @param degrees - Rotation angle (0, 90, 180, 270)
 * @returns New Position with transformed coordinates
 *
 * @example
 * rotatePosition({ x: 0, y: 0 }, 9, 90);  // returns { x: 8, y: 0 }
 */
export function rotatePosition(
  position: Position,
  size: number,
  degrees: BoardRotation
): Position {
  const [x, y] = rotateCoordinate(position.x, position.y, size, degrees);
  return { x, y };
}

/**
 * Rotate multiple positions at once.
 *
 * @param positions - Array of positions to rotate
 * @param size - Board size
 * @param degrees - Rotation angle
 * @returns Array of rotated positions
 */
export function rotatePositions(
  positions: readonly Position[],
  size: number,
  degrees: BoardRotation
): Position[] {
  return positions.map((pos) => rotatePosition(pos, size, degrees));
}

// ============================================================================
// Inverse Rotation (for click handling)
// ============================================================================

/**
 * Get the inverse rotation angle.
 *
 * When the board is rotated, click coordinates need to be transformed
 * back to the original coordinate system. This returns the angle needed
 * to undo a rotation.
 *
 * @param degrees - Current rotation angle
 * @returns Angle to apply for inverse transformation
 *
 * @example
 * // If board is rotated 90°, clicks need to be rotated 270° (back)
 * getInverseRotation(90);  // returns 270
 */
export function getInverseRotation(degrees: BoardRotation): BoardRotation {
  switch (degrees) {
    case 90:
      return 270;
    case 270:
      return 90;
    case 180:
    case 0:
    default:
      return degrees; // 0 and 180 are their own inverses
  }
}

/**
 * Transform a clicked position back to original board coordinates.
 *
 * When the board is displayed rotated, user clicks are in rotated space.
 * This function converts back to the original coordinate system used
 * by the puzzle data.
 *
 * @param position - Position clicked in rotated view
 * @param size - Board size
 * @param rotation - Current board rotation
 * @returns Position in original (unrotated) coordinate system
 */
export function inverseRotatePosition(
  position: Position,
  size: number,
  rotation: BoardRotation
): Position {
  return rotatePosition(position, size, getInverseRotation(rotation));
}

/**
 * Transform a clicked coordinate back to original board coordinates.
 *
 * @param x - X coordinate in rotated view
 * @param y - Y coordinate in rotated view
 * @param size - Board size
 * @param rotation - Current board rotation
 * @returns [x, y] in original (unrotated) coordinate system
 */
export function inverseRotateCoordinate(
  x: number,
  y: number,
  size: number,
  rotation: BoardRotation
): [number, number] {
  return rotateCoordinate(x, y, size, getInverseRotation(rotation));
}

// ============================================================================
// Rotation Cycle
// ============================================================================

/**
 * Get the next rotation value in the cycle.
 * Cycles: 0 → 90 → 180 → 270 → 0
 *
 * @param current - Current rotation
 * @returns Next rotation in cycle
 */
export function getNextRotation(current: BoardRotation): BoardRotation {
  const index = ROTATION_VALUES.indexOf(current);
  return ROTATION_VALUES[(index + 1) % ROTATION_VALUES.length] as BoardRotation;
}

/**
 * Get the previous rotation value in the cycle.
 * Cycles: 0 → 270 → 180 → 90 → 0
 *
 * @param current - Current rotation
 * @returns Previous rotation in cycle
 */
export function getPreviousRotation(current: BoardRotation): BoardRotation {
  const index = ROTATION_VALUES.indexOf(current);
  return ROTATION_VALUES[(index + 3) % ROTATION_VALUES.length] as BoardRotation;
}

// ============================================================================
// Validation
// ============================================================================

/**
 * Check if a value is a valid BoardRotation.
 *
 * @param value - Value to check
 * @returns True if value is 0, 90, 180, or 270
 */
export function isValidRotation(value: unknown): value is BoardRotation {
  return value === 0 || value === 90 || value === 180 || value === 270;
}

/**
 * Parse a rotation value, returning 0 if invalid.
 *
 * @param value - Value to parse
 * @returns Valid rotation or 0
 */
export function parseRotation(value: unknown): BoardRotation {
  if (typeof value === 'number' && isValidRotation(value)) {
    return value;
  }
  return 0;
}

// ============================================================================
// Display Labels
// ============================================================================

/**
 * Get a human-readable label for a rotation value.
 *
 * @param degrees - Rotation angle
 * @returns Label like "Normal", "90°", "180°", "270°"
 */
export function getRotationLabel(degrees: BoardRotation): string {
  switch (degrees) {
    case 0:
      return 'Normal';
    case 90:
      return '90°';
    case 180:
      return '180°';
    case 270:
      return '270°';
  }
}

/**
 * Get ARIA label for rotation button.
 *
 * @param current - Current rotation
 * @param next - Next rotation after clicking
 * @returns Accessible description of what the button does
 */
export function getRotationAriaLabel(current: BoardRotation, next: BoardRotation): string {
  return `Rotate board from ${getRotationLabel(current)} to ${getRotationLabel(next)}`;
}
