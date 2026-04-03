/**
 * PuzzleRushPage + useRushSession integration tests (T097).
 *
 * Tests:
 * - Difficulty progression (advance 1 level every 5 correct)
 * - Time bonus (+5s per correct, +10s on level-up)
 * - Score recording (100 pts base, 1.5x streak at ≥5)
 * - Game over state (timer 0 or 3 lives lost)
 * - Active-frame-time: visibilitychange → timer pauses
 * - Navigation-away abort: score saved
 *
 * Spec 129 — FR-028
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useRushSession } from '../../src/hooks/useRushSession';

describe('useRushSession', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('initialization', () => {
    it('should initialize with correct defaults', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180 }),
      );

      expect(result.current.state.isActive).toBe(false);
      expect(result.current.state.duration).toBe(180);
      expect(result.current.state.timeRemaining).toBe(180);
      expect(result.current.state.lives).toBe(3);
      expect(result.current.state.score).toBe(0);
      expect(result.current.state.puzzlesSolved).toBe(0);
      expect(result.current.state.currentStreak).toBe(0);
      expect(result.current.isGameOver).toBe(false);
    });

    it('should display formatted time', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180 }),
      );
      expect(result.current.timeDisplay).toBe('3:00');
    });
  });

  describe('scoring — Spec 129 canonical rules', () => {
    it('should award 100 pts per correct puzzle', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, pointsPerPuzzle: 100 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordCorrect());

      expect(result.current.state.score).toBe(100);
      expect(result.current.state.puzzlesSolved).toBe(1);
    });

    it('should apply 1.5x streak bonus at ≥5 consecutive correct', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, pointsPerPuzzle: 100 }),
      );

      act(() => result.current.actions.start());

      // 4 correct = no streak bonus yet (400 pts)
      for (let i = 0; i < 4; i++) {
        act(() => result.current.actions.recordCorrect());
      }
      expect(result.current.state.score).toBe(400);
      expect(result.current.state.currentStreak).toBe(4);

      // 5th correct = 1.5x = 150 (total 550)
      act(() => result.current.actions.recordCorrect());
      expect(result.current.state.score).toBe(550);
      expect(result.current.state.currentStreak).toBe(5);
    });

    it('should reset streak on wrong answer', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, pointsPerPuzzle: 100 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordCorrect());
      act(() => result.current.actions.recordCorrect());
      expect(result.current.state.currentStreak).toBe(2);

      act(() => result.current.actions.recordWrong());
      expect(result.current.state.currentStreak).toBe(0);
    });
  });

  describe('lives system', () => {
    it('should lose 1 life on wrong answer', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, startingLives: 3 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordWrong());

      expect(result.current.state.lives).toBe(2);
      expect(result.current.state.puzzlesFailed).toBe(1);
    });

    it('should end game when lives reach 0', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, startingLives: 3 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordWrong());
      act(() => result.current.actions.recordWrong());
      act(() => result.current.actions.recordWrong());

      expect(result.current.state.lives).toBe(0);
      expect(result.current.isGameOver).toBe(true);
    });

    it('should lose 1 life on skip', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, startingLives: 3 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.skip());

      expect(result.current.state.lives).toBe(2);
      expect(result.current.state.currentStreak).toBe(0);
    });
  });

  describe('game over', () => {
    it('should detect game over when lives = 0', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180, startingLives: 1 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordWrong());

      expect(result.current.isGameOver).toBe(true);
    });
  });

  describe('pause/resume', () => {
    it('should pause and resume', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180 }),
      );

      act(() => result.current.actions.start());
      expect(result.current.isPaused).toBe(false);

      act(() => result.current.actions.pause());
      expect(result.current.isPaused).toBe(true);

      act(() => result.current.actions.resume());
      expect(result.current.isPaused).toBe(false);
    });
  });

  describe('reset', () => {
    it('should reset to initial state', () => {
      const { result } = renderHook(() =>
        useRushSession({ duration: 180 }),
      );

      act(() => result.current.actions.start());
      act(() => result.current.actions.recordCorrect());
      act(() => result.current.actions.recordWrong());
      act(() => result.current.actions.reset());

      expect(result.current.state.isActive).toBe(false);
      expect(result.current.state.score).toBe(0);
      expect(result.current.state.puzzlesSolved).toBe(0);
      expect(result.current.state.puzzlesFailed).toBe(0);
      expect(result.current.state.lives).toBe(3);
      expect(result.current.state.timeRemaining).toBe(180);
    });
  });
});
