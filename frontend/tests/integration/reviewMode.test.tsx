/**
 * Integration Tests for Review Mode
 * @module tests/integration/reviewMode.test
 *
 * Covers: FR-036, FR-037, FR-038, US6
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { renderHook, act } from '@testing-library/preact';
import type { Puzzle, Explanation } from '../../src/models/puzzle';
import { BLACK, WHITE } from '../../src/models/puzzle';
import {
  ReviewMode,
  ReviewControls,
  useReviewMode,
  type SolutionStep,
} from '../../src/components/Puzzle/ReviewMode';
import {
  ExplanationPanel,
  ExplanationList,
  EmptyExplanation,
} from '../../src/components/Puzzle/ExplanationPanel';

// --- Test Fixtures ---

const SIMPLE_PUZZLE: Puzzle = {
  version: '1.0',
  id: 'test-review-puzzle',
  boardSize: 9,
  initialState: [
    ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
    ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
    ['empty', 'empty', 'white', 'white', 'white', 'empty', 'empty', 'empty', 'empty'],
    ['empty', 'white', 'black', 'black', 'black', 'white', 'empty', 'empty', 'empty'],
    ['empty', 'white', 'black', 'empty', 'black', 'white', 'empty', 'empty', 'empty'],
    ['empty', 'white', 'black', 'black', 'black', 'white', 'empty', 'empty', 'empty'],
    ['empty', 'empty', 'white', 'white', 'white', 'empty', 'empty', 'empty', 'empty'],
    ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
    ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
  ],
  sideToMove: 'black',
  solutionTree: {
    move: { x: 3, y: 4 }, // Black plays in the eye
    response: { x: 2, y: 4 }, // White responds
    branches: [
      {
        move: { x: 3, y: 3 }, // Black's next move
        isWinning: true,
      },
    ],
  },
  hints: ['Focus on the vital point in the center'],
  explanations: [
    {
      move: { x: 3, y: 4 },
      text: 'This is the vital point - playing here creates two eyes.',
      highlightPoints: [{ x: 3, y: 4 }],
    },
    {
      move: { x: 3, y: 3 },
      text: 'This completes the second eye, ensuring life.',
    },
  ],
  metadata: {
    difficulty: '15kyu',
    difficultyScore: 2,
    tags: ['life-and-death', 'two-eyes'],
    level: '2026-01-20',
    createdAt: '2026-01-20T00:00:00Z',
  },
};

const NO_EXPLANATION_PUZZLE: Puzzle = {
  ...SIMPLE_PUZZLE,
  id: 'no-explanation-puzzle',
  explanations: [],
};

// --- useReviewMode Hook Tests ---

describe('useReviewMode', () => {
  describe('initialization', () => {
    it('should start at initial position (index -1)', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      expect(result.current.currentStepIndex).toBe(-1);
      expect(result.current.isAtStart).toBe(true);
    });

    it('should extract solution path from puzzle', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      expect(result.current.solutionPath.length).toBeGreaterThan(0);
      expect(result.current.totalSteps).toBeGreaterThan(0);
    });

    it('should start with initial board state', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      expect(result.current.currentBoard).toEqual(SIMPLE_PUZZLE.initialState);
    });

    it('should have canGoForward true at start', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      expect(result.current.canGoForward).toBe(true);
      expect(result.current.canGoBack).toBe(false);
    });
  });

  describe('navigation', () => {
    it('should go forward to first move', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goForward();
      });

      expect(result.current.currentStepIndex).toBe(0);
      expect(result.current.currentStep).not.toBeNull();
      expect(result.current.isAtStart).toBe(false);
    });

    it('should go back to initial position', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goForward();
      });

      act(() => {
        result.current.goBack();
      });

      expect(result.current.currentStepIndex).toBe(-1);
      expect(result.current.isAtStart).toBe(true);
    });

    it('should jump to end', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goToEnd();
      });

      expect(result.current.isAtEnd).toBe(true);
      expect(result.current.canGoForward).toBe(false);
    });

    it('should jump to start', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goToEnd();
      });

      act(() => {
        result.current.goToStart();
      });

      expect(result.current.isAtStart).toBe(true);
      expect(result.current.currentStepIndex).toBe(-1);
    });

    it('should go to specific step', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goToStep(1);
      });

      expect(result.current.currentStepIndex).toBe(1);
    });

    it('should not go beyond bounds', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      act(() => {
        result.current.goToStep(-5);
      });

      // Should stay at valid position
      expect(result.current.currentStepIndex).toBe(-1);

      act(() => {
        result.current.goToStep(1000);
      });

      // Should not exceed total steps
      expect(result.current.currentStepIndex).toBe(-1);
    });
  });

  describe('solution steps', () => {
    it('should include move information in steps', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      const firstStep = result.current.solutionPath[0];
      expect(firstStep).toBeDefined();
      expect(firstStep?.move).toBeDefined();
      expect(firstStep?.move.x).toBe(3);
      expect(firstStep?.move.y).toBe(4);
    });

    it('should mark player vs opponent moves', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      // First move should be player (black)
      const firstStep = result.current.solutionPath[0];
      expect(firstStep?.isPlayerMove).toBe(true);
      expect(firstStep?.move.color).toBe(BLACK);
    });

    it('should include explanations in steps when available', () => {
      const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

      const firstStep = result.current.solutionPath[0];
      expect(firstStep?.explanation).toBe('This is the vital point - playing here creates two eyes.');
    });

    it('should have undefined explanation when none exists', () => {
      const { result } = renderHook(() => useReviewMode(NO_EXPLANATION_PUZZLE));

      const firstStep = result.current.solutionPath[0];
      expect(firstStep?.explanation).toBeUndefined();
    });
  });
});

// --- ReviewMode Component Tests ---

describe('ReviewMode Component', () => {
  describe('rendering', () => {
    it('should render review mode container', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      expect(screen.getByRole('region', { name: /solution review/i })).toBeDefined();
    });

    it('should render header with title', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      expect(screen.getByRole('heading', { name: /solution review/i })).toBeDefined();
    });

    it('should render exit button when onExit provided', () => {
      const onExit = vi.fn();
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} onExit={onExit} />);

      expect(screen.getByRole('button', { name: /exit review/i })).toBeDefined();
    });

    it('should not render exit button when onExit not provided', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      expect(screen.queryByRole('button', { name: /exit review/i })).toBeNull();
    });

    it('should render navigation controls', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      expect(screen.getByRole('group', { name: /review navigation/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /go to start/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /previous move/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /next move/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /go to end/i })).toBeDefined();
    });

    it('should render progress bar', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      expect(screen.getByRole('progressbar')).toBeDefined();
    });

    it('should show initial position status', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      // Multiple status elements exist (Board's screen reader live region + step indicator)
      const statusElements = screen.getAllByRole('status');
      expect(statusElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/initial position/i)).toBeDefined();
    });
  });

  describe('navigation interactions', () => {
    it('should advance to next move when forward clicked', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      const forwardButton = screen.getByRole('button', { name: /next move/i });
      fireEvent.click(forwardButton);

      expect(screen.getByText(/move 1 of/i)).toBeDefined();
    });

    it('should go back when back clicked', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      // Go forward first
      const forwardButton = screen.getByRole('button', { name: /next move/i });
      fireEvent.click(forwardButton);

      // Then go back
      const backButton = screen.getByRole('button', { name: /previous move/i });
      fireEvent.click(backButton);

      expect(screen.getByText(/initial position/i)).toBeDefined();
    });

    it('should call onExit when exit clicked', () => {
      const onExit = vi.fn();
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} onExit={onExit} />);

      const exitButton = screen.getByRole('button', { name: /exit review/i });
      fireEvent.click(exitButton);

      expect(onExit).toHaveBeenCalled();
    });

    it('should disable back button at start', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      const backButton = screen.getByRole('button', { name: /previous move/i });
      expect(backButton.getAttribute('disabled')).not.toBeNull();
    });

    it('should disable forward button at end', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      // Go to end
      const endButton = screen.getByRole('button', { name: /go to end/i });
      fireEvent.click(endButton);

      const forwardButton = screen.getByRole('button', { name: /next move/i });
      expect(forwardButton.getAttribute('disabled')).not.toBeNull();
    });
  });

  describe('explanation display', () => {
    it('should show explanation when available for current move', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      // Go to first move (has explanation)
      const forwardButton = screen.getByRole('button', { name: /next move/i });
      fireEvent.click(forwardButton);

      expect(screen.getByText(/vital point/i)).toBeDefined();
    });

    it('should not show explanation at initial position', () => {
      render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

      // At initial position - no explanation
      expect(screen.queryByRole('region', { name: /move explanation/i })).toBeNull();
    });
  });
});

// --- ReviewControls Component Tests ---

describe('ReviewControls', () => {
  const defaultProps = {
    canGoBack: true,
    canGoForward: true,
    isAtStart: false,
    isAtEnd: false,
    onGoToStart: vi.fn(),
    onGoBack: vi.fn(),
    onGoForward: vi.fn(),
    onGoToEnd: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render all control buttons', () => {
    render(<ReviewControls {...defaultProps} />);

    expect(screen.getByRole('button', { name: /go to start/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /previous move/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /next move/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /go to end/i })).toBeDefined();
  });

  it('should call onGoForward when forward clicked', () => {
    render(<ReviewControls {...defaultProps} />);

    const forwardButton = screen.getByRole('button', { name: /next move/i });
    fireEvent.click(forwardButton);

    expect(defaultProps.onGoForward).toHaveBeenCalled();
  });

  it('should call onGoBack when back clicked', () => {
    render(<ReviewControls {...defaultProps} />);

    const backButton = screen.getByRole('button', { name: /previous move/i });
    fireEvent.click(backButton);

    expect(defaultProps.onGoBack).toHaveBeenCalled();
  });

  it('should call onGoToStart when start clicked', () => {
    render(<ReviewControls {...defaultProps} />);

    const startButton = screen.getByRole('button', { name: /go to start/i });
    fireEvent.click(startButton);

    expect(defaultProps.onGoToStart).toHaveBeenCalled();
  });

  it('should call onGoToEnd when end clicked', () => {
    render(<ReviewControls {...defaultProps} />);

    const endButton = screen.getByRole('button', { name: /go to end/i });
    fireEvent.click(endButton);

    expect(defaultProps.onGoToEnd).toHaveBeenCalled();
  });

  it('should disable buttons appropriately at start', () => {
    render(
      <ReviewControls
        {...defaultProps}
        canGoBack={false}
        isAtStart={true}
      />
    );

    const startButton = screen.getByRole('button', { name: /go to start/i });
    const backButton = screen.getByRole('button', { name: /previous move/i });

    expect(startButton.getAttribute('disabled')).not.toBeNull();
    expect(backButton.getAttribute('disabled')).not.toBeNull();
  });

  it('should disable buttons appropriately at end', () => {
    render(
      <ReviewControls
        {...defaultProps}
        canGoForward={false}
        isAtEnd={true}
      />
    );

    const forwardButton = screen.getByRole('button', { name: /next move/i });
    const endButton = screen.getByRole('button', { name: /go to end/i });

    expect(forwardButton.getAttribute('disabled')).not.toBeNull();
    expect(endButton.getAttribute('disabled')).not.toBeNull();
  });
});

// --- ExplanationPanel Component Tests ---

describe('ExplanationPanel', () => {
  const testExplanation: Explanation = {
    move: { x: 3, y: 4 },
    text: 'This is a test explanation for the move.',
    highlightPoints: [{ x: 3, y: 4 }, { x: 4, y: 4 }],
  };

  it('should render explanation text', () => {
    render(<ExplanationPanel explanation={testExplanation} />);

    expect(screen.getByText(/test explanation/i)).toBeDefined();
  });

  it('should render with text prop directly', () => {
    render(<ExplanationPanel text="Direct text explanation" />);

    expect(screen.getByText(/direct text explanation/i)).toBeDefined();
  });

  it('should return null when no explanation', () => {
    const { container } = render(<ExplanationPanel />);

    expect(container.innerHTML).toBe('');
  });

  it('should have accessible region role', () => {
    render(<ExplanationPanel explanation={testExplanation} />);

    expect(screen.getByRole('region', { name: /move explanation/i })).toBeDefined();
  });

  it('should show highlight points when provided', () => {
    render(<ExplanationPanel explanation={testExplanation} />);

    expect(screen.getByText(/key points/i)).toBeDefined();
  });

  it('should render in compact mode', () => {
    render(<ExplanationPanel explanation={testExplanation} compact />);

    const panel = screen.getByRole('region');
    expect(panel.className).toContain('compact');
  });
});

// --- ExplanationList Component Tests ---

describe('ExplanationList', () => {
  const explanations: readonly Explanation[] = [
    { move: { x: 3, y: 4 }, text: 'First explanation' },
    { move: { x: 2, y: 4 }, text: 'Second explanation' },
    { move: { x: 3, y: 3 }, text: 'Third explanation' },
  ];

  it('should render all explanations', () => {
    render(<ExplanationList explanations={explanations} />);

    expect(screen.getByText(/first explanation/i)).toBeDefined();
    expect(screen.getByText(/second explanation/i)).toBeDefined();
    expect(screen.getByText(/third explanation/i)).toBeDefined();
  });

  it('should return null when empty', () => {
    const { container } = render(<ExplanationList explanations={[]} />);

    expect(container.innerHTML).toBe('');
  });

  it('should highlight current move', () => {
    render(<ExplanationList explanations={explanations} currentMoveIndex={1} />);

    const items = screen.getAllByRole('listitem');
    expect(items[1]?.getAttribute('aria-current')).toBe('true');
  });

  it('should have accessible list role', () => {
    render(<ExplanationList explanations={explanations} />);

    expect(screen.getByRole('list', { name: /all move explanations/i })).toBeDefined();
  });
});

// --- EmptyExplanation Component Tests ---

describe('EmptyExplanation', () => {
  it('should render default message', () => {
    render(<EmptyExplanation />);

    expect(screen.getByText(/no explanation available/i)).toBeDefined();
  });

  it('should render custom message', () => {
    render(<EmptyExplanation message="Custom empty message" />);

    expect(screen.getByText(/custom empty message/i)).toBeDefined();
  });

  it('should have status role', () => {
    render(<EmptyExplanation />);

    expect(screen.getByRole('status')).toBeDefined();
  });
});

// --- Integration Scenario Tests ---

describe('Review Mode Integration', () => {
  it('should complete full review flow', () => {
    const onExit = vi.fn();
    render(<ReviewMode puzzle={SIMPLE_PUZZLE} onExit={onExit} />);

    // Start at initial position
    expect(screen.getByText(/initial position/i)).toBeDefined();

    // Step through all moves
    const forwardButton = screen.getByRole('button', { name: /next move/i });

    // Click forward until we can't anymore
    let steps = 0;
    while (!forwardButton.hasAttribute('disabled') && steps < 10) {
      fireEvent.click(forwardButton);
      steps++;
    }

    // Should be at end now
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar.getAttribute('aria-valuenow')).toBe(String(steps));

    // Exit review
    const exitButton = screen.getByRole('button', { name: /exit review/i });
    fireEvent.click(exitButton);

    expect(onExit).toHaveBeenCalled();
  });

  it('should preserve state when navigating back and forth', () => {
    render(<ReviewMode puzzle={SIMPLE_PUZZLE} />);

    const forwardButton = screen.getByRole('button', { name: /next move/i });
    const backButton = screen.getByRole('button', { name: /previous move/i });

    // Go forward twice
    fireEvent.click(forwardButton);
    fireEvent.click(forwardButton);

    expect(screen.getByText(/move 2 of/i)).toBeDefined();

    // Go back once
    fireEvent.click(backButton);

    expect(screen.getByText(/move 1 of/i)).toBeDefined();

    // Go forward again
    fireEvent.click(forwardButton);

    expect(screen.getByText(/move 2 of/i)).toBeDefined();
  });

  it('should show correct board state at each step', () => {
    const { result } = renderHook(() => useReviewMode(SIMPLE_PUZZLE));

    // Initial state should match puzzle initial state
    expect(result.current.currentBoard).toEqual(SIMPLE_PUZZLE.initialState);

    // After first move, should have a step recorded
    act(() => {
      result.current.goForward();
    });

    // Current step should exist and have board state
    expect(result.current.currentStep).not.toBeNull();
    expect(result.current.currentStep?.boardState).toBeDefined();

    // Going back should restore initial state
    act(() => {
      result.current.goBack();
    });

    expect(result.current.currentBoard).toEqual(SIMPLE_PUZZLE.initialState);
  });
});
