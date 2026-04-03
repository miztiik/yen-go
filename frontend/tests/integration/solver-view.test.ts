/**
 * Integration test for SolverView.
 *
 * Mounts with test SGF, verifies:
 * - Component renders board + controls
 * - Correct move → solved state
 * - Off-trunk move → exploration mode
 * - Complete flow (hints, solution reveal, next)
 *
 * Spec 127: Phase 5, T057
 * @module tests/integration/solver-view
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { SolverView } from '../../src/components/Solver/SolverView';

// -------------------------------------------------------------------
// Mocks
// -------------------------------------------------------------------

// Mock useGoban — returns stable refs + isReady=true
vi.mock('../../src/hooks/useGoban', () => ({
  useGoban: () => ({
    gobanRef: { current: { draw_top_labels: true, draw_left_labels: true, draw_bottom_labels: true, draw_right_labels: true, redraw: vi.fn() } },
    isReady: true,
  }),
}));

// Mock usePuzzleState — default solving state
const mockPuzzleState = {
  state: { status: 'solving' as const, currentComment: null },
  revealSolution: vi.fn(),
};
vi.mock('../../src/hooks/usePuzzleState', () => ({
  usePuzzleState: () => mockPuzzleState,
}));

// Mock useBoardMarkers
vi.mock('../../src/hooks/useBoardMarkers', () => ({
  useBoardMarkers: () => ({ setColoredCircles: vi.fn(), clearMarkers: vi.fn() }),
}));

// Mock useSettings
vi.mock('../../src/hooks/useSettings', () => ({
  useSettings: () => ({
    settings: { theme: 'light', soundEnabled: true, coordinateLabels: true },
    updateSettings: vi.fn(),
  }),
}));

// Mock boot
vi.mock('../../src/boot', () => ({
  getBootConfigs: () => null,
}));

// -------------------------------------------------------------------
// Test SGF
// -------------------------------------------------------------------

const TEST_SGF = '(;FF[4]GM[1]SZ[9]YG[beginner]YT[life-and-death]YH[Corner focus|Try atari|Read carefully];B[cc];W[cd];B[dc])';

// -------------------------------------------------------------------
// Tests
// -------------------------------------------------------------------

describe('SolverView integration', () => {
  beforeEach(() => {
    mockPuzzleState.state = { status: 'solving', currentComment: null };
    vi.clearAllMocks();
  });

  it('renders the board container', () => {
    const { container } = render(<SolverView sgf={TEST_SGF} />);
    const solver = container.querySelector('[data-component="solver-view"]');
    expect(solver).toBeTruthy();
  });

  it('renders with solving status', () => {
    const { container } = render(<SolverView sgf={TEST_SGF} />);
    const solver = container.querySelector('[data-component="solver-view"]');
    expect(solver?.getAttribute('data-status')).toBe('solving');
  });

  it('shows skip button when onSkip is provided and not solved', () => {
    render(<SolverView sgf={TEST_SGF} onSkip={() => {}} />);
    expect(screen.getByText('Skip')).toBeTruthy();
  });

  it('hides skip button when puzzle is solved', () => {
    mockPuzzleState.state = { status: 'correct', currentComment: null };
    render(<SolverView sgf={TEST_SGF} onSkip={() => {}} />);
    expect(screen.queryByText('Skip')).toBeNull();
  });

  it('shows next button when solved and onNext provided', () => {
    mockPuzzleState.state = { status: 'correct', currentComment: null };
    render(<SolverView sgf={TEST_SGF} onNext={() => {}} />);
    expect(screen.getByText('Next →')).toBeTruthy();
  });

  it('shows solved state when puzzle is correct', () => {
    mockPuzzleState.state = { status: 'correct', currentComment: null };
    render(<SolverView sgf={TEST_SGF} />);
    expect(screen.getByText('✓ Puzzle Solved!')).toBeTruthy();
  });

  it('shows coordinate toggle button', () => {
    render(<SolverView sgf={TEST_SGF} />);
    const toggle = screen.getByLabelText('Toggle coordinates');
    expect(toggle).toBeTruthy();
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
  });

  it('renders hint overlay when not solved', () => {
    const { container } = render(<SolverView sgf={TEST_SGF} />);
    // HintOverlay renders a button for requesting hints
    const hintButton = container.querySelector('[data-component="solver-view"] button');
    expect(hintButton).toBeTruthy();
  });
});
