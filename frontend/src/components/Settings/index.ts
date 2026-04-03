/**
 * Settings components exports.
 *
 * @deprecated Use `useSettings()` from `@/hooks/useSettings` for settings access.
 * Use `SettingsPanel` from `@/components/Layout/SettingsPanel` for the settings UI.
 * This module is kept for backwards compatibility during migration (T044).
 *
 * Browse-oriented types (GameMode, DifficultyFilter) are re-exported for use
 * as contextual filter controls on collection/browse pages (T042).
 *
 * @module components/Settings
 */

export { HintToggle, type HintToggleProps } from './HintToggle';
export {
  DIFFICULTY_PRESETS,
  type GameMode,
  type DifficultyFilter,
  type BoardRotation,
} from './SettingsPanel';
