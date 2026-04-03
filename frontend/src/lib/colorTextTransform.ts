/**
 * Color text transformation for color-swapped puzzles (UI-011)
 *
 * When the user toggles "Reverse colors", stone positions swap but text
 * in hints/comments still references the original color. This utility
 * transforms "Black" ↔ "White" text in multiple languages.
 *
 * Ported from OGS PuzzleTransform.transformMoveText() pattern.
 *
 * @module lib/colorTextTransform
 */

// ---------------------------------------------------------------------------
// Color word pairs (Black ↔ White) in supported languages
// ---------------------------------------------------------------------------

/**
 * Each pair is [blackWord, whiteWord]. Matching uses word boundaries
 * for Latin scripts to avoid partial matches (e.g., "vital" matching "Vit").
 * CJK characters don't need word boundaries.
 */
const COLOR_PAIRS: ReadonlyArray<[string, string, boolean]> = [
  // English (word boundary needed)
  ['Black', 'White', true],
  ['black', 'white', true],
  ['BLACK', 'WHITE', true],
  // Finnish
  ['Musta', 'Valkoinen', true],
  ['musta', 'valkoinen', true],
  // Spanish
  ['Negro', 'Blanco', true],
  ['negro', 'blanco', true],
  // French
  ['Noir', 'Blanc', true],
  ['noir', 'blanc', true],
  // German
  ['Schwarz', 'Weiß', true],
  ['schwarz', 'weiß', true],
  // Polish
  ['Czarny', 'Biały', true],
  ['czarny', 'biały', true],
  // Swedish
  ['Svart', 'Vit', true],
  ['svart', 'vit', true],
  // CJK (no word boundary needed — single characters)
  // Note: Chinese 黑 and Japanese 黒 both map to 白 for white.
  // Only include 黑 (Chinese); 黒 (Japanese) shares 白 and would interfere.
  ['黑', '白', false],
  // Russian
  ['Чёрный', 'Белый', true],
  ['чёрный', 'белый', true],
  // Korean
  ['흑', '백', false],
];

/**
 * Swap color references in text for color-swapped puzzles.
 *
 * Replaces "Black" with "White" and vice versa in multiple languages,
 * using word-boundary-aware replacement to avoid partial matches.
 *
 * @param text - Text to transform
 * @returns Text with color references swapped
 */
export function swapColorText(text: string): string {
  if (!text) return text;

  // Use a placeholder to avoid double-swapping
  // E.g., "Black plays, White responds" should become "White plays, Black responds"
  // not "White plays, White responds" (if we did sequential replace)
  let result = text;

  for (const [black, white, useWordBoundary] of COLOR_PAIRS) {
    if (useWordBoundary) {
      // Use regex with word boundaries for Latin scripts
      const blackRe = new RegExp(`\\b${escapeRegex(black)}\\b`, 'g');
      const whiteRe = new RegExp(`\\b${escapeRegex(white)}\\b`, 'g');
      const placeholder = `\x00WB_${black}\x00`;

      result = result.replace(blackRe, placeholder);
      result = result.replace(whiteRe, black);
      result = result.split(placeholder).join(white);
    } else {
      // Direct replacement for CJK characters (no word boundaries needed)
      const placeholder = `\x00CJK_${black}\x00`;
      result = result.split(black).join(placeholder);
      result = result.split(white).join(black);
      result = result.split(placeholder).join(white);
    }
  }

  return result;
}

/** Escape special regex characters in a string. */
function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
