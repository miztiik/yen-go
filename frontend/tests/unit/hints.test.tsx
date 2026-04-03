/**
 * Tests for useHints hook and HintPanel component
 * @module tests/unit/hints.test
 *
 * Covers: FR-032 to FR-035, US5
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { render, screen, fireEvent } from '@testing-library/preact';
import type { Puzzle } from '../../src/models/puzzle';
import { useHints } from '../../src/hooks/useHints';
import { HintPanel } from '../../src/components/Puzzle/HintPanel';

// --- Test Fixtures ---

function createTestPuzzle(hints: string[]): Puzzle {
  return {
    version: '1.0',
    id: 'test-puzzle',
    boardSize: 9,
    initialState: Array(9).fill(null).map(() => Array(9).fill('empty')),
    sideToMove: 'black',
    solutionTree: {
      move: { x: 4, y: 4 },
    },
    hints,
    explanations: [],
    metadata: {
      difficulty: '15kyu',
      difficultyScore: 2,
      tags: ['test'],
      level: '2026-01-20',
      createdAt: '2026-01-20T00:00:00Z',
    },
  };
}

const THREE_HINT_PUZZLE = createTestPuzzle([
  'First hint: Look at the corner',
  'Second hint: Focus on the vital point',
  'Third hint: The key move is on the 3rd line',
]);

const ONE_HINT_PUZZLE = createTestPuzzle(['Only one hint available']);

const NO_HINT_PUZZLE = createTestPuzzle([]);

// --- useHints Hook Tests ---

describe('useHints', () => {
  describe('initialization', () => {
    it('should start with no revealed hints', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      expect(result.current.revealedHints).toEqual([]);
      expect(result.current.hintsUsed).toBe(0);
      expect(result.current.nextHintIndex).toBe(0);
    });

    it('should report correct total hints', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      expect(result.current.totalHints).toBe(3);
    });

    it('should indicate more hints available initially', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      expect(result.current.hasMoreHints).toBe(true);
    });

    it('should handle puzzle with no hints', () => {
      const { result } = renderHook(() => useHints(NO_HINT_PUZZLE));

      expect(result.current.totalHints).toBe(0);
      expect(result.current.hasMoreHints).toBe(false);
    });

    it('should handle null puzzle', () => {
      const { result } = renderHook(() => useHints(null));

      expect(result.current.totalHints).toBe(0);
      expect(result.current.hasMoreHints).toBe(false);
    });
  });

  describe('requestHint', () => {
    it('should reveal first hint', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      let hint: string | null = null;
      act(() => {
        hint = result.current.requestHint();
      });

      expect(hint).toBe('First hint: Look at the corner');
      expect(result.current.revealedHints).toEqual(['First hint: Look at the corner']);
      expect(result.current.hintsUsed).toBe(1);
    });

    it('should reveal hints progressively', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      act(() => {
        result.current.requestHint();
      });
      act(() => {
        result.current.requestHint();
      });

      expect(result.current.revealedHints).toHaveLength(2);
      expect(result.current.revealedHints[1]).toBe('Second hint: Focus on the vital point');
      expect(result.current.hintsUsed).toBe(2);
    });

    it('should return null when no more hints', () => {
      const { result } = renderHook(() => useHints(ONE_HINT_PUZZLE));

      act(() => {
        result.current.requestHint();
      });

      let hint: string | null = 'not null';
      act(() => {
        hint = result.current.requestHint();
      });

      expect(hint).toBeNull();
      expect(result.current.hintsUsed).toBe(1);
    });

    it('should update hasMoreHints correctly', () => {
      const { result } = renderHook(() => useHints(ONE_HINT_PUZZLE));

      expect(result.current.hasMoreHints).toBe(true);

      act(() => {
        result.current.requestHint();
      });

      expect(result.current.hasMoreHints).toBe(false);
    });
  });

  describe('resetHints', () => {
    it('should reset all revealed hints', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      act(() => {
        result.current.requestHint();
        result.current.requestHint();
      });

      expect(result.current.hintsUsed).toBe(2);

      act(() => {
        result.current.resetHints();
      });

      expect(result.current.revealedHints).toEqual([]);
      expect(result.current.hintsUsed).toBe(0);
      expect(result.current.hasMoreHints).toBe(true);
    });
  });

  describe('getHintByIndex', () => {
    it('should return hint at specific index', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      const hint = result.current.getHintByIndex(1);

      expect(hint).toBe('Second hint: Focus on the vital point');
    });

    it('should return null for invalid index', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      expect(result.current.getHintByIndex(-1)).toBeNull();
      expect(result.current.getHintByIndex(10)).toBeNull();
    });
  });

  describe('getAllHints', () => {
    it('should return all hints for review mode', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      const allHints = result.current.getAllHints();

      expect(allHints).toHaveLength(3);
      expect(allHints).toEqual(THREE_HINT_PUZZLE.hints);
    });
  });

  describe('enabled prop', () => {
    it('should return empty when disabled', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE, false));

      expect(result.current.totalHints).toBe(0);
      expect(result.current.hasMoreHints).toBe(false);
    });

    it('should not reveal hints when disabled', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE, false));

      const hint = result.current.requestHint();

      expect(hint).toBeNull();
    });
  });
});

// --- HintPanel Component Tests ---

describe('HintPanel', () => {
  describe('rendering', () => {
    it('should render hint panel with puzzle', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      expect(screen.getByRole('region', { name: /hint/i })).toBeDefined();
      expect(screen.getByRole('heading', { name: /hints/i })).toBeDefined();
      // Check for counter format (0/3) - text is split but contained in span
      const heading = screen.getByRole('heading');
      expect(heading.textContent).toContain('Hints');
      expect(heading.textContent).toContain('0');
      expect(heading.textContent).toContain('3');
    });

    it('should render "Get Hint" button', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      expect(screen.getByRole('button', { name: /get hint/i })).toBeDefined();
    });

    it('should not render when puzzle is null', () => {
      const { container } = render(<HintPanel puzzle={null} />);

      expect(container.innerHTML).toBe('');
    });

    it('should not render when disabled', () => {
      const { container } = render(<HintPanel puzzle={THREE_HINT_PUZZLE} enabled={false} />);

      expect(container.innerHTML).toBe('');
    });

    it('should show empty state initially', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      expect(screen.getByText(/No hints used yet/i)).toBeDefined();
    });
  });

  describe('hint requesting', () => {
    it('should reveal hint when button clicked', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      expect(screen.getByText('First hint: Look at the corner')).toBeDefined();
    });

    it('should update counter after hint requested', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      expect(screen.getByText('(1/3)')).toBeDefined();
    });

    it('should call onHintRequested callback', () => {
      const onHintRequested = vi.fn();
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} onHintRequested={onHintRequested} />);

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      // Note: hintsUsed is captured before increment in the callback
      expect(onHintRequested).toHaveBeenCalledWith('First hint: Look at the corner', 0);
    });

    it('should disable button when no more hints', () => {
      render(<HintPanel puzzle={ONE_HINT_PUZZLE} />);

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      const disabledButton = screen.getByRole('button', { name: /no more hints/i });
      expect(disabledButton).toBeDefined();
      expect(disabledButton.getAttribute('disabled')).not.toBeNull();
    });
  });

  describe('hint reset', () => {
    it('should show reset button after using hints', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      // No reset button initially
      expect(screen.queryByRole('button', { name: /reset/i })).toBeNull();

      // Request a hint
      const hintButton = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(hintButton);

      // Reset button should appear
      expect(screen.getByRole('button', { name: /reset/i })).toBeDefined();
    });

    it('should reset hints when reset clicked', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      // Request hints
      const hintButton = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(hintButton);
      fireEvent.click(hintButton);

      // Click reset
      const resetButton = screen.getByRole('button', { name: /reset/i });
      fireEvent.click(resetButton);

      // Should be back to initial state
      expect(screen.getByText('(0/3)')).toBeDefined();
      expect(screen.getByText(/No hints used yet/i)).toBeDefined();
    });

    it('should call onHintsReset callback', () => {
      const onHintsReset = vi.fn();
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} onHintsReset={onHintsReset} />);

      // Request a hint
      const hintButton = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(hintButton);

      // Reset
      const resetButton = screen.getByRole('button', { name: /reset/i });
      fireEvent.click(resetButton);

      expect(onHintsReset).toHaveBeenCalled();
    });
  });

  describe('progress indicator', () => {
    it('should render progress bar', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeDefined();
      expect(progressBar.getAttribute('aria-valuemax')).toBe('3');
    });

    it('should update progress as hints revealed', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar.getAttribute('aria-valuenow')).toBe('0');

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      expect(progressBar.getAttribute('aria-valuenow')).toBe('1');
    });
  });

  describe('accessibility', () => {
    it('should have accessible region', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const region = screen.getByRole('region', { name: /puzzle hints/i });
      expect(region).toBeDefined();
    });

    it('should have accessible button labels', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const button = screen.getByRole('button', { name: /get hint 1 of 3/i });
      expect(button).toBeDefined();
    });

    it('should have accessible hint list', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} />);

      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);

      const list = screen.getByRole('list', { name: /revealed hints/i });
      expect(list).toBeDefined();

      const listItem = screen.getByRole('listitem', { name: /hint 1/i });
      expect(listItem).toBeDefined();
    });
  });

  describe('compact mode', () => {
    it('should render in compact mode', () => {
      render(<HintPanel puzzle={THREE_HINT_PUZZLE} compact />);

      const panel = screen.getByRole('region');
      expect(panel.className).toContain('compact');
    });
  });
});

// --- Integration: Hint tracking in progress ---

describe('Hint Usage Tracking', () => {
  let mockStore: Record<string, string>;

  beforeEach(() => {
    mockStore = {};

    const mockLocalStorage = {
      getItem: vi.fn((key: string) => mockStore[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        mockStore[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete mockStore[key];
      }),
      clear: vi.fn(() => {
        mockStore = {};
      }),
      get length() {
        return Object.keys(mockStore).length;
      },
      key: vi.fn((i: number) => Object.keys(mockStore)[i] ?? null),
    };

    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should track hints used in puzzle completion record', async () => {
    // Import dynamically to get fresh module with mocked localStorage
    const { recordPuzzleCompletion, loadProgress } = await import(
      '../../src/services/progressTracker'
    );

    // Record a completion with hints (using correct API)
    const result = recordPuzzleCompletion('test-puzzle-1', {
      timeSpentMs: 30000,
      attempts: 2,
      hintsUsed: 2,
      perfectSolve: false,
      difficulty: 'beginner',
    });

    expect(result.success).toBe(true);

    // Verify hints are stored
    const progress = loadProgress();
    expect(progress.success).toBe(true);
    expect(progress.data?.completedPuzzles['test-puzzle-1']?.hintsUsed).toBe(2);
  });

  it('should accumulate total hints in statistics', async () => {
    const { recordPuzzleCompletion, getStatistics } = await import(
      '../../src/services/progressTracker'
    );

    // Complete multiple puzzles with hints
    recordPuzzleCompletion('puzzle-1', {
      timeSpentMs: 10000,
      attempts: 1,
      hintsUsed: 1,
      perfectSolve: true,
      difficulty: 'beginner',
    });

    recordPuzzleCompletion('puzzle-2', {
      timeSpentMs: 20000,
      attempts: 1,
      hintsUsed: 3,
      perfectSolve: true,
      difficulty: 'beginner',
    });

    const stats = getStatistics();
    expect(stats.totalHintsUsed).toBe(4);
  });
});
// --- Integration: Full Hint Flow (T027) ---

describe('Full Hint Flow Integration', () => {
  describe('Progressive Hint Request Flow', () => {
    it('should provide hints in correct order (position → technique → text)', () => {
      // Create a puzzle with structured hints
      const puzzleWithStructuredHints = createTestPuzzle([
        'Hint 1: Look at position A1',
        'Hint 2: This is a ladder technique',
        'Hint 3: Play the atari at the corner',
      ]);

      const { result } = renderHook(() => useHints(puzzleWithStructuredHints));

      // Request hints progressively
      let hint1: string | null = null;
      let hint2: string | null = null;
      let hint3: string | null = null;

      act(() => {
        hint1 = result.current.requestHint();
      });
      expect(hint1).toBe('Hint 1: Look at position A1');
      expect(result.current.nextHintIndex).toBe(1);

      act(() => {
        hint2 = result.current.requestHint();
      });
      expect(hint2).toBe('Hint 2: This is a ladder technique');
      expect(result.current.nextHintIndex).toBe(2);

      act(() => {
        hint3 = result.current.requestHint();
      });
      expect(hint3).toBe('Hint 3: Play the atari at the corner');
      expect(result.current.hasMoreHints).toBe(false);
    });

    it('should handle hint panel with callback integration', () => {
      const hints: string[] = [];
      const hintCounts: number[] = [];

      const onHintRequested = (hint: string, count: number): void => {
        hints.push(hint);
        hintCounts.push(count);
      };

      render(
        <HintPanel
          puzzle={THREE_HINT_PUZZLE}
          onHintRequested={onHintRequested}
        />
      );

      // Click hint button multiple times
      const button = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);

      expect(hints).toEqual([
        'First hint: Look at the corner',
        'Second hint: Focus on the vital point',
        'Third hint: The key move is on the 3rd line',
      ]);
      expect(hintCounts).toEqual([0, 1, 2]);
    });

    it('should maintain hint state across puzzle reset scenario', () => {
      const onHintsReset = vi.fn();

      render(
        <HintPanel
          puzzle={THREE_HINT_PUZZLE}
          onHintsReset={onHintsReset}
        />
      );

      // Request hints
      const hintButton = screen.getByRole('button', { name: /get hint/i });
      fireEvent.click(hintButton);
      fireEvent.click(hintButton);

      // Verify 2 hints shown
      expect(screen.getByText('(2/3)')).toBeDefined();

      // Reset hints
      const resetButton = screen.getByRole('button', { name: /reset/i });
      fireEvent.click(resetButton);

      // Verify reset
      expect(onHintsReset).toHaveBeenCalled();
      expect(screen.getByText('(0/3)')).toBeDefined();
      expect(screen.getByText(/No hints used yet/i)).toBeDefined();
    });

    it('should report correct hint metrics for puzzle completion', () => {
      const { result } = renderHook(() => useHints(THREE_HINT_PUZZLE));

      // Simulate partial hint usage (common scenario)
      act(() => {
        result.current.requestHint();
        result.current.requestHint();
      });

      // Get metrics for completion tracking
      const metrics = {
        hintsUsed: result.current.hintsUsed,
        totalHints: result.current.totalHints,
        hintsRemaining: result.current.totalHints - result.current.hintsUsed,
        perfectSolve: result.current.hintsUsed === 0,
      };

      expect(metrics).toEqual({
        hintsUsed: 2,
        totalHints: 3,
        hintsRemaining: 1,
        perfectSolve: false,
      });
    });
  });
});