/**
 * Unit test for boot sequence.
 *
 * Tests: happy path, fetch failures, idempotency, error state.
 * Spec 127: T055 (test-first for T009)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock document for rendering
Object.defineProperty(globalThis, 'document', {
  value: {
    getElementById: vi.fn(() => ({
      innerHTML: '',
    })),
    documentElement: {
      setAttribute: vi.fn(),
      getAttribute: vi.fn(),
    },
  },
  writable: true,
});

// Mock preact render
vi.mock('preact', () => ({
  render: vi.fn(),
  h: vi.fn(),
}));

// Mock goban
vi.mock('goban', () => ({
  setGobanCallbacks: vi.fn(),
}));

import { boot, getBootConfigs, _resetBootForTesting } from '../../src/boot';

function mockFetchSuccess() {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('puzzle-levels.json')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          levels: [
            { slug: 'novice', name: 'Novice', rankRange: '30k+', order: 1 },
            { slug: 'beginner', name: 'Beginner', rankRange: '25k-20k', order: 2 },
          ],
        }),
      });
    }
    if (url.includes('tags.json')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          schema_version: '8.0',
          tags: {
            'life-and-death': {
              slug: 'life-and-death',
              id: 10,
              name: 'Life & Death',
              category: 'objective',
              description: 'Kill or live',
              aliases: ['killing'],
            },
          },
        }),
      });
    }
    if (url.includes('go-tips.json')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          schema_version: '1.0',
          tips: [
            { text: 'A group with two eyes is alive', category: 'definition', levels: ['novice'] },
          ],
        }),
      });
    }
    return Promise.resolve({ ok: false, status: 404 });
  });
}

describe('boot', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    if (typeof _resetBootForTesting === 'function') {
      _resetBootForTesting();
    }
  });

  it('should complete boot sequence on happy path', async () => {
    mockFetchSuccess();
    await boot();

    const configs = getBootConfigs();
    expect(configs.levels).toHaveLength(2);
    expect(configs.levels[0]?.slug).toBe('novice');
    expect(configs.tags).toHaveLength(1);
    expect(configs.tags[0]?.id).toBe(10);
    expect(configs.tips).toHaveLength(1);
  });

  it('should handle config fetch failure gracefully', async () => {
    mockFetch.mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500 })
    );

    // boot() should not throw — it handles errors gracefully with defaults
    await expect(boot()).resolves.not.toThrow();
  });

  it('should be idempotent — second call returns cached configs', async () => {
    mockFetchSuccess();
    await boot();
    mockFetch.mockReset();

    // Second call should NOT re-fetch
    await boot();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('getBootConfigs throws if called before boot', () => {
    expect(() => getBootConfigs()).toThrow();
  });
});
