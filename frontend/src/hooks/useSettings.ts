/**
 * useSettings — unified settings hook with shared reactive state.
 *
 * Single source of truth for all user preferences via `yengo:settings`
 * localStorage key. Uses a module-level store with subscriber pattern —
 * all consumers re-render automatically on any settings change.
 *
 * Spec 127: FR-004, FR-013, FR-019, FR-031, US3
 * T073a: Removed @preact/signals dependency.
 * @module hooks/useSettings
 */

import { useCallback, useEffect, useState } from 'preact/hooks';

// ============================================================================
// Types
// ============================================================================

/** User preferences — the only data stored in SETTINGS_KEY. */
export interface AppSettings {
  /** Color scheme. No "system" option — explicit choice only. */
  theme: 'light' | 'dark';
  /** Sound effects (stone, capture, correct/wrong feedback). */
  soundEnabled: boolean;
  /** Board coordinate labels (A-T, 1-19). Toggled on puzzle page. */
  coordinateLabels: boolean;
  /** Auto-advance to next puzzle after correct solve. */
  autoAdvance: boolean;
  /** Delay in seconds before auto-advancing (1–5). */
  autoAdvanceDelay: number;
}

/** Return type of the useSettings() hook. */
export interface UseSettingsReturn {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

// ============================================================================
// Constants
// ============================================================================

/** The canonical localStorage key for all user settings. */
export const SETTINGS_KEY = 'yengo:settings' as const;

/** Legacy keys to delete on first load (clean slate — FR-013). */
export const LEGACY_KEYS: readonly string[] = [
  'yen-go-settings',
  'yen-go:theme',
  'yen-go:audio:muted',
  'yen-go:audio:volume',
  'yengo-coordinate-labels',
  'yengo-renderer-preference',
  'yengo-user-settings',
  'yen-go:settings',
] as const;

export const DEFAULT_SETTINGS: AppSettings = {
  theme: 'light',
  soundEnabled: true,
  coordinateLabels: true,
  autoAdvance: false,
  autoAdvanceDelay: 3,
};

// ============================================================================
// Internal State (Module-Level Signal)
// ============================================================================

/** Validate that theme is exactly 'light' or 'dark'. */
function validateTheme(theme: unknown): 'light' | 'dark' {
  return theme === 'dark' ? 'dark' : 'light';
}

/** Clamp auto-advance delay to valid range (1–5 seconds). */
function validateDelay(delay: unknown): number {
  const n = typeof delay === 'number' ? delay : DEFAULT_SETTINGS.autoAdvanceDelay;
  return Math.max(1, Math.min(5, Math.round(n)));
}

/** Load and validate settings from localStorage. */
function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Record<string, unknown>;
      return {
        ...DEFAULT_SETTINGS,
        theme: validateTheme(parsed.theme),
        autoAdvanceDelay: validateDelay(parsed.autoAdvanceDelay),
        soundEnabled:
          typeof parsed.soundEnabled === 'boolean'
            ? parsed.soundEnabled
            : DEFAULT_SETTINGS.soundEnabled,
        coordinateLabels:
          typeof parsed.coordinateLabels === 'boolean'
            ? parsed.coordinateLabels
            : DEFAULT_SETTINGS.coordinateLabels,
        autoAdvance:
          typeof parsed.autoAdvance === 'boolean'
            ? parsed.autoAdvance
            : DEFAULT_SETTINGS.autoAdvance,
      };
    }
  } catch {
    // localStorage unavailable or corrupt — use defaults
  }
  return { ...DEFAULT_SETTINGS };
}

/** Save settings to localStorage. Non-fatal on failure. */
function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // Quota exceeded or private browsing — ignore
  }
}

/** Apply theme to document.documentElement via data-theme attribute. */
function applyTheme(theme: 'light' | 'dark'): void {
  try {
    document.documentElement.setAttribute('data-theme', theme);
  } catch {
    // SSR or testing — ignore
  }
}

/** Delete all legacy localStorage keys (FR-013). */
export function cleanLegacyKeys(): void {
  try {
    for (const key of LEGACY_KEYS) {
      localStorage.removeItem(key);
    }
  } catch {
    // Non-fatal
  }
}

// Module-level store — the single shared source of truth (T073a: no signals).
type Listener = () => void;
const listeners = new Set<Listener>();
let currentSettings: AppSettings | null = null;
let initialized = false;

function notifyListeners(): void {
  for (const listener of listeners) listener();
}

function getSettings(): AppSettings {
  if (!currentSettings) {
    currentSettings = loadSettings();
    applyTheme(currentSettings.theme);

    if (!initialized) {
      initialized = true;
      try {
        const hasNewKey = localStorage.getItem(SETTINGS_KEY) !== null;
        if (!hasNewKey) {
          cleanLegacyKeys();
          saveSettings(currentSettings);
        }
      } catch {
        // Non-fatal
      }
    }
  }
  return currentSettings;
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for managing app settings with shared reactive state.
 *
 * All consumers share the same module-level store and re-render
 * automatically when any setting changes. No prop drilling, no Context provider.
 *
 * @returns Current settings, updateSettings, resetSettings
 */
export function useSettings(): UseSettingsReturn {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const listener = (): void => forceUpdate((c) => c + 1);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const settings = getSettings();

  const updateSettings = useCallback((updates: Partial<AppSettings>) => {
    const next: AppSettings = {
      ...getSettings(),
      ...updates,
    };
    next.theme = validateTheme(next.theme);
    next.autoAdvanceDelay = validateDelay(next.autoAdvanceDelay);
    currentSettings = next;
    saveSettings(next);
    applyTheme(next.theme);
    notifyListeners();
  }, []);

  const resetSettings = useCallback(() => {
    currentSettings = { ...DEFAULT_SETTINGS };
    saveSettings(DEFAULT_SETTINGS);
    applyTheme(DEFAULT_SETTINGS.theme);
    notifyListeners();
  }, []);

  return {
    settings,
    updateSettings,
    resetSettings,
  };
}

/**
 * Read current settings outside of React hooks (for services, callbacks).
 * Returns a snapshot of the current AppSettings.
 */
export function getSettingsSnapshot(): AppSettings {
  return getSettings();
}

/**
 * Reset settings state for testing only.
 * @internal
 */
export function _resetSettingsForTesting(): void {
  currentSettings = null;
  initialized = false;
  listeners.clear();
}

export default useSettings;
