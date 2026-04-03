/**
 * Tests for retryQueue service
 * @module tests/unit/retryQueue.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  addToRetryQueue,
  getRetryQueue,
  removeFromRetryQueue,
  clearRetryQueue,
} from '@services/retryQueue';

describe('retryQueue', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('returns empty array when queue is empty', () => {
    expect(getRetryQueue()).toEqual([]);
  });

  it('adds an entry and retrieves it', () => {
    addToRetryQueue('puzzle-1', 'ladder');
    const queue = getRetryQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0]).toMatchObject({
      puzzleId: 'puzzle-1',
      context: 'ladder',
      retryCount: 1,
    });
    expect(queue[0]?.failedAt).toBeTruthy();
  });

  it('increments retryCount on re-add', () => {
    addToRetryQueue('puzzle-1', 'ladder');
    addToRetryQueue('puzzle-1', 'ladder');
    addToRetryQueue('puzzle-1', 'ladder');
    const queue = getRetryQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0]?.retryCount).toBe(3);
  });

  it('updates context on re-add', () => {
    addToRetryQueue('puzzle-1', 'ladder');
    addToRetryQueue('puzzle-1', 'snapback');
    const queue = getRetryQueue();
    expect(queue[0]?.context).toBe('snapback');
  });

  it('filters by context', () => {
    addToRetryQueue('p1', 'ladder');
    addToRetryQueue('p2', 'snapback');
    addToRetryQueue('p3', 'ladder');

    expect(getRetryQueue('ladder')).toHaveLength(2);
    expect(getRetryQueue('snapback')).toHaveLength(1);
    expect(getRetryQueue('ko')).toHaveLength(0);
  });

  it('removes a specific puzzle', () => {
    addToRetryQueue('p1', 'ladder');
    addToRetryQueue('p2', 'snapback');
    removeFromRetryQueue('p1');

    const queue = getRetryQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0]?.puzzleId).toBe('p2');
  });

  it('remove is a no-op for non-existent puzzle', () => {
    addToRetryQueue('p1', 'ladder');
    removeFromRetryQueue('non-existent');
    expect(getRetryQueue()).toHaveLength(1);
  });

  it('clears entire queue when no context given', () => {
    addToRetryQueue('p1', 'ladder');
    addToRetryQueue('p2', 'snapback');
    clearRetryQueue();
    expect(getRetryQueue()).toEqual([]);
  });

  it('clears only matching context entries', () => {
    addToRetryQueue('p1', 'ladder');
    addToRetryQueue('p2', 'snapback');
    addToRetryQueue('p3', 'ladder');
    clearRetryQueue('ladder');

    const queue = getRetryQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0]?.puzzleId).toBe('p2');
  });

  it('handles corrupted localStorage gracefully', () => {
    localStorage.setItem('yen-go-retry-queue', 'not-json');
    expect(getRetryQueue()).toEqual([]);
  });
});
