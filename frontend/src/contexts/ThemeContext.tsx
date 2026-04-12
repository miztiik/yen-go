/**
 * ThemeContext - Global theme state management.
 * @module contexts/ThemeContext
 *
 * Covers: T8.8 - Create ThemeProvider context
 *
 * Constitution Compliance:
 * - II. Local-First: Theme preference stored in localStorage
 * - IX. Accessibility: Respects prefers-color-scheme media query
 */

import { createContext } from 'preact';
import type { JSX } from 'preact';
import { useContext, useState, useEffect, useCallback } from 'preact/hooks';
import type { ComponentChildren } from 'preact';

// ============================================================================
// Types
// ============================================================================

/**
 * Available theme modes
 */
export type ThemeMode = 'light' | 'dark' | 'system';

/**
 * Resolved theme (what's actually applied)
 */
export type ResolvedTheme = 'light' | 'dark';

/**
 * Theme context value
 */
export interface ThemeContextValue {
  /** User's selected theme mode (including 'system') */
  mode: ThemeMode;
  /** Resolved theme (what's actually rendered) */
  theme: ResolvedTheme;
  /** Set the theme mode */
  setMode: (mode: ThemeMode) => void;
  /** Toggle between light and dark */
  toggleTheme: () => void;
  /** Whether using system preference */
  isSystem: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'yen-go:theme';
const DEFAULT_MODE: ThemeMode = 'system';
const DARK_CLASS = 'dark-theme';

// ============================================================================
// Context
// ============================================================================

const ThemeContext = createContext<ThemeContextValue | null>(null);

// ============================================================================
// Helpers
// ============================================================================

/**
 * Get the system's preferred color scheme
 */
function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Resolve the theme mode to a concrete theme
 */
function resolveTheme(mode: ThemeMode): ResolvedTheme {
  if (mode === 'system') return getSystemTheme();
  return mode;
}

/**
 * Load saved theme mode from localStorage
 */
function loadSavedMode(): ThemeMode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark' || saved === 'system') {
      return saved;
    }
  } catch {
    console.warn('[ThemeContext] Failed to load theme preference');
  }
  return DEFAULT_MODE;
}

/**
 * Save theme mode to localStorage
 */
function saveMode(mode: ThemeMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    console.warn('[ThemeContext] Failed to save theme preference');
  }
}

/**
 * Apply theme to document
 */
function applyTheme(theme: ResolvedTheme): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add(DARK_CLASS);
  } else {
    root.classList.remove(DARK_CLASS);
  }

  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute('content', theme === 'dark' ? '#1a1a2e' : '#f5f0e8');
  }
}

// ============================================================================
// Provider Component
// ============================================================================

export interface ThemeProviderProps {
  /** Optional initial theme mode (overrides localStorage) */
  initialMode?: ThemeMode;
  /** Child components */
  children: ComponentChildren;
}

/**
 * ThemeProvider component.
 * Manages theme state and applies CSS class to document root.
 */
export function ThemeProvider({ initialMode, children }: ThemeProviderProps): JSX.Element {
  // Initialize from localStorage or prop
  const [mode, setModeState] = useState<ThemeMode>(() => {
    if (initialMode !== undefined) return initialMode;
    return loadSavedMode();
  });

  const [theme, setTheme] = useState<ResolvedTheme>(() => resolveTheme(mode));

  // Sync theme when mode changes
  useEffect(() => {
    const resolved = resolveTheme(mode);
    setTheme(resolved);
    applyTheme(resolved);
    saveMode(mode);
  }, [mode]);

  // Listen for system theme changes when in 'system' mode
  useEffect(() => {
    if (mode !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      const newTheme: ResolvedTheme = e.matches ? 'dark' : 'light';
      setTheme(newTheme);
      applyTheme(newTheme);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [mode]);

  // Apply theme on mount
  useEffect(() => {
    applyTheme(theme);
  }, []);

  // Set mode with persistence
  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
  }, []);

  // Toggle between light and dark (bypasses system)
  const toggleTheme = useCallback(() => {
    setModeState((current) => {
      const resolved = resolveTheme(current);
      return resolved === 'light' ? 'dark' : 'light';
    });
  }, []);

  const value: ThemeContextValue = {
    mode,
    theme,
    setMode,
    toggleTheme,
    isSystem: mode === 'system',
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook to access theme context.
 * Must be used within a ThemeProvider.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

/**
 * Hook to get just the current resolved theme.
 * Throws if used outside ThemeProvider.
 */
export function useResolvedTheme(): ResolvedTheme {
  return useTheme().theme;
}

/**
 * Hook to check if dark mode is active.
 */
export function useIsDarkMode(): boolean {
  return useTheme().theme === 'dark';
}

export default ThemeProvider;
