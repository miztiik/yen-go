/**
 * Rush Mode Model Tests
 * @module tests/unit/rush.test
 */

import { describe, it, expect } from 'vitest';
import {
  createRushSession,
  calculateSolveScore,
  calculateSkipPenalty,
  shouldAutoSkip,
  formatTimeRemaining,
  getRushSummary,
  DEFAULT_RUSH_CONFIG,
  RUSH_DURATION_OPTIONS,
  type RushConfig,
  type RushSession,
  type RushDuration,
  type RushDifficulty,
} from '../../src/models/rush';
import type { Puzzle } from '../../src/models/puzzle';

// Mock puzzle for testing
const mockPuzzle: Puzzle = {
  id: 'test-puzzle-001',
  fen: '19x19:b[aa,bb];w[cc,dd]',
  difficulty: 'intermediate',
  tags: ['capture'],
  solutionPath: ['ef', 'gh'],
  explanation: { objective: 'Capture the stones', moves: {} },
};

describe('Rush Mode Model', () => {
  describe('DEFAULT_RUSH_CONFIG', () => {
    it('should have 3-minute default duration', () => {
      expect(DEFAULT_RUSH_CONFIG.duration).toBe(180);
    });

    it('should have mixed difficulty default', () => {
      expect(DEFAULT_RUSH_CONFIG.difficulty).toBe('mixed');
    });

    it('should have 1 point skip penalty', () => {
      expect(DEFAULT_RUSH_CONFIG.skipPenalty).toBe(1);
    });

    it('should have 3 max consecutive wrong', () => {
      expect(DEFAULT_RUSH_CONFIG.maxConsecutiveWrong).toBe(3);
    });
  });

  describe('RUSH_DURATION_OPTIONS', () => {
    it('should have 3 duration options', () => {
      expect(RUSH_DURATION_OPTIONS).toHaveLength(3);
    });

    it('should include 1 minute option', () => {
      const option = RUSH_DURATION_OPTIONS.find(o => o.value === 60);
      expect(option).toBeDefined();
      expect(option?.label).toBe('1 minute');
    });

    it('should include 3 minutes option', () => {
      const option = RUSH_DURATION_OPTIONS.find(o => o.value === 180);
      expect(option).toBeDefined();
      expect(option?.label).toBe('3 minutes');
    });

    it('should include 5 minutes option', () => {
      const option = RUSH_DURATION_OPTIONS.find(o => o.value === 300);
      expect(option).toBeDefined();
      expect(option?.label).toBe('5 minutes');
    });
  });

  describe('createRushSession', () => {
    it('should create session with default config', () => {
      const session = createRushSession();
      expect(session.config).toEqual(DEFAULT_RUSH_CONFIG);
      expect(session.state).toBe('idle');
      expect(session.score).toBe(0);
      expect(session.timeRemainingSeconds).toBe(180);
    });

    it('should create session with custom duration', () => {
      const session = createRushSession({ duration: 60 });
      expect(session.config.duration).toBe(60);
      expect(session.timeRemainingSeconds).toBe(60);
    });

    it('should create session with custom difficulty', () => {
      const session = createRushSession({ difficulty: 'beginner' });
      expect(session.config.difficulty).toBe('beginner');
    });

    it('should initialize with null start timestamp', () => {
      const session = createRushSession();
      expect(session.startedAt).toBeNull();
    });

    it('should initialize with empty puzzle results', () => {
      const session = createRushSession();
      expect(session.puzzleResults).toEqual([]);
    });

    it('should initialize with null current puzzle', () => {
      const session = createRushSession();
      expect(session.currentPuzzle).toBeNull();
    });

    it('should initialize counters to zero', () => {
      const session = createRushSession();
      expect(session.currentPuzzleIndex).toBe(0);
      expect(session.consecutiveWrong).toBe(0);
      expect(session.puzzlesSolved).toBe(0);
      expect(session.puzzlesSkipped).toBe(0);
    });

    it('should merge partial config with defaults', () => {
      const session = createRushSession({ skipPenalty: 2 });
      expect(session.config.skipPenalty).toBe(2);
      expect(session.config.duration).toBe(180); // default preserved
      expect(session.config.difficulty).toBe('mixed'); // default preserved
    });
  });

  describe('calculateSolveScore', () => {
    it('should return 1 point for solving puzzle', () => {
      const score = calculateSolveScore(mockPuzzle, 0);
      expect(score).toBe(1);
    });

    it('should return 1 point even with wrong attempts', () => {
      const score = calculateSolveScore(mockPuzzle, 2);
      expect(score).toBe(1);
    });

    it('should return 1 point at exactly 3 wrong attempts', () => {
      const score = calculateSolveScore(mockPuzzle, 3);
      expect(score).toBe(1);
    });

    it('should return 1 point for many wrong attempts', () => {
      const score = calculateSolveScore(mockPuzzle, 10);
      expect(score).toBe(1);
    });
  });

  describe('calculateSkipPenalty', () => {
    it('should return negative skip penalty from config', () => {
      const penalty = calculateSkipPenalty(DEFAULT_RUSH_CONFIG);
      expect(penalty).toBe(-1);
    });

    it('should return custom skip penalty', () => {
      const config: RushConfig = { ...DEFAULT_RUSH_CONFIG, skipPenalty: 2 };
      const penalty = calculateSkipPenalty(config);
      expect(penalty).toBe(-2);
    });

    it('should return zero for zero penalty config', () => {
      const config: RushConfig = { ...DEFAULT_RUSH_CONFIG, skipPenalty: 0 };
      const penalty = calculateSkipPenalty(config);
      expect(penalty).toBe(0);
    });
  });

  describe('shouldAutoSkip', () => {
    it('should return false for 0 consecutive wrong', () => {
      const session = createRushSession();
      expect(shouldAutoSkip(session)).toBe(false);
    });

    it('should return false for 1 consecutive wrong', () => {
      const session: RushSession = { ...createRushSession(), consecutiveWrong: 1 };
      expect(shouldAutoSkip(session)).toBe(false);
    });

    it('should return false for 2 consecutive wrong', () => {
      const session: RushSession = { ...createRushSession(), consecutiveWrong: 2 };
      expect(shouldAutoSkip(session)).toBe(false);
    });

    it('should return true for 3 consecutive wrong (default max)', () => {
      const session: RushSession = { ...createRushSession(), consecutiveWrong: 3 };
      expect(shouldAutoSkip(session)).toBe(true);
    });

    it('should return true for more than max consecutive wrong', () => {
      const session: RushSession = { ...createRushSession(), consecutiveWrong: 5 };
      expect(shouldAutoSkip(session)).toBe(true);
    });

    it('should respect custom maxConsecutiveWrong config', () => {
      const session: RushSession = {
        ...createRushSession({ maxConsecutiveWrong: 5 }),
        consecutiveWrong: 4,
      };
      expect(shouldAutoSkip(session)).toBe(false);

      const session2: RushSession = {
        ...createRushSession({ maxConsecutiveWrong: 5 }),
        consecutiveWrong: 5,
      };
      expect(shouldAutoSkip(session2)).toBe(true);
    });
  });

  describe('formatTimeRemaining', () => {
    it('should format 0 seconds as 0:00', () => {
      expect(formatTimeRemaining(0)).toBe('0:00');
    });

    it('should format 30 seconds as 0:30', () => {
      expect(formatTimeRemaining(30)).toBe('0:30');
    });

    it('should format 60 seconds as 1:00', () => {
      expect(formatTimeRemaining(60)).toBe('1:00');
    });

    it('should format 90 seconds as 1:30', () => {
      expect(formatTimeRemaining(90)).toBe('1:30');
    });

    it('should format 180 seconds as 3:00', () => {
      expect(formatTimeRemaining(180)).toBe('3:00');
    });

    it('should format 185 seconds as 3:05', () => {
      expect(formatTimeRemaining(185)).toBe('3:05');
    });

    it('should format 300 seconds as 5:00', () => {
      expect(formatTimeRemaining(300)).toBe('5:00');
    });

    it('should pad single digit seconds with zero', () => {
      expect(formatTimeRemaining(61)).toBe('1:01');
      expect(formatTimeRemaining(69)).toBe('1:09');
    });
  });

  describe('getRushSummary', () => {
    it('should show summary for new session', () => {
      const session = createRushSession();
      const summary = getRushSummary(session);
      expect(summary).toBe('Score: 0 | Solved: 0/0');
    });

    it('should show summary with solved puzzles', () => {
      const session: RushSession = {
        ...createRushSession(),
        score: 5,
        puzzlesSolved: 5,
        puzzlesSkipped: 0,
      };
      const summary = getRushSummary(session);
      expect(summary).toBe('Score: 5 | Solved: 5/5');
    });

    it('should show summary with skipped puzzles', () => {
      const session: RushSession = {
        ...createRushSession(),
        score: 3,
        puzzlesSolved: 4,
        puzzlesSkipped: 1,
      };
      const summary = getRushSummary(session);
      expect(summary).toBe('Score: 3 | Solved: 4/5');
    });

    it('should show negative score in display (note: actual gameplay clamps score to 0 per FR-041)', () => {
      // This tests the formatting function only - in actual gameplay,
      // RushMode.tsx clamps score to Math.max(0, score) per spec requirement
      const session: RushSession = {
        ...createRushSession(),
        score: -2,
        puzzlesSolved: 0,
        puzzlesSkipped: 2,
      };
      const summary = getRushSummary(session);
      expect(summary).toBe('Score: -2 | Solved: 0/2');
    });
  });

  describe('Type constraints', () => {
    it('should only allow valid RushDuration values', () => {
      const validDurations: RushDuration[] = [60, 180, 300];
      validDurations.forEach(d => {
        const session = createRushSession({ duration: d });
        expect(session.config.duration).toBe(d);
      });
    });

    it('should only allow valid RushDifficulty values', () => {
      const validDifficulties: RushDifficulty[] = ['mixed', 'beginner', 'intermediate', 'advanced'];
      validDifficulties.forEach(d => {
        const session = createRushSession({ difficulty: d });
        expect(session.config.difficulty).toBe(d);
      });
    });
  });
});
