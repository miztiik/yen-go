/**
 * Shared accent palette utility for page-specific CSS variable tokens.
 * @module lib/accent-palette
 *
 * Each page mode uses the same 4-key structure with mode-specific
 * CSS variable fallbacks (e.g., --color-mode-training-text).
 *
 * PURSIG Finding 12: DRY — previously duplicated across 3 page modules.
 */

// ============================================================================
// Types
// ============================================================================

/** Page modes that define accent color palettes. */
export type PageMode = 'training' | 'technique' | 'random' | 'collection' | 'daily' | 'learning';

/** A 4-key accent palette for page theming. */
export interface AccentPalette {
  readonly text: string;
  readonly light: string;
  readonly bg: string;
  readonly border: string;
}

// ============================================================================
// Factory
// ============================================================================

/**
 * Build an accent palette for the given page mode.
 * Uses CSS variable cascade: `--color-accent` → `--color-mode-{mode}-{key}`.
 */
export function getAccentPalette(mode: PageMode): AccentPalette {
  return {
    text: `var(--color-accent, var(--color-mode-${mode}-text))`,
    light: `var(--color-accent-light, var(--color-mode-${mode}-light))`,
    bg: `var(--color-accent-bg, var(--color-mode-${mode}-bg))`,
    border: `var(--color-accent-border, var(--color-mode-${mode}-border))`,
  };
}
