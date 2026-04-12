/**
 * Page mode types for visual identity system.
 *
 * Each page in YenGo has a distinctive accent color. The mode drives
 * CSS cascade via `[data-mode]` attribute and `--color-accent` variable.
 *
 * Spec 132 — FR-031, FR-035
 * @module types/page-mode
 */

/** The page modes — each maps to a unique accent color */
export type PageMode =
  | 'daily'
  | 'rush'
  | 'collections'
  | 'training'
  | 'technique'
  | 'random'
  | 'learning';

/**
 * Primary accent color hex values for each page mode.
 * Used for programmatic color references (e.g., chart fills).
 * For CSS, prefer `var(--color-mode-{name}-border)` via cascade.
 */
export const PAGE_MODE_COLORS: Record<PageMode, string> = {
  daily: '#fbbf24', // Amber
  rush: '#f43f5e', // Rose
  collections: '#a855f7', // Purple
  training: '#3b82f6', // Blue
  technique: '#10b981', // Emerald
  random: '#6366f1', // Indigo
  learning: '#f59e0b', // Amber-500 (progress/learning accent)
} as const;
