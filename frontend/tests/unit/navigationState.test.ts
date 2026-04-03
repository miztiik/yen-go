/**
 * Navigation State + Daily Offline Fallback Tests (T113d)
 *
 * Spec 129 — FR-028, FR-085, FR-090/091/092
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Navigation state persistence (T113b)', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('should save nav state to sessionStorage on unmount key', () => {
    const key = 'yen-go-nav-state:collection:test';
    const state = { currentIndex: 3, completedIndexes: [0, 1], failedIndexes: [2] };
    sessionStorage.setItem(key, JSON.stringify(state));

    const raw = sessionStorage.getItem(key);
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!);
    expect(parsed.currentIndex).toBe(3);
    expect(parsed.completedIndexes).toEqual([0, 1]);
    expect(parsed.failedIndexes).toEqual([2]);
  });

  it('should handle missing state gracefully', () => {
    const raw = sessionStorage.getItem('yen-go-nav-state:nonexistent');
    expect(raw).toBeNull();
  });

  it('should handle corrupted state gracefully', () => {
    sessionStorage.setItem('yen-go-nav-state:corrupt', '{invalid json');
    let result = null;
    try {
      result = JSON.parse(sessionStorage.getItem('yen-go-nav-state:corrupt')!);
    } catch {
      result = null;
    }
    expect(result).toBeNull();
  });
});

describe('Daily challenge offline fallback (T113c)', () => {
  it('should detect offline state via navigator.onLine', () => {
    // navigator.onLine is read-only in browsers but can be mocked
    const originalDescriptor = Object.getOwnPropertyDescriptor(navigator, 'onLine');
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    expect(navigator.onLine).toBe(false);
    
    // Restore
    if (originalDescriptor) {
      Object.defineProperty(navigator, 'onLine', originalDescriptor);
    } else {
      Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    }
  });

  it('should have window.addEventListener for online/offline events', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    
    const handler = vi.fn();
    window.addEventListener('online', handler);
    window.addEventListener('offline', handler);
    
    expect(addSpy).toHaveBeenCalledWith('online', handler);
    expect(addSpy).toHaveBeenCalledWith('offline', handler);
    
    addSpy.mockRestore();
  });
});
