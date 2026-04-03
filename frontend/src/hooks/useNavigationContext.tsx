/**
 * Navigation Context Hook
 * @module hooks/useNavigationContext
 *
 * Manages focus context between board and solution tree.
 * Prevents keyboard navigation conflicts.
 *
 * Spec 122 - T1.3
 *
 * Constitution Compliance:
 * - IX. Accessibility: Proper focus management
 */

import { createContext } from 'preact';
import { useContext, useState, useCallback, useMemo } from 'preact/hooks';
import type { ComponentChildren, JSX } from 'preact';

// Focus contexts
export type FocusContext = 'board' | 'tree' | 'controls' | 'sidebar' | 'none';

// Navigation context state
export interface NavigationContextState {
  /** Current focus context */
  currentFocus: FocusContext;
  /** Set focus to a specific context */
  setFocus: (context: FocusContext) => void;
  /** Check if a context has focus */
  hasFocus: (context: FocusContext) => boolean;
  /** Clear focus (set to none) */
  clearFocus: () => void;
}

// Context with default values
const NavigationContext = createContext<NavigationContextState>({
  currentFocus: 'none',
  setFocus: () => {},
  hasFocus: () => false,
  clearFocus: () => {},
});

/**
 * Navigation context provider props
 */
export interface NavigationProviderProps {
  children: ComponentChildren;
  /** Initial focus context */
  initialFocus?: FocusContext;
}

/**
 * Navigation Context Provider
 *
 * Wraps components that need focus coordination.
 * Only one context can have focus at a time.
 */
export function NavigationProvider({
  children,
  initialFocus = 'none',
}: NavigationProviderProps): JSX.Element {
  const [currentFocus, setCurrentFocus] = useState<FocusContext>(initialFocus);

  const setFocus = useCallback((context: FocusContext) => {
    setCurrentFocus(context);
  }, []);

  const hasFocus = useCallback(
    (context: FocusContext) => currentFocus === context,
    [currentFocus]
  );

  const clearFocus = useCallback(() => {
    setCurrentFocus('none');
  }, []);

  const value = useMemo(
    () => ({ currentFocus, setFocus, hasFocus, clearFocus }),
    [currentFocus, setFocus, hasFocus, clearFocus]
  );

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
}

/**
 * Hook to access navigation context
 *
 * @returns Navigation context state
 *
 * @example
 * ```tsx
 * const { currentFocus, setFocus, hasFocus } = useNavigationContext();
 *
 * // Set focus when clicking on tree
 * const handleTreeFocus = () => setFocus('tree');
 *
 * // Check if board has focus
 * if (hasFocus('board')) {
 *   // Handle board keyboard navigation
 * }
 * ```
 */
export function useNavigationContext(): NavigationContextState {
  return useContext(NavigationContext);
}

/**
 * Hook to conditionally handle keyboard events based on focus context
 *
 * @param context - The context this hook belongs to
 * @param onKeyDown - Keyboard handler (only called when context has focus)
 * @returns Whether the handler should be active
 */
export function useContextualKeyboard(
  context: FocusContext,
  onKeyDown?: (e: KeyboardEvent) => void
): { isActive: boolean; handleKeyDown: (e: KeyboardEvent) => void } {
  const { hasFocus } = useNavigationContext();

  const isActive = hasFocus(context);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive || !onKeyDown) return;
      onKeyDown(e);
    },
    [isActive, onKeyDown]
  );

  return { isActive, handleKeyDown };
}

export { NavigationContext };
