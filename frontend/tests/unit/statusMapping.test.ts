/**
 * StatusMapping utility tests (T023)
 *
 * Spec 129 — FR-028
 */

import { describe, it, expect } from 'vitest';
import {
  toProblemNavStatus,
  toCarouselStatus,
} from '../../src/utils/statusMapping';

describe('toProblemNavStatus', () => {
  it('should return "solved" when completed and not failed', () => {
    expect(toProblemNavStatus(true, false)).toBe('solved');
  });

  it('should return "failed" when failed (takes precedence)', () => {
    expect(toProblemNavStatus(false, true)).toBe('failed');
    expect(toProblemNavStatus(true, true)).toBe('failed');
  });

  it('should return "unsolved" when neither completed nor failed', () => {
    expect(toProblemNavStatus(false, false)).toBe('unsolved');
  });
});

describe('toCarouselStatus', () => {
  const completed = new Set([0, 2]);
  const failed = new Set([1]);

  it('should return "current" for current index', () => {
    expect(toCarouselStatus(3, 3, completed, failed)).toBe('current');
  });

  it('should return "current" even if also completed', () => {
    expect(toCarouselStatus(0, 0, completed, failed)).toBe('current');
  });

  it('should return "correct" for completed index', () => {
    expect(toCarouselStatus(0, 3, completed, failed)).toBe('correct');
  });

  it('should return "incorrect" for failed index', () => {
    expect(toCarouselStatus(1, 3, completed, failed)).toBe('incorrect');
  });

  it('should return "unsolved" for untouched index', () => {
    expect(toCarouselStatus(4, 3, completed, failed)).toBe('unsolved');
  });
});
