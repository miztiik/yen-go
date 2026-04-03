/**
 * useNavigationContext Hook Tests
 * @module tests/unit/hooks/use-navigation-context.test
 *
 * Unit tests for the navigation context hook that manages focus between board and tree.
 * Spec 122 - T6.2
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { h } from 'preact';
import {
  useNavigationContext,
  useContextualKeyboard,
  NavigationProvider,
  type FocusContext,
} from '../../../src/hooks/useNavigationContext';

// Wrapper component for providing context
const createWrapper = (initialFocus: FocusContext = 'none') => {
  return function Wrapper({ children }: { children: preact.ComponentChildren }) {
    return h(NavigationProvider, { initialFocus }, children);
  };
};

describe('useNavigationContext', () => {
  describe('initial state', () => {
    it('should default to "none" focus', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      expect(result.current.currentFocus).toBe('none');
    });

    it('should respect initialFocus prop', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper('board'),
      });

      expect(result.current.currentFocus).toBe('board');
    });
  });

  describe('setFocus', () => {
    it('should update currentFocus to board', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFocus('board');
      });

      expect(result.current.currentFocus).toBe('board');
    });

    it('should update currentFocus to tree', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFocus('tree');
      });

      expect(result.current.currentFocus).toBe('tree');
    });

    it('should update currentFocus to controls', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFocus('controls');
      });

      expect(result.current.currentFocus).toBe('controls');
    });

    it('should update currentFocus to sidebar', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFocus('sidebar');
      });

      expect(result.current.currentFocus).toBe('sidebar');
    });
  });

  describe('hasFocus', () => {
    it('should return true when context has focus', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper('board'),
      });

      expect(result.current.hasFocus('board')).toBe(true);
      expect(result.current.hasFocus('tree')).toBe(false);
    });

    it('should update when focus changes', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper(),
      });

      expect(result.current.hasFocus('tree')).toBe(false);

      act(() => {
        result.current.setFocus('tree');
      });

      expect(result.current.hasFocus('tree')).toBe(true);
      expect(result.current.hasFocus('board')).toBe(false);
    });
  });

  describe('clearFocus', () => {
    it('should set focus to none', () => {
      const { result } = renderHook(() => useNavigationContext(), {
        wrapper: createWrapper('board'),
      });

      expect(result.current.currentFocus).toBe('board');

      act(() => {
        result.current.clearFocus();
      });

      expect(result.current.currentFocus).toBe('none');
    });
  });
});

describe('useContextualKeyboard', () => {
  it('should be inactive when context does not have focus', () => {
    const { result } = renderHook(
      () => useContextualKeyboard('board', () => {}),
      { wrapper: createWrapper('tree') }
    );

    expect(result.current.isActive).toBe(false);
  });

  it('should be active when context has focus', () => {
    const { result } = renderHook(
      () => useContextualKeyboard('board', () => {}),
      { wrapper: createWrapper('board') }
    );

    expect(result.current.isActive).toBe(true);
  });

  it('should provide handleKeyDown function', () => {
    const { result } = renderHook(
      () => useContextualKeyboard('board', () => {}),
      { wrapper: createWrapper('board') }
    );

    expect(typeof result.current.handleKeyDown).toBe('function');
  });
});
