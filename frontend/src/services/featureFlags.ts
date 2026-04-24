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

// ============================================================================
// UI Layout flags (Phase 1: chrome shrink)
//
// Build-time toggles for the puzzle-set viewer redesign. Flip to `false` to
// revert any single change without a rebuild diff. Once a flag has settled in
// production for ~2 weeks with no regressions, remove the flag and the dead
// branch (delete-don't-deprecate policy).
// ============================================================================

/**
 * Top-align the board on mobile/portrait so it sits at the top of the viewport
 * instead of being vertically centered (which created a large empty band above
 * the board on phones).
 */
export const UI_BOARD_TOP_ALIGN = true;

/**
 * Hide the StreakBadge inside AppHeader when on a puzzle-solving route.
 * The streak is already shown inside ProblemNav in the sidebar, so the
 * AppHeader copy is redundant chrome.
 */
export const UI_COMPACT_HEADER_HIDE_STREAK = true;

/**
 * Drop the "1 / 200" counter pill in PuzzleSetHeader when ProblemNav is
 * present in the sidebar (it shows the same data). Avoids duplicate counters.
 */
export const UI_HEADER_DROP_COUNTER = true;

/**
 * Drop the thin progress strip below PuzzleSetHeader. ProblemNav in the
 * sidebar already renders a richer progress bar with "Solved: X/Y (Z%)"
 * footer text, so the header strip is redundant chrome (Phase 4 — Issue 3).
 */
export const UI_HEADER_DROP_PROGRESS_BAR = true;

/**
 * Remove the QualityStars badge from the SolverView metadata row. Quality is
 * a curation signal, not a solving signal. Stars remain on browse/list pages.
 */
export const UI_HIDE_QUALITY_IN_SOLVER = true;

/**
 * Move TransformBar (flip/rotate/swap/zoom/coords) into a collapsible
 * "View options" panel at the bottom of the sidebar. Set once per puzzle,
 * does not need to be visible by default. Side effect: Hint+Comment naturally
 * moves up next to Metadata, giving the agreed "solving content first" order.
 */
export const UI_COLLAPSE_TRANSFORM_BAR = true;

// ============================================================================
// UI Layout flags (Phase 2: filters in sheet)
// ============================================================================

/**
 * Replace the inline filter strip in PuzzleSetHeader with a "Filters" trigger
 * button. The full filter UI opens in a BottomSheet (mobile slides up from
 * bottom; desktop appears as a centered popover). Active filter chips render
 * inside the sheet alongside the controls. Hides the multi-row filter chrome
 * that pushed the board out of the mobile viewport.
 */
export const UI_FILTERS_IN_SHEET = true;

// ============================================================================
// UI Layout flags (Phase 3: solver action bar + keyboard help)
// ============================================================================

/**
 * Pin the solver action bar (Prev / Undo / Reset / Hint / Solution / Next) to
 * the bottom of the viewport on mobile via fixed positioning. Adds bottom
 * padding to the sidebar column so content does not slide under the bar.
 * Desktop layout is unaffected.
 */
export const UI_PINNED_SOLVER_ACTION_BAR = true;

/**
 * Show a keyboard-shortcut help overlay when the user presses `?`. Lists the
 * existing keyboard bindings (Esc, z, x, arrows, `a`). Pure addition — does
 * not change any existing binding behavior.
 */
export const UI_KEYBOARD_HELP = true;
