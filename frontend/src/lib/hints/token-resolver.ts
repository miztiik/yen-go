/**
 * Token resolver for transform-aware hint coordinates.
 *
 * The backend embeds `{!xy}` tokens (SGF coordinates) in hint text
 * instead of human-readable coordinates like "C5". This module resolves
 * those tokens to human-readable notation after applying the active
 * board transforms, so hints remain correct regardless of flip/rotation.
 *
 * Token format: `{!<col><row>}` where col/row are SGF-style lowercase
 * letters (a=0, b=1, ..., s=18). Example: `{!bb}` = Point(1, 1).
 *
 * @module lib/hints/token-resolver
 */

import { transformSgfCoordinate, type TransformSettings } from '../sgf-preprocessor';
import { positionToHumanCoord } from './sgf-mapper';
import { sgfToPosition } from '../../utils/coordinates';

/** Regex to match {!xy} tokens where x,y are SGF coordinate chars (a-s). */
const TOKEN_RE = /\{!([a-s]{2})\}/g;

/**
 * Resolve all `{!xy}` coordinate tokens in hint text.
 *
 * For each token:
 * 1. Parse the SGF coordinate pair
 * 2. Apply board transforms (flip H/V/diagonal)
 * 3. Convert to human-readable Go notation (e.g., "D16")
 * 4. Replace the token in the text
 *
 * Text without tokens passes through unchanged.
 *
 * @param text - Hint text potentially containing `{!xy}` tokens
 * @param boardSize - Board size for coordinate calculation (default 19)
 * @param transforms - Active transform settings
 * @returns Text with all tokens replaced by human-readable coordinates
 */
export function resolveHintTokens(
  text: string,
  boardSize: number,
  transforms: TransformSettings
): string {
  return text.replace(TOKEN_RE, (_match: string, coord: string) => {
    // Apply transforms to the SGF coordinate
    const transformed = transformSgfCoordinate(coord, boardSize, transforms);

    // Convert to {x, y} position
    const pos = sgfToPosition(transformed);
    if (!pos) return coord; // fallback: return raw coord if parse fails

    // Convert to human-readable (e.g., "D16")
    return positionToHumanCoord(pos, boardSize);
  });
}

/**
 * Check if text contains any `{!xy}` tokens.
 *
 * @param text - Text to check
 * @returns true if text contains at least one token
 */
export function hasTokens(text: string): boolean {
  // Use a fresh non-global regex to avoid lastIndex issues
  return /\{![a-s]{2}\}/.test(text);
}
