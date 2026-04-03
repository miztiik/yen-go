/**
 * Collection Progress Unit Tests
 * @module tests/unit/collectionProgress.test
 *
 * Tests for collection progress tracking in progressTracker.
 * Covers: FR-008 to FR-011 (Progress Tracking)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
});

// Import after mocking localStorage
import {
  getCollectionProgress,
  startCollection,
  updateCollectionProgress,
  markPuzzleSolved,
  getResumePosition,
  clearCollectionProgress,
  getAllCollectionProgress,
  calculateCompletionPercentage,
  getCollectionStats,
} from '../../src/services/progressTracker';

describe('Collection Progress Tracking', () => {
  const COLLECTION_ID = 'test-collection-001';

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('getCollectionProgress', () => {
    it('should return null for new collection', () => {
      const progress = getCollectionProgress(COLLECTION_ID);
      expect(progress).toBeNull();
    });

    it('should return saved progress', () => {
      const savedProgress = {
        collectionId: COLLECTION_ID,
        currentIndex: 5,
        completedPuzzles: ['p1', 'p2', 'p3', 'p4', 'p5'],
        totalAttempts: 10,
        correctAttempts: 8,
        lastAccessedAt: new Date().toISOString(),
      };

      localStorageMock.setItem('yen-go-progress', JSON.stringify({
        collections: {
          [COLLECTION_ID]: savedProgress,
        },
      }));

      const progress = getCollectionProgress(COLLECTION_ID);
      
      expect(progress).not.toBeNull();
      expect(progress?.currentIndex).toBe(5);
      expect(progress?.completedPuzzles.length).toBe(5);
    });
  });

  describe('startCollection', () => {
    it('should initialize progress for new collection', () => {
      const result = startCollection(COLLECTION_ID, 20);

      expect(result.success).toBe(true);
      expect(result.data?.currentIndex).toBe(0);
      expect(result.data?.completedPuzzles).toEqual([]);
    });

    it('should return existing progress if already started', () => {
      startCollection(COLLECTION_ID, 20);
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      
      const result = startCollection(COLLECTION_ID, 20);

      expect(result.success).toBe(true);
      expect(result.data?.completedPuzzles.length).toBe(1);
    });

    it('should save to localStorage', () => {
      startCollection(COLLECTION_ID, 20);

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });
  });

  describe('updateCollectionProgress', () => {
    beforeEach(() => {
      startCollection(COLLECTION_ID, 20);
    });

    it('should update current index', () => {
      const result = updateCollectionProgress(COLLECTION_ID, { currentIndex: 10 });

      expect(result.success).toBe(true);
      expect(result.data?.currentIndex).toBe(10);
    });

    it('should preserve existing data when updating', () => {
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      
      const result = updateCollectionProgress(COLLECTION_ID, { currentIndex: 5 });

      expect(result.data?.completedPuzzles).toContain('p1');
    });

    it('should update lastAccessedAt timestamp', () => {
      const before = new Date().toISOString();
      
      updateCollectionProgress(COLLECTION_ID, { currentIndex: 5 });
      
      const progress = getCollectionProgress(COLLECTION_ID);
      expect(progress?.lastAccessedAt).toBeDefined();
      expect(new Date(progress?.lastAccessedAt ?? '').getTime())
        .toBeGreaterThanOrEqual(new Date(before).getTime());
    });
  });

  describe('markPuzzleSolved', () => {
    beforeEach(() => {
      startCollection(COLLECTION_ID, 20);
    });

    it('should add puzzle to completed list on correct solve', () => {
      const result = markPuzzleSolved(COLLECTION_ID, 'puzzle-1', true);

      expect(result.success).toBe(true);
      expect(result.data?.completedPuzzles).toContain('puzzle-1');
    });

    it('should increment attempt counts', () => {
      markPuzzleSolved(COLLECTION_ID, 'puzzle-1', true);
      markPuzzleSolved(COLLECTION_ID, 'puzzle-2', false);

      const progress = getCollectionProgress(COLLECTION_ID);
      
      expect(progress?.totalAttempts).toBe(2);
      expect(progress?.correctAttempts).toBe(1);
    });

    it('should advance currentIndex on solve', () => {
      const progress1 = markPuzzleSolved(COLLECTION_ID, 'puzzle-1', true);
      expect(progress1.data?.currentIndex).toBe(1);
      
      const progress2 = markPuzzleSolved(COLLECTION_ID, 'puzzle-2', true);
      expect(progress2.data?.currentIndex).toBe(2);
    });

    it('should not duplicate completed puzzles', () => {
      markPuzzleSolved(COLLECTION_ID, 'puzzle-1', true);
      markPuzzleSolved(COLLECTION_ID, 'puzzle-1', true);

      const progress = getCollectionProgress(COLLECTION_ID);
      
      const count = progress?.completedPuzzles.filter(p => p === 'puzzle-1').length;
      expect(count).toBe(1);
    });
  });

  describe('getResumePosition', () => {
    it('should return 0 for new collection', () => {
      const position = getResumePosition(COLLECTION_ID);
      expect(position).toBe(0);
    });

    it('should return current index from progress', () => {
      startCollection(COLLECTION_ID, 20);
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      markPuzzleSolved(COLLECTION_ID, 'p2', true);
      markPuzzleSolved(COLLECTION_ID, 'p3', true);

      const position = getResumePosition(COLLECTION_ID);
      expect(position).toBe(3);
    });
  });

  describe('clearCollectionProgress', () => {
    beforeEach(() => {
      startCollection(COLLECTION_ID, 20);
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
    });

    it('should clear progress for collection', () => {
      clearCollectionProgress(COLLECTION_ID);

      const progress = getCollectionProgress(COLLECTION_ID);
      expect(progress).toBeNull();
    });

    it('should preserve other collections', () => {
      const OTHER_COLLECTION = 'other-collection';
      startCollection(OTHER_COLLECTION, 10);
      markPuzzleSolved(OTHER_COLLECTION, 'other-p1', true);

      clearCollectionProgress(COLLECTION_ID);

      const otherProgress = getCollectionProgress(OTHER_COLLECTION);
      expect(otherProgress).not.toBeNull();
    });
  });

  describe('getAllCollectionProgress', () => {
    it('should return empty object when no progress', () => {
      const allProgress = getAllCollectionProgress();
      expect(Object.keys(allProgress).length).toBe(0);
    });

    it('should return all collection progress', () => {
      startCollection('collection-1', 10);
      startCollection('collection-2', 20);

      const allProgress = getAllCollectionProgress();

      expect(Object.keys(allProgress)).toContain('collection-1');
      expect(Object.keys(allProgress)).toContain('collection-2');
    });
  });

  describe('calculateCompletionPercentage', () => {
    it('should return 0 for new collection', () => {
      const percentage = calculateCompletionPercentage(COLLECTION_ID, 10);
      expect(percentage).toBe(0);
    });

    it('should calculate percentage correctly', () => {
      startCollection(COLLECTION_ID, 10);
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      markPuzzleSolved(COLLECTION_ID, 'p2', true);
      markPuzzleSolved(COLLECTION_ID, 'p3', true);

      const percentage = calculateCompletionPercentage(COLLECTION_ID, 10);
      expect(percentage).toBe(30);
    });

    it('should return 100 for completed collection', () => {
      startCollection(COLLECTION_ID, 3);
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      markPuzzleSolved(COLLECTION_ID, 'p2', true);
      markPuzzleSolved(COLLECTION_ID, 'p3', true);

      const percentage = calculateCompletionPercentage(COLLECTION_ID, 3);
      expect(percentage).toBe(100);
    });

    it('should handle edge case of zero total', () => {
      const percentage = calculateCompletionPercentage(COLLECTION_ID, 0);
      expect(percentage).toBe(0);
    });
  });

  describe('getCollectionStats', () => {
    beforeEach(() => {
      startCollection(COLLECTION_ID, 10);
    });

    it('should return initial stats for new collection', () => {
      const stats = getCollectionStats(COLLECTION_ID);

      expect(stats.totalPuzzles).toBe(10);
      expect(stats.completed).toBe(0);
      expect(stats.accuracy).toBe(0);
    });

    it('should calculate accuracy correctly', () => {
      markPuzzleSolved(COLLECTION_ID, 'p1', true);
      markPuzzleSolved(COLLECTION_ID, 'p2', true);
      markPuzzleSolved(COLLECTION_ID, 'p3', false);
      markPuzzleSolved(COLLECTION_ID, 'p4', true);

      const stats = getCollectionStats(COLLECTION_ID);

      expect(stats.completed).toBe(3);
      expect(stats.accuracy).toBe(75); // 3/4 correct = 75%
    });

    it('should include time tracking if available', () => {
      startCollection(COLLECTION_ID, 10);
      
      // Simulate time passage
      const progress = getCollectionProgress(COLLECTION_ID);
      if (progress) {
        const startTime = new Date(Date.now() - 300000); // 5 minutes ago
        localStorageMock.setItem('yen-go-progress', JSON.stringify({
          collections: {
            [COLLECTION_ID]: {
              ...progress,
              startedAt: startTime.toISOString(),
              totalTimeMs: 300000,
            },
          },
        }));
      }

      const stats = getCollectionStats(COLLECTION_ID);
      
      expect(stats.totalTimeMs).toBeDefined();
    });
  });
});

describe('Progress Persistence', () => {
  const COLLECTION_ID = 'persistence-test';

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('should persist across simulated page reloads', () => {
    // Initial session
    startCollection(COLLECTION_ID, 20);
    markPuzzleSolved(COLLECTION_ID, 'p1', true);
    markPuzzleSolved(COLLECTION_ID, 'p2', true);

    // Simulate page reload by reading fresh from localStorage
    const stored = localStorageMock.getItem('yen-go-progress');
    expect(stored).not.toBeNull();

    const progress = getCollectionProgress(COLLECTION_ID);
    expect(progress?.completedPuzzles).toContain('p1');
    expect(progress?.completedPuzzles).toContain('p2');
  });

  it('should handle corrupted localStorage gracefully', () => {
    localStorageMock.setItem('yen-go-progress', 'invalid json');

    // Should not throw, return null or empty
    const progress = getCollectionProgress(COLLECTION_ID);
    expect(progress).toBeNull();
  });
});
