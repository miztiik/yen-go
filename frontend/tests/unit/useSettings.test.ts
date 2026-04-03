/**
 * Unit test for useSettings hook.
 *
 * Tests: load/save/validate/legacy cleanup/defaults/cross-component reactivity.
 * Spec 127: T053 (test-first for T004)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/preact';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
    _store: store,
    _reset() { store = {}; },
  };
})();

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });
Object.defineProperty(document, 'documentElement', {
  value: {
    setAttribute: vi.fn(),
    getAttribute: vi.fn(),
  },
  writable: true,
});

// Import after mocks
import { useSettings, _resetSettingsForTesting } from '../../src/hooks/useSettings';

describe('useSettings', () => {
  beforeEach(() => {
    localStorageMock.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    if (typeof _resetSettingsForTesting === 'function') {
      _resetSettingsForTesting();
    }
  });

  it('returns default settings when no localStorage data', () => {
    const { result } = renderHook(() => useSettings());
    expect(result.current.settings).toEqual({
      theme: 'light',
      soundEnabled: true,
      coordinateLabels: true,
      autoAdvance: false,
      autoAdvanceDelay: 3,
    });
  });

  it('loads saved settings from localStorage', () => {
    localStorageMock.setItem('yengo:settings', JSON.stringify({
      theme: 'dark',
      soundEnabled: false,
      coordinateLabels: true,
    }));
    if (typeof _resetSettingsForTesting === 'function') {
      _resetSettingsForTesting();
    }

    const { result } = renderHook(() => useSettings());
    expect(result.current.settings.theme).toBe('dark');
    expect(result.current.settings.soundEnabled).toBe(false);
    expect(result.current.settings.coordinateLabels).toBe(true);
  });

  it('fills missing fields from defaults', () => {
    localStorageMock.setItem('yengo:settings', JSON.stringify({ theme: 'dark' }));
    if (typeof _resetSettingsForTesting === 'function') {
      _resetSettingsForTesting();
    }

    const { result } = renderHook(() => useSettings());
    expect(result.current.settings.soundEnabled).toBe(true);
    expect(result.current.settings.coordinateLabels).toBe(true);
  });

  it('resets invalid theme to light', () => {
    localStorageMock.setItem('yengo:settings', JSON.stringify({
      theme: 'system',
      soundEnabled: true,
      coordinateLabels: false,
    }));
    if (typeof _resetSettingsForTesting === 'function') {
      _resetSettingsForTesting();
    }

    const { result } = renderHook(() => useSettings());
    expect(result.current.settings.theme).toBe('light');
  });

  it('updateSettings merges partial updates', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ soundEnabled: false });
    });

    expect(result.current.settings.soundEnabled).toBe(false);
    expect(result.current.settings.theme).toBe('light');
  });

  it('persists settings to localStorage on update', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ theme: 'dark' });
    });

    const stored = localStorageMock.getItem('yengo:settings');
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.theme).toBe('dark');
  });

  it('resetSettings restores defaults', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ theme: 'dark', soundEnabled: false });
    });
    act(() => {
      result.current.resetSettings();
    });

    expect(result.current.settings).toEqual({
      theme: 'light',
      soundEnabled: true,
      coordinateLabels: true,
      autoAdvance: false,
      autoAdvanceDelay: 3,
    });
  });

  it('applies theme to document element on change', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ theme: 'dark' });
    });

    expect(document.documentElement.setAttribute).toHaveBeenCalledWith('data-theme', 'dark');
  });

  it('returns default auto-advance settings', () => {
    const { result } = renderHook(() => useSettings());
    expect(result.current.settings.autoAdvance).toBe(false);
    expect(result.current.settings.autoAdvanceDelay).toBe(3);
  });

  it('updates auto-advance settings', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ autoAdvance: true, autoAdvanceDelay: 2 });
    });

    expect(result.current.settings.autoAdvance).toBe(true);
    expect(result.current.settings.autoAdvanceDelay).toBe(2);
  });

  it('clamps auto-advance delay to valid range', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ autoAdvanceDelay: 10 });
    });
    expect(result.current.settings.autoAdvanceDelay).toBe(5);

    act(() => {
      result.current.updateSettings({ autoAdvanceDelay: 0 });
    });
    expect(result.current.settings.autoAdvanceDelay).toBe(1);
  });

  it('fills default auto-advance fields from legacy stored settings', () => {
    localStorageMock.setItem('yengo:settings', JSON.stringify({ theme: 'dark' }));
    if (typeof _resetSettingsForTesting === 'function') {
      _resetSettingsForTesting();
    }

    const { result } = renderHook(() => useSettings());
    expect(result.current.settings.autoAdvance).toBe(false);
    expect(result.current.settings.autoAdvanceDelay).toBe(3);
  });

  it('resetSettings clears auto-advance to defaults', () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({ autoAdvance: true, autoAdvanceDelay: 5 });
    });
    act(() => {
      result.current.resetSettings();
    });

    expect(result.current.settings.autoAdvance).toBe(false);
    expect(result.current.settings.autoAdvanceDelay).toBe(3);
  });
});
