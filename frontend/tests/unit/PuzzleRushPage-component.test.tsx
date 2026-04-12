/**
 * PuzzleRushPage component tests (T3).
 *
 * Initiative: 20260324-1400-feature-rush-progress-component-tests
 * Heavy mocking: useRushSession hook, service stubs, component stubs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/preact';

// -- Hook mock -------------------------------------------------------------
const mockActions = {
  start: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  recordCorrect: vi.fn(),
  recordWrong: vi.fn(),
  skip: vi.fn(),
  reset: vi.fn(),
};

const defaultRushState = {
  isActive: false,
  duration: 180,
  timeRemaining: 180,
  lives: 3,
  maxLives: 3,
  score: 0,
  puzzlesSolved: 0,
  puzzlesFailed: 0,
  currentStreak: 0,
};

let hookReturn = {
  state: { ...defaultRushState },
  actions: mockActions,
  isGameOver: false,
  isPaused: false,
  timeDisplay: '3:00',
};

vi.mock('@hooks/useRushSession', () => ({
  useRushSession: vi.fn(() => hookReturn),
}));

// -- Service mock ----------------------------------------------------------
vi.mock('@services/progress', () => ({
  recordRushScore: vi.fn(),
}));

// -- Component stubs -------------------------------------------------------
vi.mock('@components/Rush', () => ({
  RushOverlay: () => <div data-testid="rush-overlay" />,
}));

vi.mock('@components/PuzzleSetPlayer', () => ({
  PuzzleSetPlayer: ({ renderHeader, renderSummary, ...rest }: any) => (
    <div data-testid="puzzle-set-player" {...rest} />
  ),
}));

vi.mock('@services/puzzleLoaders/RushPuzzleLoader', () => ({
  RushPuzzleLoader: vi.fn().mockImplementation(() => ({})),
}));

vi.mock('@components/Layout', () => ({
  PageLayout: ({ children, mode }: { children: any; mode?: string }) => (
    <div data-testid="page-layout" data-mode={mode}>{children}</div>
  ),
}));

vi.mock('@components/shared/Button', () => ({
  Button: ({ children, onClick, ...rest }: any) => (
    <button onClick={onClick} {...rest}>{children}</button>
  ),
}));

vi.mock('@components/shared/icons', () => ({
  HeartIcon: () => <span>♥</span>,
  FireIcon: () => <span>🔥</span>,
}));

vi.mock('@lib/accuracy-color', () => ({
  getAccuracyColorClass: () => '',
}));

import { PuzzleRushPage, type PuzzleRushPageProps } from '../../src/pages/PuzzleRushPage';

function createProps(overrides: Partial<PuzzleRushPageProps> = {}): PuzzleRushPageProps {
  return {
    onNavigateHome: vi.fn(),
    onNewRush: vi.fn(),
    ...overrides,
  };
}

describe('PuzzleRushPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    hookReturn = {
      state: { ...defaultRushState },
      actions: mockActions,
      isGameOver: false,
      isPaused: false,
      timeDisplay: '3:00',
    };
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('P1: renders PageLayout with mode="rush"', () => {
    render(<PuzzleRushPage {...createProps()} />);
    const layout = screen.getByTestId('page-layout');
    expect(layout.dataset.mode).toBe('rush');
  });

  it('P2: starts in countdown state showing "Get ready!"', () => {
    render(<PuzzleRushPage {...createProps()} />);
    expect(screen.getByText('Get ready!')).toBeTruthy();
  });

  it('P3: renders countdown value element', () => {
    render(<PuzzleRushPage {...createProps()} />);
    expect(screen.getByTestId('countdown-value')).toBeTruthy();
  });

  it('P4: accepts custom testId prop', () => {
    render(<PuzzleRushPage {...createProps()} testId="custom-rush" />);
    expect(screen.getByTestId('custom-rush')).toBeTruthy();
  });

  it('P5: finished state renders "Game Over!" heading', () => {
    hookReturn = { ...hookReturn, isGameOver: true };
    render(<PuzzleRushPage {...createProps()} />);

    // Advance past countdown: 3 × 1s ticks (synchronous act to avoid deadlock)
    act(() => { vi.advanceTimersByTime(3000); });

    expect(screen.getByText('Game Over!')).toBeTruthy();
  });

  it('P6: finished state renders final score display', () => {
    hookReturn = { ...hookReturn, isGameOver: true, state: { ...defaultRushState, score: 750 } };
    render(<PuzzleRushPage {...createProps()} />);

    act(() => { vi.advanceTimersByTime(3000); });

    expect(screen.getByTestId('final-score')).toBeTruthy();
    expect(screen.getByText('750')).toBeTruthy();
  });

  it('P7: finished state Play Again button calls onNewRush', () => {
    const onNewRush = vi.fn();
    hookReturn = { ...hookReturn, isGameOver: true };
    render(<PuzzleRushPage {...createProps({ onNewRush })} />);

    act(() => { vi.advanceTimersByTime(3000); });

    fireEvent.click(screen.getByTestId('play-again-button'));
    expect(onNewRush).toHaveBeenCalledOnce();
  });

  it('P8: finished state Go Home button calls onNavigateHome', () => {
    const onNavigateHome = vi.fn();
    hookReturn = { ...hookReturn, isGameOver: true };
    render(<PuzzleRushPage {...createProps({ onNavigateHome })} />);

    act(() => { vi.advanceTimersByTime(3000); });

    fireEvent.click(screen.getByTestId('home-button'));
    expect(onNavigateHome).toHaveBeenCalledOnce();
  });
});
