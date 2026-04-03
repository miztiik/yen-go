/**
 * Feature Flags - Besogo Extensions
 * @module services/featureFlags
 *
 * Controls toggleable features. When ENABLE_BESOGO_EXTENSIONS is false,
 * all analysis functions return safe defaults and no performance cost is incurred.
 */

/**
 * Master toggle for all Besogo Extensions (board analysis features).
 * When false: hover shows ghost on all empty positions, no self-atari warnings.
 * When true: hover blocks illegal moves, self-atari markers shown.
 */
export const ENABLE_BESOGO_EXTENSIONS = true;

/**
 * Show self-atari warning overlay on hover.
 * Recommended: true for novice/beginner, false for intermediate+.
 */
export const SHOW_SELF_ATARI_WARNING = true;

/**
 * Difficulty levels at or above which self-atari warnings are hidden.
 * Levels below this threshold show the warning by default.
 */
export const SELF_ATARI_WARNING_HIDDEN_ABOVE = 'intermediate';
