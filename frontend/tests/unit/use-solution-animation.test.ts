/**
 * Solution Animation Hook Unit Tests
 * @module tests/unit/use-solution-animation.test
 *
 * Tests for T015: useSolutionAnimation hook for playback control.
 * Covers FR-004, FR-005, FR-006.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useSolutionAnimation } from '../../src/hooks/useSolutionAnimation';

// NOTE: Fake timers are now scoped to beforeEach/afterEach to prevent pollution
// (Moved from module level per T003 fix for test hanging issue)

describe('useSolutionAnimation', () => {
  beforeEach(() => {
    vi.useFakeTimers();  // Setup fake timers for each test
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();  // CRITICAL: Restore real timers after each test
  });

  describe('initialization', () => {
    it('should start at frame 0', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      expect(result.current.state.currentFrame).toBe(0);
    });

    it('should not be playing initially', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      expect(result.current.state.isPlaying).toBe(false);
    });

    it('should use provided total frames', () => {
      const { result } = renderHook(() => useSolutionAnimation(15));

      expect(result.current.state.totalFrames).toBe(15);
    });

    it('should use default delay', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      expect(result.current.state.delayMs).toBe(1500);
    });

    it('should use custom initial delay', () => {
      const { result } = renderHook(() => useSolutionAnimation(10, 500));

      expect(result.current.state.delayMs).toBe(500);
    });
  });

  describe('play/pause', () => {
    it('should start playing when play is called', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.play();
      });

      expect(result.current.state.isPlaying).toBe(true);
    });

    it('should stop playing when pause is called', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.play();
      });

      act(() => {
        result.current.actions.pause();
      });

      expect(result.current.state.isPlaying).toBe(false);
    });

    it('should advance frame after delay while playing', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.play();
      });

      expect(result.current.state.currentFrame).toBe(0);

      // Advance timer
      act(() => {
        vi.advanceTimersByTime(1500);
      });

      expect(result.current.state.currentFrame).toBe(1);
    });

    it('should stop at the last frame', () => {
      const { result } = renderHook(() => useSolutionAnimation(3, 500));

      act(() => {
        result.current.actions.play();
      });

      // Advance through all frames
      act(() => {
        vi.advanceTimersByTime(500); // Frame 1
      });
      act(() => {
        vi.advanceTimersByTime(500); // Frame 2
      });
      act(() => {
        vi.advanceTimersByTime(500); // Frame 3
      });

      expect(result.current.state.currentFrame).toBe(3);
      expect(result.current.state.isPlaying).toBe(false);
    });
  });

  describe('navigation', () => {
    it('should step forward one frame', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.stepForward();
      });

      expect(result.current.state.currentFrame).toBe(1);
    });

    it('should go to specific frame', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.goToFrame(5);
      });

      expect(result.current.state.currentFrame).toBe(5);
    });

    it('should step backward one frame', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.goToFrame(5);
      });

      act(() => {
        result.current.actions.stepBackward();
      });

      expect(result.current.state.currentFrame).toBe(4);
    });

    it('should not go below frame 0', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.stepBackward();
      });

      expect(result.current.state.currentFrame).toBe(0);
    });

    it('should not exceed total frames', () => {
      const { result } = renderHook(() => useSolutionAnimation(3));

      act(() => {
        result.current.actions.goToFrame(2);
      });

      act(() => {
        result.current.actions.stepForward();
      });

      expect(result.current.state.currentFrame).toBe(3);

      act(() => {
        result.current.actions.stepForward();
      });

      // Should stay at 3
      expect(result.current.state.currentFrame).toBe(3);
    });

    it('should clamp goToFrame to valid range', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.goToFrame(100);
      });

      expect(result.current.state.currentFrame).toBe(10);

      act(() => {
        result.current.actions.goToFrame(-5);
      });

      expect(result.current.state.currentFrame).toBe(0);
    });

    it('should reset to frame 0 and stop playing', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.goToFrame(7);
        result.current.actions.play();
      });

      act(() => {
        result.current.actions.reset();
      });

      expect(result.current.state.currentFrame).toBe(0);
      expect(result.current.state.isPlaying).toBe(false);
    });
  });

  describe('delay control', () => {
    it('should update delay', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.setDelay(500);
      });

      expect(result.current.state.delayMs).toBe(500);
    });

    it('should clamp delay to minimum', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.setDelay(100); // Below min
      });

      expect(result.current.state.delayMs).toBe(500); // MIN_DELAY_MS
    });

    it('should clamp delay to maximum', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      act(() => {
        result.current.actions.setDelay(10000); // Above max
      });

      expect(result.current.state.delayMs).toBe(3000); // MAX_DELAY_MS
    });

    it('should respect new delay during playback', () => {
      const { result } = renderHook(() => useSolutionAnimation(10, 1000));

      act(() => {
        result.current.actions.setDelay(500);
        result.current.actions.play();
      });

      // Advance by 500ms (new delay)
      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(result.current.state.currentFrame).toBe(1);
    });
  });

  describe('computed values', () => {
    it('should correctly compute canGoForward', () => {
      const { result } = renderHook(() => useSolutionAnimation(2));

      expect(result.current.canGoForward).toBe(true);

      act(() => {
        result.current.actions.goToFrame(2);
      });

      expect(result.current.canGoForward).toBe(false);
    });

    it('should correctly compute canGoBack', () => {
      const { result } = renderHook(() => useSolutionAnimation(10));

      expect(result.current.canGoBack).toBe(false);

      act(() => {
        result.current.actions.stepForward();
      });

      expect(result.current.canGoBack).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('should handle 0 total frames', () => {
      const { result } = renderHook(() => useSolutionAnimation(0));

      expect(result.current.state.currentFrame).toBe(0);
      expect(result.current.canGoForward).toBe(false);
    });

    it('should handle single frame', () => {
      const { result } = renderHook(() => useSolutionAnimation(1, 500));

      act(() => {
        result.current.actions.play();
      });

      // Should advance to frame 1 and stop
      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(result.current.state.currentFrame).toBe(1);
      expect(result.current.state.isPlaying).toBe(false);
    });

    it('should reset when totalFrames changes', () => {
      const { result, rerender } = renderHook(
        ({ total }: { total: number }) => useSolutionAnimation(total),
        { initialProps: { total: 10 } }
      );

      act(() => {
        result.current.actions.goToFrame(5);
        result.current.actions.play();
      });

      // Change total frames (new puzzle)
      rerender({ total: 20 });

      expect(result.current.state.currentFrame).toBe(0);
      expect(result.current.state.isPlaying).toBe(false);
    });

    it('should not play if already at end', () => {
      const { result } = renderHook(() => useSolutionAnimation(3));

      act(() => {
        result.current.actions.goToFrame(3);
      });

      act(() => {
        result.current.actions.play();
      });

      // Should not be playing since we're at the end
      expect(result.current.state.isPlaying).toBe(false);
    });
  });
});
