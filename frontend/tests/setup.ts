/**
 * Vitest global setup file
 * Runs before all tests
 */

import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/preact';

// Cleanup after each test to ensure DOM is clean and state is reset
afterEach(() => {
  cleanup();
  vi.useRealTimers();      // CRITICAL: Restore real timers (prevents fake timer pollution)
  vi.restoreAllMocks();    // Restore mock implementations
  vi.clearAllTimers();     // Clear any pending fake timers
  vi.unstubAllGlobals();   // Restore stubbed globals
});

// Mock localStorage for tests
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem(key: string): string | null {
    return this.store[key] ?? null;
  },
  setItem(key: string, value: string): void {
    this.store[key] = value;
  },
  removeItem(key: string): void {
    delete this.store[key];
  },
  clear(): void {
    this.store = {};
  },
  get length(): number {
    return Object.keys(this.store).length;
  },
  key(index: number): string | null {
    const keys = Object.keys(this.store);
    return keys[index] ?? null;
  },
};

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
});

// Reset localStorage before each test
afterEach(() => {
  localStorageMock.clear();
});

// Mock matchMedia
Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver
class ResizeObserverMock {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
});
