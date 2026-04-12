/**
 * Boot-to-Solve Integration Test
 *
 * End-to-end flow: mock fetch → boot() → SolverView renders →
 * getBootConfigs() returns data → puzzle validated → coordinate toggle works.
 *
 * Spec 127: T074
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import { boot, getBootConfigs, _resetBootForTesting } from '../../src/boot';
import { SolverView } from '../../src/components/Solver/SolverView';
import { useSettings } from '../../src/hooks/useSettings';

// ============================================================================
// Test Data
// ============================================================================

const MOCK_LEVELS = {
  schema_version: '1.0',
  levels: [
    { slug: 'beginner', name: 'Beginner', rank_range: '25k-20k', order: 1 },
    { slug: 'intermediate', name: 'Intermediate', rank_range: '15k-10k', order: 3 },
  ],
};

const MOCK_TAGS = {
  schema_version: '6',
  tags: [
    { id: 'life-and-death', name: 'Life and Death', category: 'technique' },
    { id: 'ladder', name: 'Ladder', category: 'technique' },
  ],
};

const MOCK_TIPS = {
  schema_version: '1.0',
  tips: [
    { text: 'Cut first, connect later.', category: 'tip', levels: ['beginner'] },
  ],
};

// Minimal valid SGF for a beginner puzzle
const MOCK_SGF =
  '(;FF[4]GM[1]SZ[9]GN[YENGO-test123]YG[beginner]YT[life-and-death]' +
  'YH[Corner focus|Read carefully|Black lives]' +
  'AB[aa][ba]AW[ab][bb];B[ca])';

// ============================================================================
// Mocks
// ============================================================================

// Mock useGoban to avoid actual goban rendering
vi.mock('../../src/hooks/useGoban', () => ({
  useGoban: () => ({
    gobanRef: { current: null },
    isReady: true,
  }),
}));

// Mock usePuzzleState
vi.mock('../../src/hooks/usePuzzleState', () => ({
  usePuzzleState: () => ({
    state: { status: 'waiting', currentComment: null },
    makeMove: vi.fn(),
    revealSolution: vi.fn(),
  }),
}));

// Mock useBoardMarkers
vi.mock('../../src/hooks/useBoardMarkers', () => ({
  useBoardMarkers: () => ({
    setMarkers: vi.fn(),
    clearMarkers: vi.fn(),
  }),
}));

// ============================================================================
// Tests
// ============================================================================

describe('Boot-to-Solve Integration', () => {
  beforeEach(() => {
    _resetBootForTesting();

    // Mock fetch to serve config files via vi.stubGlobal
    vi.stubGlobal('fetch', vi.fn(async (url: string | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();

      if (urlStr.includes('puzzle-levels.json')) {
        return new Response(JSON.stringify(MOCK_LEVELS), { status: 200 });
      }
      if (urlStr.includes('tags.json')) {
        return new Response(JSON.stringify(MOCK_TAGS), { status: 200 });
      }
      if (urlStr.includes('go-tips.json')) {
        return new Response(JSON.stringify(MOCK_TIPS), { status: 200 });
      }
      return new Response('Not Found', { status: 404 });
    }) as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('boot() loads configs and getBootConfigs() returns them', async () => {
    await boot();

    const configs = getBootConfigs();
    expect(configs).not.toBeNull();
    expect(configs!.levels).toHaveLength(2);
    expect(configs!.levels[0].slug).toBe('beginner');
    expect(configs!.tags).toHaveLength(2);
    expect(configs!.tags[0].id).toBe('life-and-death');
    expect(configs!.tips).toHaveLength(1);
  });

  it('SolverView renders with SGF data', async () => {
    await boot();

    const { container } = render(
      <SolverView sgf={MOCK_SGF} level="beginner" />,
    );

    // Should render the solver component
    const solver = container.querySelector('[data-component="solver-view"]');
    expect(solver).not.toBeNull();

    // Should show waiting status initially
    expect(solver!.getAttribute('data-status')).toBe('waiting');
  });

  it('SolverView shows coordinate toggle', async () => {
    await boot();

    render(<SolverView sgf={MOCK_SGF} level="beginner" />);

    // Coordinate toggle button should exist
    const toggleBtn = screen.getByLabelText('Toggle coordinates');
    expect(toggleBtn).not.toBeNull();
  });

  it('coordinate toggle updates settings', async () => {
    await boot();

    render(<SolverView sgf={MOCK_SGF} level="beginner" />);

    const toggleBtn = screen.getByLabelText('Toggle coordinates');

    // Initial state — check aria-pressed
    const initialPressed = toggleBtn.getAttribute('aria-pressed');

    // Click toggle
    fireEvent.click(toggleBtn);

    // Should toggle
    await waitFor(() => {
      const newPressed = toggleBtn.getAttribute('aria-pressed');
      expect(newPressed).not.toBe(initialPressed);
    });
  });

  it('SolverView displays hint overlay for unsolved puzzle', async () => {
    await boot();

    render(<SolverView sgf={MOCK_SGF} level="beginner" />);

    // HintOverlay should be present (puzzle is unsolved)
    const hintSection = screen.queryByText(/Hint/i);
    // The hint overlay renders when there are hints in the SGF
    expect(hintSection).not.toBeNull();
  });

  it('SolverView shows solution reveal button for unsolved puzzle', async () => {
    await boot();

    render(<SolverView sgf={MOCK_SGF} level="beginner" />);

    // SolutionReveal should have a "Show Solution" button
    const revealBtn = screen.queryByText(/Show Solution/i);
    expect(revealBtn).not.toBeNull();
  });
});
